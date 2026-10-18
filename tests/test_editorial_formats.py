from __future__ import annotations
from copy import deepcopy
from datetime import timedelta
import pytest
from techslop.editorial.script_format import EditorialScript, duration_bounds
from techslop.editorial.drafts import prepare_draft
from techslop.editorial.selection import select_editorial
from tests.test_tech_business import story, NOW


def inputs():
    dossier = select_editorial([story(1)], now=NOW, profile='tech_business')['selected'][0]
    claim = dossier['pending_claims'][0]
    copy = [{'section': section, 'narration_es': 'Texto sintético para comprobar el contrato, no noticia real.',
             'claim_ids': [claim['id']], 'source_urls': claim['source_urls']}
            for section in ['event', 'context', 'consequences', 'closing']]
    copy[-1]['conditional_outlook_es'] = 'Si se confirma el anuncio, podría cambiar la oferta; conviene revisar su disponibilidad.'
    return dossier, copy


@pytest.mark.parametrize('format,bounds', [('quick',(30,45)), ('explained',(60,75))])
def test_offline_formats_traceability_and_boundaries(format, bounds):
    dossier, copy = inputs()
    data = prepare_draft(dossier, copy, format)
    script = EditorialScript.model_validate(data)
    assert duration_bounds(script) == bounds
    assert script.publication_approved is False
    assert script.editorial_status == 'draft'
    assert {s.section for s in script.scenes} == {'event','context','consequences','closing'}
    for duration in [bounds[0], bounds[1]]:
        changed = deepcopy(data)
        for s in changed['scenes']:
            factor = duration/data['duration_seconds']
            s['start_seconds'] *= factor
            s['end_seconds'] *= factor
            for sub in s['subtitles']:
                sub['start_seconds'] *= factor
                sub['end_seconds'] *= factor
        changed['duration_seconds'] = duration
        assert EditorialScript.model_validate(changed)
    data['format'] = 'explained' if format == 'quick' else 'quick'
    with pytest.raises(ValueError):
        EditorialScript.model_validate(data)


def test_no_invented_sources_or_certain_forecasts():
    dossier, copy = inputs()
    copy[-1]['conditional_outlook_es'] = 'Las ventas subirán inevitablemente.'
    with pytest.raises(ValueError, match='conditional'):
        prepare_draft(dossier, copy, 'quick')
    dossier, copy = inputs()
    copy[0]['source_urls'] = ['https://inventada.invalid/noticia']
    with pytest.raises(ValueError, match='URLs'):
        prepare_draft(dossier, copy, 'quick')


def test_novelty_uses_only_dated_profile_history_and_not_duplicates():
    fresh = story('new')
    old = story('old')
    old.published_at = NOW - timedelta(days=2)
    report = select_editorial([old, fresh], now=NOW, profile='tech_business')
    event = report['selected'][0]
    assert event['score_components']['novelty'] == 2
    assert event['novelty_basis']['prior_event_urls'] == [old.url]
    assert event['editorial_questions']['que_podria_pasar_despues']['status'] == 'conditional_analysis_only'
    old.raw_data['published_at_reported'] = False
    assert select_editorial([old, fresh], now=NOW, profile='tech_business')['selected'][0]['score_components']['novelty'] == 10


def test_diversity_never_displaces_more_than_eight_points(monkeypatch):
    import techslop.editorial.selection as module
    original = module.dossier
    def scored(group, now, profile):
        event = original(group, now, profile)
        event['score'] = 90 if group[0].id != 'weak' else 10
        return event
    monkeypatch.setattr(module, 'dossier', scored)
    items = [story(str(i), title=f'OpenAI software release {i}') for i in range(4)]
    items.append(story('weak', title='Pequeña empresa local', source='xataka', category='empresas_negocios'))
    report = select_editorial(items, now=NOW, limit=3, profile='tech_business')
    assert all(e['score'] == 90 for e in report['selected'])
    assert report['warnings']


@pytest.mark.parametrize('format,durations', [('quick',[8,9,10,11]),('explained',[15,16,17,18])])
def test_renderer_accepts_new_measured_durations_but_retains_review_gate(format, durations):
    from techslop.render.adapter import adapt, word_timestamps
    dossier, copy = inputs()
    data = prepare_draft(dossier, copy, format)
    presentation = {s['id']: {'kind': 'intro' if i == 0 else 'closing' if i == 3 else 'explanation',
                               'title': 'Prueba sintética', 'text': s['narration_es']}
                    for i, s in enumerate(data['scenes'])}
    with pytest.raises(ValueError, match='reviewed'):
        adapt(data, dossier, presentation, durations, 'provided_voice')
    dossier['content_type'] = 'fictional_demonstration'
    script, plan = adapt(data, dossier, presentation, durations, 'provided_voice')
    assert plan.duration == sum(durations)
    words, mode = word_timestamps(script, plan, [[] for _ in durations])
    assert words
    assert max(w['end'] for w in words) <= sum(durations)
