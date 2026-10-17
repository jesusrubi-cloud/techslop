from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from click.testing import CliRunner
import pytest
from pydantic import ValidationError

from techslop.editorial.selection import group_events, select_editorial
from techslop.editorial.script_format import EditorialScript, validate_script
from techslop.models import Story

NOW = datetime(2026, 10, 17, 19, tzinfo=timezone.utc)
HOSTS = {'bbc_mundo': 'www.bbc.com', 'dw': 'www.dw.com', 'onu': 'news.un.org'}


def story(n, *, title=None, source='bbc_mundo', category='actualidad_general', age=2, summary='Resumen de prueba'):
    return Story(str(n), title or f'Informe editorial tema singular {n}',
                 f'https://{HOSTS[source]}/story/{n}', source, 1, NOW - timedelta(hours=age),
                 raw_data={'summary': summary, 'category': category,
                           'category_manual': True, 'published_at_reported': True})


def test_strict_time_window_and_reported_dates():
    recent, boundary, old, future, undated = [story(i, age=age) for i, age in enumerate([0, 24, 24.01, -1, 1])]
    undated.raw_data['published_at_reported'] = False
    report = select_editorial([recent, boundary, old, future, undated], now=NOW)
    assert report['eligible_stories'] == 2
    assert report['excluded_stories'] == 3
    assert len(report['selected']) == 2
    assert any('Solo hay 2' in w for w in report['warnings'])


def test_no_timestamp_inference_from_ingest_time():
    item = story(1)
    del item.raw_data['published_at_reported']
    assert select_editorial([item], now=NOW)['selected'] == []


def test_diversity_caps_with_sufficient_candidates_and_deterministic_result():
    categories = ['politica_internacional', 'economia', 'ciencia', 'tecnologia', 'actualidad_general']
    items = [story(i, source=source, category=category, title=f'Tema {i} particular')
             for i, (source, category) in enumerate((s, c) for s in HOSTS for c in categories)]
    report = select_editorial(items, now=NOW)
    assert len(report['selected']) == 10
    assert max(report['distribution']['primary_sources'].values()) <= 4
    assert max(report['distribution']['categories'].values()) <= 4
    assert len(report['distribution']['categories']) == 5
    assert report == select_editorial(list(reversed(items)), now=NOW)
    assert report['warnings'] == []


def test_missing_diversity_is_reported_not_invented():
    report = select_editorial([story(i) for i in range(12)], now=NOW)
    assert len(report['selected']) == 10
    assert set(report['distribution']['primary_sources']) == {'bbc_mundo'}
    assert any('fuente' in w for w in report['warnings'])
    assert any('categoría' in w for w in report['warnings'])


def test_same_event_different_headlines_preserves_every_original_url():
    first = story('bbc', title='El papa León XIV sale del hospital tras cirugía por cáncer de pulmón')
    second = story('dw', source='dw', title='Papa León regresa al Vaticano tras ser operado de cáncer de pulmón')
    first.raw_data['sources'] = [{'source': 'bbc_mundo', 'url': first.url + '?utm_medium=rss'}]
    report = select_editorial([first, second], now=NOW)
    assert len(report['selected']) == 1
    event = report['selected'][0]
    assert {s['url'] for s in event['sources']} == {first.url, second.url, first.url + '?utm_medium=rss'}
    assert {c['source_urls'][0] for c in event['pending_claims']} == {first.url, second.url}
    assert event['independent_corroboration']['status'] == 'not_established'
    assert set(event['independent_corroboration']['newsroom_candidates']) == {'bbc_mundo', 'dw'}


def test_distinct_events_with_shared_topic_are_not_combined():
    a = story(1, title='Elecciones en Francia: el gobierno anuncia nuevos resultados')
    b = story(2, title='Incendio en Francia: evacuaciones de varias localidades')
    assert len(group_events([a, b])) == 2


def test_official_source_never_self_corroborates():
    report = select_editorial([story('onu', source='onu', title='ONU anuncia que 500 personas recibieron ayuda')], now=NOW)
    event = report['selected'][0]
    assert event['sources'][0]['type'] == 'official'
    assert event['independent_corroboration']['newsroom_candidates'] == []
    assert all(c['status'] == 'pending_independent_verification' for c in event['pending_claims'])
    assert any('Fuente oficial' in r for r in event['pending_claims'][0]['reasons'])
    assert all(f['type'] == 'feed_metadata' for f in event['supported_facts'])
    assert event['publication_approved'] is False


def test_reliability_is_not_accepted_from_publisher_label_alone():
    item = story(1)
    item.url = 'https://bbc.com.evil.example/a'
    event = select_editorial([item], now=NOW)['selected'][0]
    assert event['sources'][0]['recognized_host'] is False
    assert event['independent_corroboration']['newsroom_candidates'] == []


def test_scores_explain_public_impact_recency_and_international_importance():
    high = story(1, title='Guerra y evacuaciones: incendio en la frontera internacional', age=1)
    low = story(2, title='Festival de música local', age=23)
    events = select_editorial([low, high], now=NOW)['selected']
    assert events[0]['title'] == high.title
    assert events[0]['score'] > events[1]['score']
    assert events[0]['score'] == round(sum(events[0]['score_components'].values()), 2)
    assert 0 <= events[0]['score'] <= 100


def test_input_is_not_mutated():
    items = [story(1), story(2)]
    before = deepcopy(items)
    select_editorial(items, now=NOW)
    assert items == before


def script_for(event):
    claim = event['pending_claims'][0]
    return {'event_id': event['event_id'], 'duration_seconds': 60, 'scenes': [
        {'id': 'intro', 'start_seconds': 0, 'end_seconds': 60,
         'narration_es': 'Borrador de prueba que requiere revisión editorial.',
         'claim_ids': [claim['id']], 'source_urls': claim['source_urls'],
         'subtitles': [{'start_seconds': 0, 'end_seconds': 5, 'text': 'Borrador en revisión'}],
         'animation': {'technique': 'typography', 'description': 'Texto original local',
                       'factual_claim_ids': [claim['id']]}}]}


def test_script_contract_duration_subtitles_and_traceability():
    event = select_editorial([story(1)], now=NOW)['selected'][0]
    script = script_for(event)
    validated = validate_script(script, event)
    assert validated.language == 'es'
    assert validated.publication_approved is False
    assert validated.editorial_status == 'draft'
    assert json.loads(Path('schemas/editorial-script.schema.json').read_text()) == EditorialScript.model_json_schema()


@pytest.mark.parametrize('mutation', ['short', 'long', 'subtitle', 'gap', 'claim', 'url', 'animation', 'publish'])
def test_invalid_scripts_rejected(mutation):
    event = select_editorial([story(1)], now=NOW)['selected'][0]
    data = script_for(event)
    scene = data['scenes'][0]
    if mutation == 'short': data['duration_seconds'] = 44
    elif mutation == 'long': data['duration_seconds'] = 76
    elif mutation == 'subtitle': scene['subtitles'][0]['end_seconds'] = 61
    elif mutation == 'gap': scene['start_seconds'] = 1
    elif mutation == 'claim': scene['claim_ids'] = ['invented']
    elif mutation == 'url': scene['source_urls'] = ['https://invented.example/a']
    elif mutation == 'animation': scene['animation']['factual_claim_ids'] = ['invented']
    elif mutation == 'publish': data['publication_approved'] = True
    with pytest.raises((ValueError, ValidationError)):
        validate_script(data, event)


def test_cli_offline_ranking_dossiers(tmp_path, monkeypatch):
    import pipeline
    from techslop.db import init_db, upsert_story
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    init_db()
    from datetime import datetime
    current = story(1)
    current.published_at = datetime.now(timezone.utc) - timedelta(hours=1)
    upsert_story(current)
    runner = CliRunner()
    report = runner.invoke(pipeline.cli, ['editorial', '--json'])
    assert report.exit_code == 0, report.output
    parsed = json.loads(report.output)
    assert len(parsed['selected']) == 1
    assert parsed['selected'][0]['sources'][0]['url'] == current.url
    text = runner.invoke(pipeline.cli, ['editorial', '--dossiers'])
    assert text.exit_code == 0
    assert 'pending_claims' in text.output


def test_same_policy_and_its_international_reaction_are_grouped():
    policy = story(1, source='dw', title='Trump exime a Rusia de nuevas sanciones que aprobó el Congreso de Estados Unidos')
    reaction = story(2, title='Ucrania lamenta la decisión de Trump sobre las sanciones a Rusia y Moscú la califica de histórica')
    assert len(group_events([policy, reaction])) == 1


def test_available_low_scoring_category_is_not_squeezed_out():
    candidates = [story(i, title=f'Guerra y ataque internacional número {i}', source='bbc_mundo' if i % 2 else 'dw', category='politica_internacional') for i in range(12)]
    science = story('science', title='La vida de los animales', category='ciencia', age=23)
    report = select_editorial(candidates + [science], now=NOW)
    assert any(e['category'] == 'ciencia' for e in report['selected'])


def test_documented_template_matches_structural_contract():
    data = json.loads(Path('schemas/editorial-script.example.json').read_text())
    assert EditorialScript.model_validate(data).duration_seconds == 60
