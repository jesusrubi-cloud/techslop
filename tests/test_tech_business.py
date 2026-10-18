from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch

from click.testing import CliRunner
import httpx
import pytest

from techslop.models import Story
from techslop.profiles.tech_business import classify, content_kind
from techslop.editorial.selection import select_editorial, group_events, source_info
from techslop.editorial.script_format import validate_script

NOW = datetime(2026,10,18,21,tzinfo=timezone.utc)


def story(n, title='Apple launches new AI model', source='the_verge', language='en', category=None):
    hosts={'the_verge':'www.theverge.com','xataka':'www.xataka.com','genbeta':'www.genbeta.com','google_blog':'blog.google','ecb':'www.ecb.europa.eu'}
    return Story(str(n),title,f'https://{hosts[source]}/story/{n}',source,1,NOW-timedelta(hours=2),
                 raw_data={'language':language,'summary':'Original summary', 'published_at_reported':True,
                           'category':'tecnologia','profiles':{'tech_business':{'category':category or classify(title)}}})


@pytest.mark.parametrize('title,expected',[
 ('OpenAI launches new AI model','tecnologia_ia'),
 ('Una startup anuncia ronda de financiación','emprendimiento_innovacion'),
 ('Inflación y mercados de México','economia_mercados'),
 ('Microsoft reports earnings and layoffs','empresas_negocios'),
 ('Intel lanza chips para inteligencia artificial','tecnologia_ia'),
 ('Banco central anuncia tipos de interés','economia_mercados'),
])
def test_bilingual_classification(title,expected):
    assert classify(title)==expected


def test_general_sources_are_filtered_and_false_friends_not_business():
    assert classify('Demichelis y Kompany: de compañeros a rivales en Bundesliga',focused=False) is None
    assert classify('Qué beneficios tuvo comer verduras para mi cuerpo',focused=False) is None
    assert classify('Música y deportes',focused=False) is None
    assert classify('Mi historia','El negocio de pelucas crece',focused=False)=='empresas_negocios'


def test_english_spanish_same_event_preserves_sources_and_originals():
    a=story(1)
    b=story(2,'Apple lanza nuevo modelo de IA',source='xataka',language='es')
    report=select_editorial([a,b],now=NOW,profile='tech_business')
    assert len(report['selected'])==1
    event=report['selected'][0]
    assert {s['url'] for s in event['sources']}=={a.url,b.url}
    assert {x['title'] for x in event['original_articles']}=={a.title,b.title}
    assert event['requires_translation'] is True
    assert event['editorial_language']=='es'
    assert event['verified_facts']==[]
    assert event['independent_corroboration']['status']=='not_established'


def test_different_product_versions_do_not_merge():
    a=story(1,'Apple launches iPhone 17')
    b=story(2,'Apple lanza iPhone 16',source='xataka',language='es')
    assert len(group_events([a,b],profile='tech_business'))==2


def test_source_ownership_is_not_independent_corroboration():
    assert source_info('xataka','https://www.xataka.com/a')['independence_group']=='webedia'
    assert source_info('genbeta','https://www.genbeta.com/a')['independence_group']=='webedia'
    assert source_info('google_blog','https://blog.google/a')['type']=='company'
    assert source_info('ecb','https://www.ecb.europa.eu/a')['type']=='official'
    assert source_info('google_blog','https://blog.google.evil.example/a')['type']=='unverified'


@pytest.mark.parametrize('title,kind',[
 ('Rumor: new AI model reportedly launches soon','rumor'),
 ('Why AI changes work','analysis'),
 ('Análisis: nuevas empresas','analysis'),
 ('New model launched','reported_claim'),
])
def test_rumor_analysis_and_reports_are_distinct(title,kind):
    assert content_kind(story(1,title),'newsroom')==kind


def test_company_claims_are_never_verified_by_their_issuer():
    event=select_editorial([story(1,source='google_blog')],now=NOW,profile='tech_business')['selected'][0]
    assert event['claims_by_role']['company_claim']
    assert event['independent_corroboration']['newsroom_candidates']==[]
    assert all(c['status']=='pending_independent_verification' for c in event['pending_claims'])
    assert any('empresarial interesada' in r for r in event['pending_claims'][0]['reasons'])


def test_profiles_are_isolated_and_selection_does_not_mutate_originals():
    business=story(1)
    international=deepcopy(business);international.id='other';international.raw_data.pop('profiles')
    before=deepcopy([business,international])
    tech=select_editorial([business,international],now=NOW,profile='tech_business')
    general=select_editorial([business,international],now=NOW)
    assert tech['eligible_stories']==1
    assert general['eligible_stories']==1
    assert [business,international]==before


def test_business_score_explains_all_dimensions_and_hispanic_bonus():
    a=story(1,'Microsoft AI inversión en México y economía',language='es')
    b=story(2,'A product review')
    events=select_editorial([a,b],now=NOW,profile='tech_business')['selected']
    top=next(e for e in events if e['title']==a.title)
    assert set(top['score_components'])=={'technological_impact','business_impact','economic_relevance','recency','hispanic_relevance','source_reliability'}
    assert top['score_components']['hispanic_relevance']==10
    assert top['score']==round(sum(top['score_components'].values()),2)
    assert top['score']<=100


@pytest.mark.asyncio
async def test_profile_fetches_bilingual_rss_without_network(monkeypatch):
    import techslop.ingest.tech_business as ingest
    from techslop.profiles.tech_business import Feed
    monkeypatch.setattr(ingest,'FEEDS',[
      Feed('the_verge','https://www.theverge.com/rss/index.xml','en',('theverge.com',),'vox_media'),
      Feed('xataka','https://www.xataka.com/tag/feeds/latest','es',('xataka.com',),'webedia')])
    payload=b'<rss><channel><title>RSS</title><item><title>Apple launches AI model</title><link>https://www.theverge.com/a</link><description>Original</description><pubDate>Sun, 18 Oct 2026 20:00:00 GMT</pubDate></item></channel></rss>'
    factory=httpx.AsyncClient
    with patch('techslop.ingest.international.httpx.AsyncClient',side_effect=lambda **kw:factory(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=payload)),**kw)):
        results=await ingest.fetch_tech_business()
    assert {s.raw_data['language'] for s in results}=={'en','es'}
    assert all(s.title=='Apple launches AI model' for s in results)
    assert all(s.raw_data['profiles']['tech_business']['category']=='tecnologia_ia' for s in results)
    assert all(d['status']=='ok' for d in ingest.LAST_FETCH_REPORT)


def test_database_preserves_both_profiles_and_manual_category(tmp_path,monkeypatch):
    from techslop.db import init_db,upsert_story,get_all_stories
    monkeypatch.setattr('techslop.config.settings.database_path',str(tmp_path/'db'))
    init_db()
    original=story(1);original.raw_data.pop('profiles');original.raw_data['category']='economia'
    upsert_story(original)
    business=story(1);upsert_story(business)
    loaded=get_all_stories()[0]
    assert set(loaded.raw_data['profiles'])=={'international','tech_business'}
    assert loaded.category=='economia'
    loaded.raw_data['profiles']['tech_business']={'category':'empresas_negocios','category_manual':True}
    upsert_story(loaded)
    upsert_story(story(1))
    assert get_all_stories()[0].raw_data['profiles']['tech_business']['category']=='empresas_negocios'


def test_business_dossier_stays_compatible_with_script_contract():
    event=select_editorial([story(1)],now=NOW,profile='tech_business')['selected'][0]
    claim=event['pending_claims'][0]
    data={'event_id':event['event_id'],'duration_seconds':60,'scenes':[{'id':'scene','start_seconds':0,'end_seconds':60,
      'narration_es':'Borrador en español pendiente de verificar.','claim_ids':[claim['id']],'source_urls':claim['source_urls'],
      'subtitles':[{'start_seconds':0,'end_seconds':60,'text':'Borrador'}],
      'animation':{'technique':'typography','description':'Original local','factual_claim_ids':[claim['id']]}}]}
    assert validate_script(data,event).publication_approved is False


def test_cli_editorial_and_list_profile_arguments(tmp_path,monkeypatch):
    import pipeline
    from techslop.db import init_db,upsert_story
    monkeypatch.setattr(pipeline.settings,'database_path',str(tmp_path/'db'))
    monkeypatch.setattr(pipeline.settings,'output_dir',str(tmp_path/'out'))
    init_db();item=story(1);item.published_at=datetime.now(timezone.utc)-timedelta(hours=1);upsert_story(item)
    runner=CliRunner()
    report=runner.invoke(pipeline.cli,['editorial','--profile','tech_business','--json'])
    assert report.exit_code==0,report.output
    assert json.loads(report.output)['selected'][0]['category']=='tecnologia_ia'
    listing=runner.invoke(pipeline.cli,['list','--profile','tech_business','--category','tecnologia_ia'])
    assert 'Apple' in listing.output
    general=runner.invoke(pipeline.cli,['editorial','--profile','international','--json'])
    assert json.loads(general.output)['selected']==[]


def test_diversity_counts_related_publishers_together():
    categories=['tecnologia_ia','empresas_negocios','economia_mercados','emprendimiento_innovacion']
    items=[story(f'{source}-{i}',f'Informe independiente {source} {i}',source=source,category=category)
           for source in ['xataka','genbeta','the_verge','ecb'] for i,category in enumerate(categories)]
    report=select_editorial(items,now=NOW,profile='tech_business')
    assert len(report['selected'])==10
    assert report['distribution']['publisher_groups']['webedia']<=4
    assert len(report['distribution']['categories'])==4


def test_business_ranking_excludes_stale_and_future_items():
    old=story(1);old.published_at=NOW-timedelta(hours=25)
    future=story(2);future.published_at=NOW+timedelta(minutes=1)
    fresh=story(3)
    report=select_editorial([old,future,fresh],now=NOW,profile='tech_business')
    assert report['eligible_stories']==1
    assert len(report['selected'])==1
    assert report['warnings']


@pytest.mark.asyncio
async def test_blocked_business_feed_does_not_cancel_working_source(monkeypatch):
    import techslop.ingest.tech_business as ingest
    from techslop.profiles.tech_business import Feed
    monkeypatch.setattr(ingest,'FEEDS',[
        Feed('xataka','https://www.xataka.com/rss','es',('xataka.com',),'webedia'),
        Feed('the_verge','https://www.theverge.com/rss','en',('theverge.com',),'vox_media')])
    async def fetch(name,url,**kwargs):
        if name=='xataka':raise httpx.ProxyError('403')
        return [story('english')]
    monkeypatch.setattr(ingest,'fetch_feed',fetch)
    result=await ingest.fetch_tech_business()
    assert len(result)==1
    assert any(d['source']=='xataka' and d['status']=='failed' for d in ingest.LAST_FETCH_REPORT)


def test_profile_category_can_be_corrected_again_without_changing_international(tmp_path,monkeypatch):
    import pipeline
    from techslop.db import init_db,upsert_story,get_all_stories
    monkeypatch.setattr(pipeline.settings,'database_path',str(tmp_path/'db'))
    monkeypatch.setattr(pipeline.settings,'output_dir',str(tmp_path/'out'))
    init_db();item=story('1');upsert_story(item)
    runner=CliRunner()
    for category in ['empresas_negocios','emprendimiento_innovacion']:
        result=runner.invoke(pipeline.cli,['classify',item.id,category,'--profile','tech_business'])
        assert result.exit_code==0,result.output
    saved=get_all_stories()[0]
    assert saved.raw_data['profiles']['tech_business']['category']=='emprendimiento_innovacion'
    assert saved.category=='tecnologia'


def test_release_source_requires_the_official_repository_path():
    assert source_info('openai_releases','https://github.com/openai/openai-python/releases/tag/v3.0')['type']=='company'
    assert source_info('openai_releases','https://github.com/another-user/openai-python/releases/tag/v3.0')['type']=='unverified'
    assert source_info('typescript_releases','https://github.com/Microsoft/typescript/releases/tag/v5.0')['type']=='company'


def test_memory_leak_fix_is_not_automatically_a_rumor():
    assert content_kind(story(1,'Fix memory leaks in SDK'),'company')=='company_claim'


def test_dedup_and_database_retain_distinct_original_summaries(tmp_path,monkeypatch):
    from techslop.db import init_db,upsert_story,get_all_stories
    monkeypatch.setattr('techslop.config.settings.database_path',str(tmp_path/'db'))
    init_db()
    title='Apple announces important new artificial intelligence model'
    first=story('first',title,source='the_verge');first.raw_data['summary']='Original English summary'
    second=story('second',title,source='xataka',language='es');second.raw_data['summary']='Resumen original en español'
    upsert_story(first);upsert_story(second)
    items=get_all_stories()
    assert len(items)==1
    report=select_editorial(items,now=NOW,profile='tech_business')
    event=report['selected'][0]
    assert {a['summary'] for a in event['original_articles']}=={'Original English summary','Resumen original en español'}
    assert {c['text'] for c in event['pending_claims'] if c['kind']=='rss_summary'}=={'Original English summary','Resumen original en español'}
