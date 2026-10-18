"""Conservative lexical triage of supplied RSS text, never economic fact inference."""
from __future__ import annotations
import re
from html import unescape
from techslop.ingest.categories import normalize
from techslop.models import Story

# Matches are descriptions found in a source, not verified consequences.
TECH = r'tecnolog\w*|technology|inteligencia artificial|artificial intelligence|ia|ai|llm\w*|software|chips?|semiconductor\w*|ciber\w*|cyber\w*|robot\w*|cloud|openai|chatgpt|internet|data cent\w*|centros? de datos'
ECONOMY = r'econom\w*|inflaci\w*|inflation|pib|gdp|tipos de interes|interest rates?|arancel\w*|tariff\w*|petroleo|oil|bolsa|stock market|cost[oe] de vida|recesion|recession|comercio|trade|export\w*|importaciones|deuda|debt'
BUSINESS_ACTION = r'acquisiti\w*|adquisici\w*|acquires?|merger\w*|fusion\w*|earnings|profits?|beneficios? netos|ingresos|revenues?|despido\w*|layoff\w*|quiebra|bankruptcy|inversion\w*|invest(?:s|ed|ing|ment|ments)?|financi\w*|funding|ronda de capital|antitrust|antimonopolio|competencia|competition|contrataci\w*|hiring|empleos|jobs|cierre de fabrica|factory closure'
CONSUMER = r'(?:sube\w*|baja\w*|aument\w*|reduc\w*|cambi\w*) (?:\w+ ){0,3}(?:precios|tarifas|costes|costos)|price (?:hike|cut|increase)|consumer protection|proteccion del consumidor|seguridad de (?:datos|usuarios)|data breach|brecha de datos|actively exploited|explotad[ao] activamente|critical vulnerability|vulnerabilidad critica'
POLITICS = r'trump|zelensk\w*|guerra|war|elecci\w*|election\w*|presidente|president|sancion\w*|sanctions?'
PROMO = r'sponsored|patrocinad\w*|compra ahora|buy now|affiliate|afiliad\w*|descuento\w*|oferta por tiempo|best deals|black friday|prime day'
ROUTINE = r'bug fixes|bugfix|correcciones de errores|patch release|actualizacion rutinaria|actualizacion menor|release notes|changelog'


def matches(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(r'\b(?:' + pattern + r')\b', text)))


def assess(story: Story) -> dict:
    summary = unescape(re.sub(r'<[^>]*>', ' ', str(story.raw_data.get('summary', ''))))
    text = normalize(story.title + ' ' + summary)
    evidence = {'technology': matches(TECH, text), 'economy': matches(ECONOMY, text),
                'business_action': matches(BUSINESS_ACTION, text), 'consumer': matches(CONSUMER, text)}
    scenarios = matches(r'podria\w*|pasaria|could|would|forecast\w*|proyecci\w*|escenario\w*|prevision\w*|predic\w*', text)
    concrete = bool(evidence['economy'] or evidence['business_action'] or evidence['consumer'])
    tech = bool(evidence['technology'])
    # An SDK version is technical material, even when its title is only a version.
    release_feed = story.source in {'openai_releases', 'typescript_releases'}
    routine = bool(release_feed or matches(ROUTINE, text) or re.fullmatch(r'v?\d+(?:\.\d+){1,3}', story.title.strip()))
    promo = bool(matches(PROMO, text))
    political_without_bridge = bool(matches(POLITICS, text)) and not concrete and not tech
    eligible = (tech or concrete or release_feed) and not political_without_bridge
    reasons = []
    if not eligible:
        reasons.append('Sin conexión sustancial descrita en el RSS; política o empresa mencionada no implica impacto económico.')
    penalties = {}
    if routine and not concrete:
        penalties['routine_software'] = -30
        reasons.append('Actualización rutinaria sin consecuencia sectorial o empresarial descrita: -30.')
    if promo:
        penalties['promotional'] = -25
        reasons.append('Indicios de contenido promocional o afiliación: -25.')
    from techslop.profiles.tech_business import FEEDS
    if not concrete and any(spec.name == story.source and spec.kind == 'company' for spec in FEEDS):
        penalties['low_impact_company_claim'] = -15
        reasons.append('Declaración empresarial sin consecuencias concretas descritas: -15.')
    if not concrete:
        penalties['no_described_consequence'] = -10
        reasons.append('No se describe una consecuencia económica, empresarial o para consumidores: -10; no se infiere.')
    if concrete:
        reasons.append('El RSS menciona un tema económico o una acción empresarial concreta; requiere verificar su alcance.')
    return {'eligible': bool(eligible), 'evidence_terms': evidence, 'penalties': penalties,
            'reasons': reasons, 'routine_software': routine, 'promotional': promo,
            'scenario_markers': scenarios,
            'consequence_status': ('scenario_or_analysis_unverified' if scenarios else 'source_description_unverified') if concrete else 'not_described',
            'evidence_url': story.url, 'assessment_scope': 'RSS title and summary only; not independent verification'}
