"""Explainable RSS triage. Scores and event matches are editorial suggestions, not fact checks."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html import unescape
import math
import re

from techslop.ingest.categories import CATEGORIES, classify, normalize
from techslop.ingest.scorer import references, same_story
from techslop.models import Story

# Source identity is checked against its URL, not just a feed-supplied label.
SOURCE_HOSTS = {
    "bbc_mundo": ("bbc.com", "bbci.co.uk"), "dw": ("dw.com",),
    "onu": ("news.un.org",), "reuters": ("reuters.com", "reutersconnect.com"),
    "ap": ("apnews.com", "ap.org"), "afp": ("afp.com", "afpforum.com"),
}
OFFICIAL = {"onu"}
STOP = set('el la los las un una unos unas de del al a en por para que con sin su sus se es son y o como tras sobre entre mas menos nuevo nueva nuevos nuevas quien quienes cuando donde hay hasta este esta estos estas dia dias jornada ultimo ultimos primera primer'.split())
ALIASES = {
    "papa": "pontifice", "leon": "pontifice", "pontifice": "pontifice",
    "hospitalaria": "hospital", "hospitalario": "hospital",
    "sale": "alta", "regresa": "alta", "regresara": "alta",
    "protestas": "protesta", "multitudinarias": "multitudinaria",
    "sanciones": "sancion", "rusia": "rusia", "rusas": "rusia",
    "incendios": "incendio", "elecciones": "eleccion",
}


def plain(text: str) -> str:
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', text))).strip()


def tokens(title: str) -> set[str]:
    return {ALIASES.get(t, t) for t in re.findall(r'\b\w+\b', normalize(title))
            if len(t) > 2 and t not in STOP}


def related(first: Story, second: Story) -> bool:
    if same_story(first, second):
        return True
    a, b = tokens(first.title), tokens(second.title)
    overlap = a & b
    if not a or not b:
        return False
    # Require shared entity candidates (capitalized words, excluding stopwords)
    # and multiple content words. Complete-link clustering prevents topic chaining.
    def entities(title, skip_first=False):
        words = re.findall(r'\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]*', title)
        return tokens(' '.join(words[1:] if skip_first else words))
    entity_overlap = ((entities(first.title) & entities(second.title, True))
                      | (entities(first.title, True) & entities(second.title)))
    similarity = len(overlap) / len(a | b)
    return (len(overlap) >= 3 and bool(entity_overlap)
            and (similarity >= 0.25
                 or (similarity >= 0.18 and (len(entity_overlap) >= 2 or len(overlap) >= 4))))


def group_events(stories: list[Story]) -> list[list[Story]]:
    groups: list[list[Story]] = []
    for story in sorted(stories, key=lambda s: (s.published_at, s.id), reverse=True):
        group = next((g for g in groups if all(related(story, other) for other in g)), None)
        if group is None:
            groups.append([story])
        else:
            group.append(story)
    return groups


def source_info(source: str, url: str) -> dict:
    from urllib.parse import urlsplit
    host = (urlsplit(url).hostname or '').lower()
    recognized = any(host == h or host.endswith('.' + h) for h in SOURCE_HOSTS.get(source, ()))
    official = source in OFFICIAL and recognized
    return {"source": source, "url": url, "recognized_host": recognized,
            "type": "official" if official else "newsroom" if recognized else "unverified",
            "independence_group": source if recognized else "unknown",
            "reliability_prior": 0.95 if recognized and not official else 0.85 if official else 0.35}


def event_sources(group: list[Story]) -> list[dict]:
    sources = {}
    for story in group:
        for ref in references(story):
            key = (ref['source'], ref['url'])
            sources[key] = source_info(*key)
    return list(sources.values())


def components(group: list[Story], now: datetime) -> tuple[dict, list[str]]:
    text = normalize(' '.join(s.title for s in group))
    reasons = []
    impact = 8
    for pattern, points, reason in [
        (r'\b(guerra|ataque|tiroteo|muert\w*|asesinat\w*|conflicto|mina|explosion)\b', 15, 'Seguridad y vidas humanas'),
        (r'\b(salud|vacuna\w*|cancer|hospital\w*|sismo|incendio\w*|evacua\w*|educacion)\b', 12, 'Salud, servicios o riesgos públicos'),
        (r'\b(economia|inflacion|sancion\w*|petrol\w*|costo de vida|empleo|trabajo|protesta\w*)\b', 10, 'Medios de vida y alcance social'),
    ]:
        if re.search(pattern, text):
            impact += points
            reasons.append(reason)
    impact = min(35, impact)
    age = min((now - s.published_at).total_seconds() / 3600 for s in group)
    recency = round(25 * max(0, 1 - age / 24), 2)
    international = 8
    if re.search(r'\b(guerra|sancion\w*|onu|ormuz|gaza|diplomac\w*|internacional|frontera\w*)\b', text):
        international = 20
        reasons.append('Indicadores de alcance internacional')
    elif re.search(r'\b(francia|alemania|rusia|ucrania|india|japon|mexico|estados unidos|ee\.uu|vaticano)\b', text):
        international = 14
        reasons.append('Acontecimiento en otro país; alcance global por revisar')
    reliability = round(20 * max(s['reliability_prior'] for s in event_sources(group)), 2)
    return {"public_impact": impact, "recency": recency,
            "international_importance": international, "source_reliability": reliability}, reasons


def dossier(group: list[Story], now: datetime) -> dict:
    lead = max(group, key=lambda s: (s.published_at, s.id))
    scores, reasons = components(group, now)
    sources = event_sources(group)
    # Distinct publishers covering a topic do not establish independent evidence
    # for a particular assertion (syndication and shared press releases are possible).
    assertions = []
    for story in group:
        for kind, text in [('headline', story.title), ('rss_summary', plain(story.raw_data.get('summary', '')))]:
            if not text:
                continue
            attribution = source_info(story.source, story.url)
            flags = ['Requiere contrastar con evidencia independiente; RSS no es verificación.']
            if re.search(r'\d', text):
                flags.append('Comprobar cifras, fechas y su contexto.')
            if re.search(r'\b(dijo|afirma|segun|declara|anuncia|acusa|califica|considera)\b|["“”]', normalize(text)):
                flags.append('Declaración atribuida: comprobar cita, emisor y contexto.')
            if attribution['type'] == 'official':
                flags.append('Fuente oficial: no confirma de forma independiente sus propias declaraciones.')
            claim_id = sha256(f'{story.id}:{kind}:{text}'.encode()).hexdigest()[:16]
            assertions.append({"id": claim_id, "text": text, "kind": kind,
                               "source_urls": [story.url], "status": "pending_independent_verification",
                               "reasons": flags})
    evidence = [{"type": "feed_metadata", "text": f"{s.source} publicó este titular en su RSS.",
                 "headline": s.title, "published_at": s.published_at.isoformat(),
                 "source_urls": [s.url], "scope": "Existencia del registro RSS; no confirma el acontecimiento."}
                for s in group]
    category = lead.category if lead.raw_data.get('category_manual') else classify(lead.title)
    if category == 'actualidad_general' and not lead.raw_data.get('category_manual'):
        category = lead.category
    if category not in CATEGORIES:
        category = 'actualidad_general'
    return {
        "event_id": sha256('|'.join(sorted(s.id for s in group)).encode()).hexdigest()[:16],
        "title": lead.title, "summary": plain(lead.raw_data.get('summary', '')) or lead.title,
        "summary_type": "attributed_rss_excerpt_not_verified_synthesis", "summary_source_url": lead.url,
        "category": category, "published_at": lead.published_at.isoformat(),
        "primary_source": lead.source, "sources": sources,
        "story_ids": [s.id for s in group], "grouping": "lexical_candidate_requires_editorial_review",
        "score": round(sum(scores.values()), 2), "score_components": scores, "score_reasons": reasons,
        "supported_facts": evidence, "pending_claims": assertions,
        "independent_corroboration": {"status": "not_established",
             "newsroom_candidates": sorted({s['independence_group'] for s in sources if s['type'] == 'newsroom'}),
             "note": "Cobertura múltiple no prueba independencia ni acuerdo sobre una afirmación."},
        "review_required": True, "publication_approved": False,
    }


def select_editorial(stories: list[Story], *, now: datetime | None = None, limit: int = 10) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError('now must include a timezone')
    if not 1 <= limit <= 50:
        raise ValueError('limit must be between 1 and 50')
    cutoff = now - timedelta(hours=24)
    recent = [s for s in stories if s.published_at.utcoffset() is not None
              and cutoff <= s.published_at <= now
              and s.raw_data.get('published_at_reported') is True]
    candidates = [dossier(g, now) for g in group_events(recent)]
    candidates.sort(key=lambda d: (-d['score'], d['event_id']))
    selected = []
    source_counts, category_counts = Counter(), Counter()
    source_cap = category_cap = max(1, math.ceil(limit * 0.4))
    warnings = []
    # A 40% cap where feasible; relax minimally to fill requested slots,
    # recording every relaxation. Never invent extra sources/categories/events.
    while candidates and len(selected) < limit:
        source_eligible = [d for d in candidates if source_counts[d['primary_source']] < source_cap]
        if not source_eligible:
            source_cap += 1
            warnings.append(f'Cuota por fuente relajada a {source_cap}: faltan fuentes distintas elegibles.')
            continue
        eligible = [d for d in source_eligible if category_counts[d['category']] < category_cap]
        if not eligible:
            category_cap += 1
            warnings.append(f'Cuota por categoría relajada a {category_cap}: faltan temas distintos elegibles.')
            continue
        unseen_eligible = [d for d in eligible if category_counts[d['category']] == 0]
        if unseen_eligible:
            # Cover available topics before repeats exhaust a source quota.
            eligible = unseen_eligible
        def adjusted(d):
            bonus = (3 if source_counts[d['primary_source']] == 0 else 0) + (3 if category_counts[d['category']] == 0 else 0)
            penalty = 2 * source_counts[d['primary_source']] + 2 * category_counts[d['category']]
            return d['score'] + bonus - penalty
        chosen = sorted(eligible, key=lambda d: (-adjusted(d), d['event_id']))[0]
        chosen['selection_score'] = round(adjusted(chosen), 2)
        chosen['diversity_adjustment'] = round(chosen['selection_score'] - chosen['score'], 2)
        chosen['rank'] = len(selected) + 1
        selected.append(chosen)
        source_counts[chosen['primary_source']] += 1
        category_counts[chosen['category']] += 1
        candidates.remove(chosen)
    if len(selected) < limit:
        warnings.append(f'Solo hay {len(selected)} acontecimientos elegibles; no se completa con noticias antiguas.')
    return {"version": "1.0", "generated_at": now.isoformat(), "window_start": cutoff.isoformat(),
            "requested": limit, "eligible_stories": len(recent), "eligible_events": len(selected) + len(candidates),
            "excluded_stories": len(stories) - len(recent), "selected": selected,
            "distribution": {"primary_sources": dict(source_counts), "categories": dict(category_counts)},
            "quota": {"initial_cap": max(1, math.ceil(limit * 0.4)), "final_source_cap": source_cap, "final_category_cap": category_cap},
            "warnings": warnings,
            "method": "Local keyword heuristics, timestamp window, publisher priors, diversity-aware greedy selection; not fact-checking."}
