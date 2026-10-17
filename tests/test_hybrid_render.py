from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import AsyncMock

from PIL import ImageChops
import pytest

from techslop.editorial.script_format import validate_script
from techslop.render.adapter import adapt, word_timestamps
from techslop.render.audio import prepare_audio
from techslop.render.scenes import frame
from techslop.video.assembler import _build_xfade_chain, get_audio_duration


@pytest.fixture
def demo():
    root = Path('examples/hybrid-demo')
    return [json.loads((root / name).read_text()) for name in ['script.json', 'dossier.json', 'presentation.json']]


def test_adapter_uses_measured_audio_instead_of_nominal_scene_times(demo):
    script, plan = adapt(*demo, [12, 16, 18, 14], 'test_tone')
    assert [s.start for s in plan.scenes] == [0, 12, 28, 46]
    assert plan.duration == 60
    assert plan.chart_values == (12, 16, 18, 14)
    assert [s.kind for s in plan.scenes] == ['intro', 'explanation', 'chart', 'closing']
    assert script.publication_approved is False


@pytest.mark.parametrize('durations', [[1, 1, 1, 1], [30, 30, 30, 30], [15], [15, 15, 15, float('nan')]])
def test_bad_audio_timelines_rejected(demo, durations):
    with pytest.raises(ValueError):
        adapt(*demo, durations, 'test_tone')


def test_uncorroborated_real_news_rejected(demo):
    demo[1]['content_type'] = 'news'
    with pytest.raises(ValueError, match='corroboration'):
        adapt(*demo, [15]*4, 'test_tone')


def test_arbitrary_statistics_and_unlicensed_assets_rejected(demo):
    demo[2]['scene-3']['values'] = [100, 500]
    with pytest.raises(ValueError, match='statistics'):
        adapt(*demo, [15]*4, 'test_tone')
    del demo[2]['scene-3']['values']
    demo[0]['scenes'][0]['animation']['asset_origin'] = 'licensed_pending_review'
    with pytest.raises(ValueError, match='external images'):
        adapt(*demo, [15]*4, 'test_tone')


def test_subtitles_preserve_contract_text_and_follow_actual_audio(demo):
    demo[0]['scenes'][1]['subtitles'] = [{'start_seconds': 16, 'end_seconds': 20, 'text': 'Texto editorial breve'}]
    script, plan = adapt(*demo, [12, 16, 18, 14], 'test_tone')
    words, mode = word_timestamps(script, plan, [[]]*4)
    edited = next(w for w in words if w['word'] == 'Texto')
    assert edited['start'] == pytest.approx(12 + 16/15)
    assert mode == 'scaled_contract_reading_cues'
    assert max(w['end'] for w in words) <= 60


def test_edge_boundaries_used_when_subtitles_match_narration(demo):
    script, plan = adapt(*demo, [15]*4, 'edge_es_MX')
    boundaries = [[{'word':'Ejemplo', 'start':1, 'end':2}] for _ in range(4)]
    words, mode = word_timestamps(script, plan, boundaries)
    assert mode == 'edge_word_boundaries'
    assert [w['start'] for w in words] == [1, 16, 31, 46]


@pytest.mark.parametrize('index', range(4))
def test_each_scene_animates_and_uses_native_vertical_canvas(demo, index):
    _, plan = adapt(*demo, [15]*4, 'test_tone')
    first = frame(plan.scenes[index], plan, index, 0)
    later = frame(plan.scenes[index], plan, index, 3)
    assert first.size == (1080, 1920)
    assert ImageChops.difference(first, later).getbbox() is not None
    # Persistent demo/audio banners are not part of the moving content.
    assert ImageChops.difference(first.crop((0, 60, 1080, 150)), later.crop((0, 60, 1080, 150))).getbbox() is None


def test_transition_padding_preserves_audio_scene_boundaries():
    chain, label = _build_xfade_chain(4, [15.4, 15.4, 15.4, 15], .4)
    assert 'offset=15.000' in chain
    assert 'offset=30.000' in chain
    assert 'offset=45.000' in chain


def test_explicit_test_audio_generates_measurable_labelled_tone(demo, tmp_path, monkeypatch):
    script = validate_script(demo[0], demo[1])
    monkeypatch.setattr('techslop.render.audio._edge', AsyncMock(side_effect=ConnectionError('blocked')))
    paths, durations, boundaries, mode, reason = prepare_audio(script, tmp_path, provider="test")
    assert mode == 'test_tone'
    assert reason == 'explicit_test_audio'
    assert sum(durations) == pytest.approx(60)
    assert all(p.name.startswith('test-audio-') for p in paths)
    assert boundaries == [[]]*4
    assert get_audio_duration(paths[0]) == pytest.approx(15)
