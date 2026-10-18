"""Score, rank, and deduplicate ingested stories."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from techslop.ingest.categories import classify, normalize
from datetime import datetime, timezone

from techslop.models import Story

logger = logging.getLogger(__name__)

# Per-source quality weights.
SOURCE_WEIGHTS: dict[str, float] = {
    "bbc_mundo": 1.0, "dw": 1.0, "onu": 1.0,
    "reuters": 1.0, "ap": 1.0, "afp": 1.0,
    "hackernews": 1.0,
    "techcrunch": 0.9,
    "x": 0.85,
    "reddit": 0.8,
    "4chan": 0.7,
}

# Stories published less than this many hours ago get a recency boost.
RECENCY_HOURS = 6
RECENCY_BOOST = 0.15


def _normalize_scores(stories: list[Story]) -> None:
    """Normalize raw scores to [0, 1] within each source, in place."""
    sources: dict[str, list[Story]] = {}
    for story in stories:
        sources.setdefault(story.source, []).append(story)

    for source, group in sources.items():
        scores = [s.score for s in group]
        min_score = min(scores)
        max_score = max(scores)
        span = max_score - min_score

        if span == 0:
            # All scores identical -- assign 1.0 to every story.
            for s in group:
                s.score = 1.0
        else:
            for s in group:
                s.score = (s.score - min_score) / span


def _apply_source_weights(stories: list[Story]) -> None:
    """Multiply each story's normalized score by its source weight."""
    for story in stories:
        weight = SOURCE_WEIGHTS.get(story.source, 0.5)
        story.score *= weight


def _apply_recency_boost(stories: list[Story]) -> None:
    """Give a boost to stories published within RECENCY_HOURS."""
    now = datetime.now(timezone.utc)
    for story in stories:
        age_hours = (now - story.published_at).total_seconds() / 3600
        if age_hours < RECENCY_HOURS:
            story.score += RECENCY_BOOST


def canonical_url(url: str) -> str:
    """Remove fragments and known tracking keys, preserving meaningful query params."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/",
                       urlencode(sorted(query)), ""))


def references(story: Story) -> list[dict]:
    refs = list(story.raw_data.get("sources", []))
    ref = {"source": story.source, "url": story.url}
    if ref not in refs:
        refs.append(ref)
    return refs


def merge_references(target: Story, other: Story) -> None:
    refs = references(target)
    for ref in references(other):
        if ref not in refs:
            refs.append(ref)
    target.raw_data["sources"] = refs
    profiles = {**other.raw_data.get('profiles', {}), **target.raw_data.get('profiles', {})}
    if profiles:
        target.raw_data['profiles'] = profiles
    if 'tech_business' in profiles:
        originals = {}
        for item in [other, target]:
            records = item.raw_data.get('original_articles') or [{
                'story_id':item.id,'title':item.title,'source':item.source,'url':item.url,
                'summary':item.raw_data.get('summary',''),'language':item.raw_data.get('language','und'),
                'published_at':item.published_at.isoformat()}]
            for record in records:
                originals[(record['source'],record['url'])] = record
        target.raw_data['original_articles'] = list(originals.values())


def same_story(first: Story, second: Story) -> bool:
    title = re.sub(r"[^\w]+", " ", normalize(first.title)).strip()
    urls = {canonical_url(ref["url"]) for ref in references(first)}
    return (first.id == second.id
            or any(canonical_url(ref["url"]) in urls for ref in references(second))
            or (len(title) >= 30
                and re.sub(r"[^\w]+", " ", normalize(second.title)).strip() == title
                and abs((first.published_at - second.published_at).total_seconds()) <= 86400))


def deduplicate(stories: list[Story]) -> list[Story]:
    """Merge IDs, canonical URLs or exact normalized headlines within 24 hours.

    Conservative headline matching avoids combining distinct developments.
    Preserve every original source URL in raw_data.sources.
    """
    unique: list[Story] = []
    for story in sorted(stories, key=lambda s: s.score, reverse=True):
        existing = next((other for other in unique if same_story(other, story)), None)
        if existing is not None:
            merge_references(existing, story)
        else:
            story.raw_data["sources"] = references(story)
            unique.append(story)
    return unique


def score_and_rank(stories: list[Story]) -> list[Story]:
    """Full scoring pipeline: normalize, weight, boost, dedup, sort.

    Returns a new list sorted by final score descending.
    """
    if not stories:
        return []

    for story in stories:
        story.raw_data.setdefault("category", classify(story.title, story.raw_data.get("tags", [])))
    _normalize_scores(stories)
    _apply_source_weights(stories)
    _apply_recency_boost(stories)

    unique = deduplicate(stories)
    unique.sort(key=lambda s: s.score, reverse=True)

    logger.info(
        "Scored and ranked %d stories (top score: %.3f)",
        len(unique),
        unique[0].score if unique else 0,
    )
    return unique
