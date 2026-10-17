from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from techslop.ingest.categories import classify
from techslop.ingest.international import configured_feeds, fetch_feed, fetch_international
from techslop.ingest.scorer import deduplicate, canonical_url
from techslop.ingest.sources import ingest_all
from techslop.models import Story

RSS = b'''<rss version="2.0"><channel><title>Noticias</title>
<item><title>Ciencia: una nueva vacuna</title><link>https://example.org/a</link>
<description>Resumen de prueba</description><pubDate>Sat, 17 Oct 2026 12:00:00 GMT</pubDate>
<category>Ciencia</category></item><item><title>Sin enlace</title></item>
<item><title>Invalida</title><link>javascript:alert(1)</link></item></channel></rss>'''


def story(url='https://example.org/a', title='Los gobiernos alcanzan un acuerdo internacional', source='bbc_mundo', score=1):
    return Story(url, title, url, source, score, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_rss_parses_fields_and_filters_bad_entries():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=RSS))
    factory = httpx.AsyncClient
    with patch('techslop.ingest.international.httpx.AsyncClient', side_effect=lambda **kwargs: factory(transport=transport, **kwargs)):
        results = await fetch_feed('bbc_mundo', 'https://example.org/rss')
    assert len(results) == 1
    assert results[0].title == 'Ciencia: una nueva vacuna'
    assert len(results[0].id) == 64
    assert results[0].published_at == datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
    assert results[0].raw_data['summary'] == 'Resumen de prueba'
    assert results[0].raw_data['tags'] == ['Ciencia']


@pytest.mark.parametrize('failure', ['403', 'timeout', 'invalid'])
@pytest.mark.asyncio
async def test_feed_failure_is_local(failure):
    def response(req):
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout', request=req)
        return httpx.Response(403 if failure == '403' else 200, content=b'not RSS')
    factory = httpx.AsyncClient
    with patch('techslop.ingest.international.httpx.AsyncClient', side_effect=lambda **kwargs: factory(transport=httpx.MockTransport(response), **kwargs)):
        assert await fetch_feed('dw', 'https://example.org/rss') == []


@pytest.mark.asyncio
async def test_international_continues_after_feed_block():
    async def fetch(name, url):
        return [] if name == 'dw' else [story(source=name)]
    with patch('techslop.ingest.international.fetch_feed', side_effect=fetch):
        assert len(await fetch_international()) == 2


@pytest.mark.asyncio
async def test_reddit_exception_does_not_cancel_other_sources(monkeypatch):
    import techslop.ingest.sources as sources
    monkeypatch.setattr(sources, 'SOURCES', [
        ('reddit', AsyncMock(side_effect=httpx.ProxyError('403'))),
        ('good', AsyncMock(return_value=[story()])),
    ])
    results = await ingest_all(profile='tech')
    assert len(results) == 1
    assert results[0].category == 'politica_internacional'


@pytest.mark.asyncio
async def test_reddit_blocked_subreddit_does_not_stop_remaining(monkeypatch):
    from techslop.ingest.reddit import fetch_reddit
    import techslop.ingest.reddit as reddit
    monkeypatch.setattr(reddit.settings, 'reddit_subreddits', 'blocked,working')
    def get(url, **kwargs):
        return httpx.Response(403 if '/blocked/' in url else 200, content=RSS, request=httpx.Request('GET', url))
    monkeypatch.setattr(reddit.httpx, 'get', get)
    results = await fetch_reddit()
    assert len(results) == 1


@pytest.mark.parametrize('title,expected', [
    ('Elecciones y diplomacia internacional', 'politica_internacional'),
    ('La inflación y el banco central', 'economia'),
    ('Científicos anuncian una vacuna', 'ciencia'),
    ('Nuevos semiconductores e inteligencia artificial', 'tecnologia'),
    ('Festival de música', 'actualidad_general'),
])
def test_spanish_categories(title, expected):
    assert classify(title) == expected


def test_dedup_keeps_all_sources_and_original_links():
    first = story('https://bbc.example/a?utm_source=rss', score=2)
    second = story('https://dw.example/b', source='dw')
    results = deduplicate([second, first])
    assert results == [first]
    assert {ref['url'] for ref in first.raw_data['sources']} == {first.url, second.url}


def test_canonical_url_preserves_semantic_query():
    assert canonical_url('https://example.org/a?id=2&utm_medium=rss#top') == 'https://example.org/a?id=2'
    assert len(deduplicate([story('https://example.org/a?utm_medium=rss'), story('https://example.org/a', title='Otra noticia')])) == 1


def test_distinct_developments_and_old_headlines_not_merged():
    a, b = story(), story('https://example.org/b')
    b.published_at -= timedelta(days=3)
    assert len(deduplicate([a, b])) == 2
    b.published_at = a.published_at
    b.title = 'Los gobiernos rechazan un acuerdo internacional'
    assert len(deduplicate([a, b])) == 2


def test_agencies_require_explicit_official_endpoint(monkeypatch):
    from techslop.config import settings
    monkeypatch.setattr(settings, 'authorized_agency_rss', '{}')
    assert not {'reuters', 'ap', 'afp'} & configured_feeds().keys()
    monkeypatch.setattr(settings, 'authorized_agency_rss', '{"reuters":"https://feeds.reuters.com/licensed"}')
    assert configured_feeds()['reuters'] == 'https://feeds.reuters.com/licensed'
    monkeypatch.setattr(settings, 'authorized_agency_rss', '{"ap":"https://ap.org.evil.example/rss"}')
    assert 'ap' not in configured_feeds()


def test_cli_ingest_persists_and_filters_without_network(tmp_path, monkeypatch):
    from click.testing import CliRunner
    import pipeline
    from techslop.db import get_all_stories
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    monkeypatch.setattr(pipeline.settings, 'authorized_agency_rss', '{}')
    factory = httpx.AsyncClient
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=RSS))
    with patch('techslop.ingest.international.httpx.AsyncClient', side_effect=lambda **kw: factory(transport=transport, **kw)):
        result = CliRunner().invoke(pipeline.cli, ['ingest', '--profile', 'international'])
    assert result.exit_code == 0, result.output
    stories = get_all_stories()
    assert len(stories) == 1
    assert stories[0].category == 'ciencia'
    assert {r['source'] for r in stories[0].raw_data['sources']} == {'bbc_mundo', 'dw', 'onu'}
    listed = CliRunner().invoke(pipeline.cli, ['list', '--category', 'ciencia'])
    assert listed.exit_code == 0
    assert 'vacuna' in listed.output
    empty = CliRunner().invoke(pipeline.cli, ['list', '--category', 'economia'])
    assert 'vacuna' not in empty.output
    corrected = CliRunner().invoke(pipeline.cli, ['classify', stories[0].id[:12], 'economia'])
    assert corrected.exit_code == 0
    with patch('techslop.ingest.international.httpx.AsyncClient', side_effect=lambda **kw: factory(transport=transport, **kw)):
        refreshed = CliRunner().invoke(pipeline.cli, ['ingest'])
    assert refreshed.exit_code == 0
    assert get_all_stories()[0].category == 'economia'


def test_cli_reports_total_failure(tmp_path, monkeypatch):
    from click.testing import CliRunner
    import pipeline
    monkeypatch.setattr(pipeline.settings, 'database_path', str(tmp_path / 'db'))
    monkeypatch.setattr(pipeline.settings, 'output_dir', str(tmp_path / 'out'))
    monkeypatch.setattr('techslop.ingest.sources.fetch_international', AsyncMock(return_value=[]))
    result = CliRunner().invoke(pipeline.cli, ['ingest', '--profile', 'international'])
    assert result.exit_code != 0
    assert 'No se captaron noticias' in result.output
