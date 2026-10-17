"""Render the editorial contract using local clips and the existing motion assembler."""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from pathlib import Path
import subprocess
import time

from techslop.editorial.script_format import validate_script
from techslop.render.adapter import adapt, word_timestamps
from techslop.render.audio import prepare_audio, concatenate
from techslop.render.scenes import render_clip, frame
from techslop.video.assembler import assemble_video_motion
from techslop.video.captions import generate_captions


def verify_mp4(path: Path, expected_duration: float) -> dict:
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    metadata = json.loads(probe.stdout)
    video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
    duration = float(metadata['format']['duration'])
    if (video['width'], video['height'], video['r_frame_rate'], video['codec_name'], video['pix_fmt']) != (1080, 1920, '30/1', 'h264', 'yuv420p'):
        raise ValueError('Unexpected video format')
    if audio['codec_name'] != 'aac' or abs(duration - expected_duration) > .15:
        raise ValueError('Unexpected audio codec or duration')
    if abs(float(audio['duration']) - float(video['duration'])) > .15:
        raise ValueError('Audio/video durations diverge')
    # Full decode exercises every video and audio packet, not just headers.
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'], check=True, capture_output=True)
    volume = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(path), '-vn', '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    mean = re.search(r'mean_volume: ([^ ]+) dB', volume.stderr)
    if not mean or mean.group(1) == '-inf':
        raise ValueError('Audio is silent or unmeasurable')
    return {'audio_mean_volume_db': float(mean.group(1)), 'duration_seconds': duration, 'width': video['width'], 'height': video['height'],
            'fps': video['r_frame_rate'], 'video_codec': video['codec_name'], 'audio_codec': audio['codec_name'],
            'audio_duration_seconds': float(audio['duration']), 'video_frames': int(video['nb_frames']),
            'size_bytes': path.stat().st_size, 'full_decode': 'passed'}


def render_editorial(script_file: Path, dossier_file: Path, presentation_file: Path, output_dir: Path, *, try_edge: bool = True, provider: str | None = None, music_file: Path | None = None, music_license: Path | None = None) -> dict:
    started = time.monotonic()
    if bool(music_file) != bool(music_license):
        raise ValueError('Music file and license metadata must be supplied together')
    if music_file:
        from techslop.render.music import validate_license
        validate_license(music_file, music_license)
    data = json.loads(script_file.read_text())
    dossier = json.loads(dossier_file.read_text())
    presentation = json.loads(presentation_file.read_text())
    script = validate_script(data, dossier)
    # Validate content and visual capabilities before any service call.
    nominal = [s.end_seconds - s.start_seconds for s in script.scenes]
    adapt(data, dossier, presentation, nominal, 'test_tone')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('Choose an empty output directory to preserve existing user artifacts')
    output_dir.mkdir(parents=True, exist_ok=True)
    paths, durations, boundaries, audio_mode, fallback_reason = prepare_audio(script, output_dir, try_edge=try_edge, provider=provider)
    script, plan = adapt(data, dossier, presentation, durations, audio_mode)
    timestamps, subtitle_mode = word_timestamps(script, plan, boundaries)
    timestamp_file = output_dir / 'timestamps.json'
    timestamp_file.write_text(json.dumps(timestamps, ensure_ascii=False, indent=2))
    captions = generate_captions(timestamp_file, output_dir / 'captions.ass')
    narration = output_dir / 'narration.wav'
    concatenate(paths, narration)
    music_report = {'enabled': False}
    assembly_audio = narration
    if music_file:
        from techslop.render.music import mix_with_ducking
        assembly_audio = output_dir / 'narration-mixed.wav'
        music_report = mix_with_ducking(narration, music_file, music_license, assembly_audio)
    clips = []
    for i, scene in enumerate(plan.scenes):
        print(f'Rendering {i+1}/{len(plan.scenes)}: {scene.kind} ({scene.duration:.2f}s)', flush=True)
        frame(scene, plan, i, min(3, scene.duration / 2)).save(output_dir / f'scene-{i+1}.png')
        clips.append(render_clip(scene, plan, i, output_dir / f'clip-{i}.mp4', tail=.4 if i < len(plan.scenes)-1 else 0))
    output = assemble_video_motion(clips, assembly_audio, captions, output_dir / 'techslop-demo.mp4', crossfade=.4)
    result = verify_mp4(output, plan.duration)
    # Preserve input snapshots and timing provenance alongside the MP4.
    for name, obj in [('script.json', data), ('dossier.json', dossier), ('presentation.json', presentation), ('render-plan.json', asdict(plan))]:
        (output_dir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    result.update(music=music_report, narration_duration_seconds=plan.duration, audio_mode=audio_mode, fallback_reason=fallback_reason, subtitle_mode=subtitle_mode,
                  fictional_demo=plan.demo, rendering_wall_seconds=round(time.monotonic()-started, 2),
                  paid_api_calls=0, external_api_cost_usd=0, publication_approved=False,
                  output_path=str(output.resolve()))
    (output_dir / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
