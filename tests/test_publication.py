from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from click.testing import CliRunner
import pytest

import pipeline


@pytest.mark.parametrize('platform', ['youtube', 'tiktok', 'instagram', 'linkedin'])
def test_public_upload_requires_approval_before_any_io(platform):
    from importlib import import_module
    upload = getattr(import_module(f'techslop.publish.{platform}'), f'upload_to_{platform}')
    kwargs = {'description': 'Prueba'} if platform == 'youtube' else {}
    with pytest.raises(PermissionError):
        upload(Path('/nonexistent/video.mp4'), 'Prueba', **kwargs)


def test_cli_publish_rejects_without_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    lookup = Mock(side_effect=AssertionError('must not even look up the video'))
    monkeypatch.setattr(pipeline, '_find_story', lookup)
    result = CliRunner().invoke(pipeline.cli, ['publish', '123'])
    assert result.exit_code != 0
    assert '--approve-publication' in result.output
    lookup.assert_not_called()


def test_run_never_requests_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    run = Mock()
    monkeypatch.setattr(pipeline, '_run_pipeline', run)
    assert CliRunner().invoke(pipeline.cli, ['run']).exit_code == 0
    run.assert_called_once_with(count=1, upload=False)


def test_internal_pipeline_rejects_automatic_upload():
    with pytest.raises(PermissionError):
        pipeline._run_pipeline(upload=True)


def test_approved_cli_passes_approval_only_to_selected_uploader(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from techslop.models import Story
    from techslop.db import init_db, upsert_story, get_all_stories
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    init_db()
    story = Story('a' * 64, 'Noticia', 'https://example.org/a', 'dw', 1, datetime.now(timezone.utc))
    upsert_story(story)
    folder = tmp_path / 'out' / story.id[:12]
    folder.mkdir(parents=True)
    (folder / 'output.mp4').write_bytes(b'local fixture')
    upload = Mock(return_value='mock-id')
    monkeypatch.setattr('techslop.publish.youtube.upload_to_youtube', upload)
    result = CliRunner().invoke(pipeline.cli, ['publish', story.id[:12], '--approve-publication'])
    assert result.exit_code == 0, result.output
    assert upload.call_args.kwargs['approved'] is True
    assert get_all_stories()[0].status == 'published'
