"""Public Spanish RSS feeds; agency feeds require an authorized endpoint."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from calendar import timegm
from datetime import datetime, timezone
from urllib.parse import urlsplit

import feedparser
import httpx

from techslop.config import settings
from techslop.models import Story

logger = logging.getLogger(__name__)
PUBLIC_FEEDS = {
    "bbc_mundo": "https://feeds.bbci.co.uk/mundo/rss.xml",
    "dw": "https://rss.dw.com/rdf/rss-sp-all",
    "onu": "https://news.un.org/feed/subscribe/es/news/all/rss.xml",
}
AGENCY_HOSTS = {
    "reuters": {"reuters.com", "reutersconnect.com"},
    "ap": {"ap.org", "apnews.com"},
    "afp": {"afp.com", "afpforum.com"},
}


def configured_feeds() -> dict[str, str]:
    feeds = dict(PUBLIC_FEEDS)
    try:
        agencies = json.loads(settings.authorized_agency_rss)
        if not isinstance(agencies, dict):
            raise ValueError("expected an object")
        for name, url in agencies.items():
            if name not in AGENCY_HOSTS or not isinstance(url, str):
                raise ValueError("unknown agency or invalid URL")
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if (parsed.scheme != "https" or parsed.username or parsed.password
                    or parsed.port not in (None, 443)
                    or not any(host == h or host.endswith('.' + h) for h in AGENCY_HOSTS[name])):
                raise ValueError("agency URL must use an official HTTPS host without credentials")
            feeds[name] = url
    except (ValueError, TypeError):
        # Do not log configured URLs: they may contain subscription identifiers.
        logger.error("Invalid AUTHORIZED_AGENCY_RSS; agency feeds disabled")
        return dict(PUBLIC_FEEDS)
    return feeds


async def fetch_feed(name: str, url: str) -> list[Story]:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "techslop/0.1 RSS reader"})
            response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo and not feed.entries:
            logger.warning("RSS %s: invalid or empty feed", name)
            return []
        stories = []
        for entry in feed.entries[:100]:
            link, title = entry.get("link", ""), entry.get("title", "").strip()
            if not title or urlsplit(link).scheme not in {"https", "http"} or not urlsplit(link).hostname:
                continue
            date = entry.get("published_parsed") or entry.get("updated_parsed")
            try:
                published = datetime.fromtimestamp(timegm(date), timezone.utc) if date else datetime.now(timezone.utc)
            except (ValueError, OverflowError, TypeError):
                published = datetime.now(timezone.utc)
            stories.append(Story(
                id=hashlib.sha256(link.encode()).hexdigest(), title=title,
                url=link, source=name, score=1.0, published_at=published,
                raw_data={"summary": entry.get("summary", ""), "language": "es",
                          "tags": [tag.get("term", "") for tag in entry.get("tags", [])]},
            ))
        return stories
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("RSS %s unavailable (%s)", name, type(exc).__name__)
        return []


async def fetch_international() -> list[Story]:
    results = await asyncio.gather(*(asyncio.wait_for(fetch_feed(name, url), timeout=30) for name, url in configured_feeds().items()), return_exceptions=True)
    stories = []
    for group in results:
        if isinstance(group, BaseException):
            logger.warning("RSS source failed (%s)", type(group).__name__)
        else:
            stories.extend(group)
    return stories
