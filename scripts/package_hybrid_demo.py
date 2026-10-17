"""Recover exact, previously rendered demo bytes; no renderer, APIs or publication."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

REPO = Path(__file__).resolve().parents[1]
EXPECTED = {'techslop-demo.mp4', 'contact-sheet.jpg', 'verification.json'}


def package_demo(output: Path, *, bundle: Path | None = None, manifest_file: Path | None = None) -> dict:
    bundle = bundle or REPO / 'examples/hybrid-demo/download-bundle.zip'
    manifest_file = manifest_file or REPO / 'examples/hybrid-demo/download-manifest.json'
    manifest = json.loads(manifest_file.read_text())
    if set(manifest) != EXPECTED:
        raise ValueError('Unexpected manifest contents')
    # Validate all bytes before creating output. Do not extract arbitrary ZIP paths.
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(EXPECTED) or set(names) != EXPECTED:
            raise ValueError('Unexpected bundle entries')
        content = {}
        for name in sorted(EXPECTED):
            data = archive.read(name)
            if len(data) != manifest[name]['size_bytes'] or hashlib.sha256(data).hexdigest() != manifest[name]['sha256']:
                raise ValueError(f'Integrity check failed: {name}')
            content[name] = data
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory must be empty; existing files are preserved')
    output.mkdir(parents=True, exist_ok=True)
    for name, data in content.items():
        (output / name).write_bytes(data)
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{manifest[name]['sha256']}  {name}\n" for name in sorted(manifest)))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(package_demo(args.output, bundle=args.bundle, manifest_file=args.manifest), indent=2))


if __name__ == '__main__':
    main()
