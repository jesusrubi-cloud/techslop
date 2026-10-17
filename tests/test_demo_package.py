from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.package_hybrid_demo import package_demo


def test_original_demo_download_is_byte_identical(tmp_path):
    output = tmp_path / 'download'
    manifest = package_demo(output)
    for name, metadata in manifest.items():
        data = (output / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == metadata['sha256']
        assert len(data) == metadata['size_bytes']
    assert (output / 'techslop-demo.mp4').stat().st_size == 2199801
    assert (output / 'contact-sheet.jpg').read_bytes().startswith(b'\xff\xd8')
    assert 'techslop-demo.mp4' in (output / 'SHA256SUMS.txt').read_text()


def test_existing_user_files_are_preserved(tmp_path):
    (tmp_path / 'keep.txt').write_text('keep')
    with pytest.raises(ValueError, match='empty'):
        package_demo(tmp_path)
    assert (tmp_path / 'keep.txt').read_text() == 'keep'


def test_corrupted_bundle_is_rejected_before_output(tmp_path):
    original = Path('examples/hybrid-demo/download-bundle.zip')
    changed = tmp_path / 'changed.zip'
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(changed, 'w') as target:
        for name in source.namelist():
            data = source.read(name)
            target.writestr(name, data + b'changed' if name.endswith('.mp4') else data)
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='Integrity'):
        package_demo(output, bundle=changed)
    assert not output.exists()


def test_narrated_demo_archive_preserves_voice_and_music_metadata(tmp_path):
    manifest=package_demo(tmp_path/'voiced',bundle=Path('examples/narrated-demo/download-bundle.zip'),manifest_file=Path('examples/narrated-demo/download-manifest.json'))
    report=json.loads((tmp_path/'voiced/verification.json').read_text())
    assert report['audio_mode']=='espeak_es_419'
    assert report['subtitle_mode']=='espeak_word_events'
    assert report['music']['license']['license']=='CC0-1.0'
    assert report['paid_api_calls']==0
    assert report['publication_approved'] is False
    assert manifest['techslop-demo.mp4']['size_bytes']>1000000
