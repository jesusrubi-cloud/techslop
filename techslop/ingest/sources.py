"""Source registry -- run all ingestion sources and return scored results."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from techslop.models import Story
from techslop.config import settings
from techslop.ingest.international import fetch_international
from techslop.ingest.fourchan import fetch_fourchan
from techslop.ingest.hackernews import fetch_hackernews
from techslop.ingest.reddit import fetch_reddit
from techslop.ingest.techcrunch import fetch_techcrunch
from techslop.ingest.xtwitter import fetch_x
from techslop.ingest.scorer import score_and_rank

logger = logging.getLogger(__name__)

# Each source is an async callable returning a list of stories.
SourceFetcher = Callable[[], Awaitable[list[Story]]]

SOURCES: list[tuple[str, SourceFetcher]] = [
    ("hackernews", fetch_hackernews),
    ("reddit", fetch_reddit),
    ("techcrunch", fetch_techcrunch),
    ("4chan", fetch_fourchan),
    ("x", fetch_x),
]


async def _run_source(name: str, fetcher: SourceFetcher) -> list[Story]:
    """Run a single source fetcher, catching and logging any errors."""
    try:
        stories = await fetcher()
        logger.info("Source '%s' returned %d stories", name, len(stories))
        return stories
    except Exception as exc:
        logger.error("Source '%s' failed: %s", name, exc)
        return []


async def ingest_all(profile: str | None = None) -> list[Story]:
    """Run every registered source, collect stories, score, dedup, and sort.

    Sources are executed concurrently.  If any individual source fails the
    remaining sources still contribute their stories.

    Returns a deduplicated list of Story objects sorted by final score
    descending.
    """
    profile = profile or settings.news_profile
    if profile not in {"international", "tech"}:
        raise ValueError("NEWS_PROFILE must be international or tech")
    sources = [("international", fetch_international)] if profile == "international" else SOURCES
    tasks = [asyncio.wait_for(_run_source(name, fetcher), timeout=90) for name, fetcher in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_stories: list[Story] = []
    for stories in results:
        if isinstance(stories, BaseException):
            logger.warning("Source exceeded its deadline or failed (%s)", type(stories).__name__)
            continue
        all_stories.extend(stories)

    logger.info("Collected %d raw stories from %d sources", len(all_stories), len(sources))

    ranked = score_and_rank(all_stories)
    logger.info("Final pipeline produced %d scored stories", len(ranked))
    return ranked
