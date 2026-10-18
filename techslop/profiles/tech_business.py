"""Bilingual technology/business triage; heuristics never establish factual truth."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import re
from techslop.ingest.categories import normalize
from techslop.models import Story

CATEGORIES = ('tecnologia_ia', 'empresas_negocios', 'economia_mercados', 'emprendimiento_innovacion')


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    language: str
    hosts: tuple[str, ...]
    publisher: str
    kind: str = 'newsroom'
    focused: bool = True
    default_category: str = 'empresas_negocios'
    path_prefix: str = ''


FEEDS = (
    Feed('openai_releases', 'https://github.com/openai/openai-python/releases.atom', 'en', ('github.com',), 'openai', 'company', default_category='tecnologia_ia', path_prefix='/openai/openai-python/'),
    Feed('typescript_releases', 'https://github.com/microsoft/TypeScript/releases.atom', 'en', ('github.com',), 'microsoft', 'company', default_category='tecnologia_ia', path_prefix='/microsoft/TypeScript/'),
    Feed('xataka', 'https://www.xataka.com/tag/feeds/latest', 'es', ('xataka.com',), 'webedia'),
    Feed('genbeta', 'https://www.genbeta.com/tag/feeds/latest', 'es', ('genbeta.com',), 'webedia'),
    Feed('eleconomista', 'https://www.eleconomista.es/rss/rss-economia.php', 'es', ('eleconomista.es',), 'eleconomista'),
    Feed('ars_technica', 'https://feeds.arstechnica.com/arstechnica/index', 'en', ('arstechnica.com',), 'conde_nast'),
    Feed('the_verge', 'https://www.theverge.com/rss/index.xml', 'en', ('theverge.com',), 'vox_media'),
    Feed('google_blog', 'https://blog.google/rss/', 'en', ('blog.google',), 'google', 'company'),
    Feed('microsoft_blog', 'https://blogs.microsoft.com/feed/', 'en', ('blogs.microsoft.com',), 'microsoft', 'company'),
    Feed('ecb', 'https://www.ecb.europa.eu/rss/press.html', 'en', ('ecb.europa.eu',), 'ecb', 'official'),
    Feed('ft', 'https://www.ft.com/rss/home', 'en', ('ft.com',), 'financial_times', focused=False),
    Feed('bbc_mundo', 'https://feeds.bbci.co.uk/mundo/rss.xml', 'es', ('bbc.com', 'bbci.co.uk'), 'bbc', focused=False),
    Feed('dw', 'https://rss.dw.com/rdf/rss-sp-all', 'es', ('dw.com',), 'dw', focused=False),
)

RULES = {
    'emprendimiento_innovacion': r'startup\w*|emprend\w*|venture capital|funding round|seed funding|capital riesgo|innovaci\w*|innovation|ronda de financi\w*',
    'economia_mercados': r'econom\w*|inflaci\w*|inflation|mercado\w*|market\w*|bank\w*|banco\w*|interest rates?|tipos de interes|arancel\w*|tariff\w*|sancion\w*|sanctions?|petroleo|oil|pib|gdp|bolsa|stocks?|cost[oe] de vida',
    'tecnologia_ia': r'tecnolog\w*|technology|tech|inteligencia artificial|artificial intelligence|ia|ai|llm\w*|software|chips?|semiconductor\w*|ciber\w*|cyber\w*|robot\w*|cloud|nvidia|openai|chatgpt|iphone|internet',
    'empresas_negocios': r'empres\w*|negocio\w*|business\w*|compania\w*|company|companies|adquisici\w*|acquisition\w*|merger\w*|fusion\w*|earnings|beneficios? (?:netos|trimestrales|empresariales)|profits?|despido\w*|layoff\w*|empleo|trabajo|workplace|microsoft|google|amazon|apple|meta',
}


def classify(title: str, summary: str = '', tags: list[str] | None = None, *, focused: bool = True) -> str | None:
    # Headline evidence wins over broad feed tags and tangential summary words.
    for text in [normalize(title), normalize(' '.join([summary, *(tags or [])]))]:
        for category, pattern in RULES.items():
            if re.search(r'\b(?:' + pattern + r')\b', text):
                return category
    return 'empresas_negocios' if focused else None


def category_for(story: Story) -> str:
    meta = story.raw_data.get('profiles', {}).get('tech_business', {})
    return meta.get('category') if meta.get('category') in CATEGORIES else classify(story.title, focused=True)


def components(group: list[Story], now: datetime, reliability: float) -> tuple[dict, list[str]]:
    text = normalize(' '.join(s.title for s in group))
    tech = bool(re.search(r'\b(?:' + RULES['tecnologia_ia'] + r')\b', text))
    business = bool(re.search(r'\b(?:' + RULES['empresas_negocios'] + r')\b', text))
    economics = bool(re.search(r'\b(?:' + RULES['economia_mercados'] + r')\b', text))
    innovation = bool(re.search(r'\b(?:' + RULES['emprendimiento_innovacion'] + r')\b', text))
    hispanic = bool(re.search(r'\b(mexico|mexican\w*|espana|spain|spanish|latinoamerica|latin america|argentina|colombia|chile|peru|hispan\w*)\b', text))
    age = min((now-s.published_at).total_seconds()/3600 for s in group)
    scores = {'technological_impact': 20 if tech else 12 if innovation or any(category_for(s)=='tecnologia_ia' for s in group) else 3,
              'business_impact': 20 if business else 12 if tech or innovation else 4,
              'economic_relevance': 20 if economics else 10 if business else 4,
              'recency': round(20*max(0,1-age/24),2),
              'hispanic_relevance': 10 if hispanic else 6 if any(s.raw_data.get('language')=='es' for s in group) else 2,
              'source_reliability': round(10*reliability,2)}
    reasons = ['Indicadores léxicos bilingües; puntuación orientativa, no verificación']
    if hispanic: reasons.append('Referencia explícita a audiencia o regiones hispanohablantes')
    return scores, reasons


def content_kind(story: Story, source_type: str) -> str:
    text = normalize(story.title + ' ' + str(story.raw_data.get('summary','')))
    if re.search(r'\b(rumou?r\w*|unconfirmed|no confirmado|filtracion\w*|leaked|reportedly|segun fuentes)\b', text):
        return 'rumor'
    if source_type == 'company': return 'company_claim'
    if re.search(r'\b(analysis|analisis|opinion|editorial|why|por que|explainer)\b', normalize(story.title)):
        return 'analysis'
    if source_type == 'official': return 'official_claim'
    return 'reported_claim'


# Small transparent vocabulary: supports common bilingual event matches without
# translating the original article or pretending to be a semantic multilingual model.
EVENT_ALIASES = {
    'launches':'launch', 'launched':'launch', 'lanza':'launch', 'lanzamiento':'launch',
    'announces':'announce', 'anuncia':'announce', 'announced':'announce',
    'acquires':'acquire', 'compra':'acquire', 'adquiere':'acquire', 'acquisition':'acquire',
    'chips':'chip', 'ia':'ai', 'inteligencia':'intelligence', 'artificial':'artificial',
    'billion':'billion', 'millones':'million', 'models':'model', 'modelo':'model', 'modelos':'model',
    'funding':'funding', 'financiacion':'funding', 'investment':'investment', 'inversion':'investment',
}
STOP = set('the a an of to in for and with on its is as new el la los las de del al en para por con un una y su sus nuevo nueva'.split())


def related(first: Story, second: Story) -> bool:
    def words(title):
        normalized = re.sub(r'inteligencia artificial|artificial intelligence','ai',normalize(title))
        return {EVENT_ALIASES.get(t,t) for t in re.findall(r'\w+',normalized) if len(t)>1 and t not in STOP}
    a,b = words(first.title),words(second.title)
    shared = a & b
    def entities(title):
        # Preserve case-sensitive product names/version numbers as anchors.
        return {normalize(t) for t in re.findall(r'\b[A-Z][A-Za-z0-9.-]*\b',title)}
    anchors = (entities(first.title) & entities(second.title)) - STOP
    actions = shared & {'launch','announce','acquire','funding','investment'}
    # Different product versions must not collapse into a single story.
    versions_a = set(re.findall(r'\b\d+(?:\.\d+)*\b',first.title))
    versions_b = set(re.findall(r'\b\d+(?:\.\d+)*\b',second.title))
    if versions_a and versions_b and versions_a != versions_b: return False
    return len(shared)>=3 and bool(anchors) and bool(actions) and len(shared)/len(a|b)>=.3


def enrich_dossier(result: dict, group: list[Story], now: datetime) -> dict:
    lead = max(group,key=lambda s:(s.published_at,s.id))
    scores,reasons = components(group,now,max(s['reliability_prior'] for s in result['sources']))
    result.update(profile='tech_business', category=category_for(lead), score=round(sum(scores.values()),2),
                  score_components=scores,score_reasons=reasons,editorial_language='es',
                  original_language=lead.raw_data.get('language','und'),
                  requires_translation=any(s.raw_data.get('language')!='es' for s in group),
                  original_articles=[{'story_id':s.id,'title':s.title,'summary':s.raw_data.get('summary',''),
                                      'language':s.raw_data.get('language','und'),'url':s.url,
                                      'published_at':s.published_at.isoformat()} for s in group],
                  editorial_brief_es={'angle':'Explicar el impacto tecnológico, empresarial y económico para una audiencia hispanohablante.',
                                      'requirements':['Traducir al español sin alterar el original ni inventar datos.',
                                                      'Contrastar cifras, atribuir declaraciones empresariales y separar análisis de hechos.',
                                                      'Revisar contexto de México, España y Latinoamérica solo cuando haya evidencia.']},
                  verified_facts=[], verification_note='Los metadatos RSS no verifican hechos periodísticos.')
    from dataclasses import replace
    from hashlib import sha256
    from techslop.editorial.selection import plain
    originals = {}
    for story in group:
        records = story.raw_data.get('original_articles') or [{
            'story_id':story.id,'title':story.title,'source':story.source,'url':story.url,
            'summary':story.raw_data.get('summary',''),'language':story.raw_data.get('language','und'),
            'published_at':story.published_at.isoformat()}]
        for article in records:
            originals[(article['source'],article['url'])] = article
    result['original_articles'] = list(originals.values())
    result['requires_translation'] = any(a['language']!='es' for a in originals.values())
    result['pending_claims'] = []
    result['supported_facts'] = []
    for article in originals.values():
        source = next(s for s in result['sources'] if s['source']==article['source'] and s['url']==article['url'])
        role = content_kind(replace(lead,title=article['title'],raw_data={'summary':article['summary']}),source['type'])
        result['supported_facts'].append({'type':'feed_metadata','text':'Registro observado en RSS; no confirma el acontecimiento.',
                                          'headline':article['title'],'published_at':article['published_at'],
                                          'source_urls':[article['url']]})
        for kind,text in [('headline',article['title']),('rss_summary',plain(article['summary']))]:
            if not text:
                continue
            flags = ['Contrastar la afirmación con evidencia independiente; RSS no es verificación.']
            if re.search(r'\d',text): flags.append('Comprobar cifras y fechas originales.')
            if source['type']=='company': flags.append('Fuente empresarial interesada: no corrobora sus propias declaraciones.')
            if source['type']=='official': flags.append('Fuente oficial: no confirma independientemente sus propias declaraciones.')
            if role=='rumor': flags.append('Indicio de rumor/filtración: no presentar como hecho verificado.')
            if role=='analysis': flags.append('Análisis u opinión: no equivale a un hecho confirmado.')
            result['pending_claims'].append({'id':sha256(f"{article['story_id']}:{article['source']}:{kind}:{text}".encode()).hexdigest()[:16],
                                            'text':text,'kind':kind,'source_urls':[article['url']],
                                            'status':'pending_independent_verification','reasons':flags,
                                            'editorial_role':role,'original_language':article['language'],'editorial_language':'es'})
    result['claims_by_role'] = {role:[c['id'] for c in result['pending_claims'] if c['editorial_role']==role]
                               for role in ['company_claim','official_claim','rumor','analysis','reported_claim']}
    return result
