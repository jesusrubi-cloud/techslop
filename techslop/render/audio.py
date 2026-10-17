"""Free Edge TTS only; a failed connection yields an explicitly labelled test tone."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import edge_tts

from techslop.editorial.script_format import EditorialScript
from techslop.video.assembler import get_audio_duration


async def _edge(script: EditorialScript, root: Path) -> tuple[list[Path], list[list[dict]]]:
    paths, boundaries = [], []
    for i, scene in enumerate(script.scenes):
        path = root / f'narration-{i}.mp3'
        # Respect the managed HTTPS proxy; no direct-network bypass.
        stream = edge_tts.Communicate(scene.narration_es, 'es-MX-JorgeNeural', boundary='WordBoundary',
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


def prepare_audio(script: EditorialScript, root: Path, *, try_edge: bool = True) -> tuple[list[Path], list[float], list[list[dict]], str, str | None]:
    root.mkdir(parents=True, exist_ok=True)
    reason = None
    if try_edge:
        try:
            async def bounded():
                return await asyncio.wait_for(_edge(script, root), timeout=90)
            paths, boundaries = asyncio.run(bounded())
            durations = [get_audio_duration(p) for p in paths]
            if not 45 <= sum(durations) <= 75:
                raise ValueError('Measured Edge narration is outside the 45–75s contract')
            return paths, durations, boundaries, 'edge_es_MX', None
        except Exception as exc:
            # Never dump proxy URLs, credentials or arbitrary exception payloads.
            reason = type(exc).__name__
    else:
        reason = 'explicit_test_audio'
    for partial in root.glob('narration-*.mp3'):
        partial.unlink()
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
