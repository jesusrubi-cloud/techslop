"""Configurable free narration: Edge, local eSpeak, supplied audio or explicit test tone."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import edge_tts

from techslop.config import settings

from techslop.editorial.script_format import EditorialScript, duration_bounds
from techslop.video.assembler import get_audio_duration


async def _edge(script: EditorialScript, root: Path) -> tuple[list[Path], list[list[dict]]]:
    if not settings.edge_tts_voice.startswith("es-MX-"):
        raise ValueError("Choose an es-MX Edge voice for Mexican Spanish")
    paths, boundaries = [], []
    for i, scene in enumerate(script.scenes):
        path = root / f'narration-{i}.mp3'
        # Respect the managed HTTPS proxy; no direct-network bypass.
        stream = edge_tts.Communicate(scene.narration_es, settings.edge_tts_voice, rate=settings.narration_rate, boundary='WordBoundary',
                                      proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),
                                      connect_timeout=8, receive_timeout=15)
        words = []
        with path.open('wb') as output:
            async for item in stream.stream():
                if item['type'] == 'audio':
                    output.write(item['data'])
                elif item['type'] == 'WordBoundary':
                    start = item['offset'] / 10_000_000
                    words.append({'word': item['text'], 'start': start, 'end': start + item['duration'] / 10_000_000})
        if not path.stat().st_size:
            raise ValueError('Edge returned no audio')
        paths.append(path)
        boundaries.append(words)
    return paths, boundaries


def prepare_audio(script: EditorialScript, root: Path, *, try_edge: bool = True, provider: str | None = None) -> tuple[list[Path], list[float], list[list[dict]], str, str | None]:
    root.mkdir(parents=True, exist_ok=True)
    selected = provider or (settings.narration_provider if try_edge else 'test')
    if selected not in {'auto', 'edge', 'espeak', 'provided', 'test'}:
        raise ValueError('Narration provider must be auto, edge, espeak, provided or test. Paid providers are not enabled by this renderer.')
    if selected == 'provided':
        import json
        directory = Path(settings.narration_audio_dir)
        if not settings.narration_audio_dir:
            raise ValueError('NARRATION_AUDIO_DIR is required for provided narration')
        paths = [directory / f'scene-{i+1}.wav' for i in range(len(script.scenes))]
        durations = [get_audio_duration(p) for p in paths]
        if not duration_bounds(script)[0] <= sum(durations) <= duration_bounds(script)[1]:
            raise ValueError('Provided narration duration is outside the selected format bounds')
        boundaries = [json.loads(p.with_suffix('.words.json').read_text()) if p.with_suffix('.words.json').exists() else [] for p in paths]
        return paths, durations, boundaries, 'provided_voice', None
    reason = None
    if selected in {'auto', 'edge'}:
        try:
            async def bounded():
                return await asyncio.wait_for(_edge(script, root), timeout=90)
            paths, boundaries = asyncio.run(bounded())
            durations = [get_audio_duration(p) for p in paths]
            if not duration_bounds(script)[0] <= sum(durations) <= duration_bounds(script)[1]:
                raise ValueError('Measured Edge narration is outside selected-format contract')
            return paths, durations, boundaries, 'edge_es_MX', None
        except Exception as exc:
            # Never dump proxy URLs, credentials or arbitrary exception payloads.
            reason = type(exc).__name__
    elif selected == 'test':
        reason = 'explicit_test_audio'
    for partial in root.glob('narration-*.mp3'):
        partial.unlink()
    if selected in {'auto', 'espeak'}:
        from techslop.render.local_voice import synthesize_local
        paths, boundaries = [], []
        for i, scene in enumerate(script.scenes):
            path = root / f'local-voice-{i}.wav'
            boundaries.append(synthesize_local(scene.narration_es, path, voice=settings.local_tts_voice, rate=settings.local_tts_rate))
            paths.append(path)
        durations = [get_audio_duration(p) for p in paths]
        if not duration_bounds(script)[0] <= sum(durations) <= duration_bounds(script)[1]:
            raise ValueError(f'Local narration totals {sum(durations):.2f}s; revise copy or LOCAL_TTS_RATE to fit the selected format')
        return paths, durations, boundaries, 'espeak_es_419', reason
    if selected == 'edge' and reason:
        raise RuntimeError(f'Edge unavailable ({reason}); choose auto, espeak or explicit test audio')
    paths = []
    for i, scene in enumerate(script.scenes):
        path = root / f'test-audio-{i}.wav'
        duration = scene.end_seconds - scene.start_seconds
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        f'sine=frequency={330 + i * 55}:sample_rate=48000:duration={duration}',
                        '-af', 'volume=0.06', '-c:a', 'pcm_s16le', str(path)], check=True)
        paths.append(path)
    return paths, [get_audio_duration(p) for p in paths], [[] for _ in paths], 'test_tone', reason


def concatenate(paths: list[Path], output: Path) -> None:
    command = ['ffmpeg', '-v', 'error', '-y']
    for path in paths:
        command += ['-i', str(path)]
    inputs = ''.join(f'[{i}:a]' for i in range(len(paths)))
    command += ['-filter_complex', f'{inputs}concat=n={len(paths)}:v=0:a=1[a]', '-map', '[a]',
                '-ar', '48000', '-c:a', 'pcm_s16le', str(output)]
    subprocess.run(command, check=True)
