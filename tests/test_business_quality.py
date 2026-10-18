from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import httpx
import pytest
from techslop.profiles.business_quality import assess
from techslop.profiles.tech_business import components
from techslop.editorial.selection import select_editorial
from tests.test_tech_business import story, NOW


@pytest.mark.parametrize('title,summary', [
    ('Trump levanta sanciones contra Rusia', 'El presidente revoca restricciones por seguridad nacional.'),
    ('Empresario visita al presidente', 'Una reunión política sin resultados anunciados.'),
    ('Perdí mi cabello y diseño pelucas', 'Mi negocio personal ayuda a otras mujeres.'),
    ('El trabajo de los arqueólogos', 'Una expedición descubre piezas antiguas.'),
    ('Una celebridad habla de su familia', 'La muerte está siendo investigada por las autoridades.'),
    ('Police investigate a celebrity death', 'Investigators are investigating the case.'),
])
def test_rejects_weak_business_and_generic_political_connections(title, summary):
    item = story(1, title)
    item.raw_data['summary'] = summary
    before = deepcopy(item)
    report = select_editorial([item], now=NOW, profile='tech_business')
    assert report['selected'] == []
    assert report['quality_excluded'][0]['evidence_url'] == item.url
    assert item == before


@pytest.mark.parametrize('title', [
    'Microsoft anuncia despidos en su división de IA',
    'La startup obtiene financiación para fabricar chips',
    'New tariffs affect oil imports and consumer prices',
    'Regulador abre investigación antimonopolio contra Google',
    'La inflación reduce el consumo y crece la deuda',
    'Critical software vulnerability actively exploited: patch released',
])
def test_substantial_actions_described_by_source_remain_unverified(title):
    item = story(1, title)
    result = assess(item)
    assert result['eligible']
    assert result['consequence_status'] == 'source_description_unverified'
    event = select_editorial([item], now=NOW, profile='tech_business')['selected'][0]
    assert event['verified_facts'] == []
    assert event['independent_corroboration']['status'] == 'not_established'


def test_sdk_updates_archived_but_not_used_to_fill_ranking():
    item = replace(story('routine', 'v3.35.1'), source='openai_releases')
    item.raw_data['summary'] = 'Bug fixes for websocket byte reads.'
    item.url = 'https://github.com/openai/openai-python/releases/tag/v3.35.1'
    result = assess(item)
    assert result['penalties']['routine_software'] == -30
    assert result['eligible']  # technical archive, not necessarily editorial selection
    report = select_editorial([item], now=NOW, limit=15, profile='tech_business')
    assert report['selected'] == []
    assert report['quality_excluded'][0]['score'] < 35
    assert report['warnings']


def test_promo_downranked_and_ai_not_assumed_economic_impact():
    report = story(1, 'Apple launches AI model')
    promo = replace(report, id='promo', title='Sponsored: Apple launches AI model — buy now')
    clean, _ = components([report], NOW, .95)
    ads, _ = components([promo], NOW, .95)
    assert clean['business_impact'] == clean['economic_relevance'] == 0
    assert sum(ads.values()) == sum(clean.values()) - 25
    assert assess(promo)['promotional']


def test_scenarios_not_credited_as_realized_consequences():
    item = story(1, 'Microsoft podría aumentar su inversión en México')
    prospective, _ = components([item], NOW, .95)
    confirmed_wording = replace(item, title='Microsoft aumenta su inversión en México')
    reported, _ = components([confirmed_wording], NOW, .95)
    assert prospective['business_impact'] == 8
    assert reported['business_impact'] == 20
    assert assess(item)['consequence_status'] == 'scenario_or_analysis_unverified'
    # Neither wording establishes truth: the source claim remains pending.
    assert select_editorial([confirmed_wording], now=NOW, profile='tech_business')['selected'][0]['verified_facts'] == []


@pytest.mark.asyncio
async def test_focused_feed_no_longer_accepts_every_article(monkeypatch):
    import techslop.ingest.tech_business as module
    from techslop.profiles.tech_business import Feed
    monkeypatch.setattr(module, 'FEEDS', [Feed('xataka','https://www.xataka.com/rss','es',('xataka.com',),'webedia')])
    unrelated = story(1, 'Un deportista recuerda su infancia')
    unrelated.raw_data['summary'] = 'Una entrevista deportiva'
    relevant = story(2, 'Intel anuncia inversión en chips')
    factory = story(3, 'Factory closure confirmed in local manufacturing sector')
    async def fetch(*args, **kwargs):
        return [unrelated, relevant, factory]
    monkeypatch.setattr(module, 'fetch_feed', fetch)
    results = await module.fetch_tech_business()
    assert [s.id for s in results] == ['2', '3']
    assert results[-1].raw_data['profiles']['tech_business']['category'] == 'empresas_negocios'


@pytest.mark.asyncio
async def test_feed_diagnostics_follow_redirect_to_failure_without_losing_chain(monkeypatch):
    from techslop.ingest.international import fetch_feed
    def respond(request):
        if request.url.host == 'www.xataka.com':
            return httpx.Response(301, headers={'Location':'https://rss.example.org/feed'})
        return httpx.Response(403)
    factory = httpx.AsyncClient
    monkeypatch.setattr('techslop.ingest.international.httpx.AsyncClient',
                        lambda **kwargs: factory(transport=httpx.MockTransport(respond), **kwargs))
    diagnostics = []
    assert await fetch_feed('example','https://www.xataka.com/rss', diagnostics=diagnostics) == []
    result = diagnostics[0]
    assert result['http_status'] == 403
    assert result['responses'][0]['location'] == 'https://rss.example.org/feed'
    assert result['request_chain'] == ['https://www.xataka.com/rss','https://rss.example.org/feed']


@pytest.mark.asyncio
async def test_proxy_error_reports_safe_code_and_attempted_domain(monkeypatch):
    from techslop.ingest.international import fetch_feed
    def respond(request):
        raise httpx.ProxyError('403 Forbidden')
    factory = httpx.AsyncClient
    monkeypatch.setattr('techslop.ingest.international.httpx.AsyncClient',
                        lambda **kwargs: factory(transport=httpx.MockTransport(respond), **kwargs))
    diagnostics = []
    assert await fetch_feed('example','https://www.xataka.com/rss', diagnostics=diagnostics) == []
    assert diagnostics[0]['proxy_connect_status'] == 403
    assert diagnostics[0]['responses'] == []


def test_company_feature_without_described_impact_is_penalized_not_assumed_verified():
    item = replace(story(1, 'Introducing a new AI software feature'),
                   source='google_blog', url='https://blog.google/new-feature')
    quality = assess(item)
    assert quality['penalties']['low_impact_company_claim'] == -15
    assert quality['consequence_status'] == 'not_described'
    report = select_editorial([item], now=NOW, profile='tech_business')
    assert report['selected'] == []
    assert report['quality_excluded'][0]['score'] < 35
