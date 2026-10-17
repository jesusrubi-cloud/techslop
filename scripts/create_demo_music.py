"""Create an original quiet synthesized bed; generated audio dedicated under CC0-1.0."""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import wave


def create_music(output: Path) -> Path:
    sample_rate = 24000
    chords = [(130.81, 164.81, 196), (110, 130.81, 164.81), (87.31, 110, 130.81), (98, 123.47, 146.83)]
    pcm = array('h')
    for i in range(sample_rate * 16):
        t = i / sample_rate
        chord = chords[int(t // 4) % 4]
        envelope = min(1, (t % 4) / .3, (4 - t % 4) / .5)
        value = sum(math.sin(2 * math.pi * hz * t) for hz in chord) / 3
        pcm.append(int(32767 * .12 * envelope * value))
    if sys.byteorder != 'little':
        pcm.byteswap()
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), 'wb') as target:
        target.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        target.writeframes(pcm.tobytes())
    metadata = {'title':'Techslop original demo bed', 'author':'techslop procedural demo generator',
                'license':'CC0-1.0', 'source':'scripts/create_demo_music.py — original synthesized tones, no samples',
                'license_url':'https://creativecommons.org/publicdomain/zero/1.0/',
                'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    license_file = output.with_suffix('.license.json')
    license_file.write_text(json.dumps(metadata, indent=2)+'\n')
    return license_file


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    print(create_music(p.parse_args().output))
