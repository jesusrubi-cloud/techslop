"""Optional licensed music with speech-driven ducking. No automatic music downloads."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ALLOWED = {'CC0-1.0', 'CC-BY-4.0'}


def validate_license(audio: Path, license_file: Path) -> dict:
    metadata = json.loads(license_file.read_text())
    if metadata.get('license') not in ALLOWED or not all(metadata.get(k) for k in ['title', 'author', 'source']):
        raise ValueError('Music requires CC0-1.0 or CC-BY-4.0 metadata, author and source')
    if hashlib.sha256(audio.read_bytes()).hexdigest() != metadata.get('sha256'):
        raise ValueError('Music hash does not match licensed asset')
    return metadata


def mix_with_ducking(voice: Path, music: Path, license_file: Path, output: Path) -> dict:
    license_info = validate_license(music, license_file)
    # A sidechain copy of normalized speech controls only the background gain.
    filters = ('[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[v][side];'
               '[1:a]aresample=48000,volume=0.30[bg];'
               '[bg][side]sidechaincompress=threshold=0.02:ratio=12:attack=10:release=250:makeup=1[duck];'
               '[v][duck]amix=inputs=2:duration=first:normalize=0,'
               'alimiter=limit=0.95:level=0:latency=1[a]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(voice), '-stream_loop', '-1', '-i', str(music),
                    '-filter_complex', filters, '-map', '[a]', '-ar', '48000', '-c:a', 'pcm_s16le', str(output)], check=True)
    return {'enabled': True, 'license': license_info, 'ducking': 'speech_sidechain',
            'threshold': .02, 'ratio': 12, 'attack_ms': 10, 'release_ms': 250}
