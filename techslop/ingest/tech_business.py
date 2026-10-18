"""Public publisher RSS only. Reports live availability without inventing results."""
from __future__ import annotations

import asyncio
from techslop.ingest.international import fetch_feed
from techslop.profiles.tech_business import FEEDS, classify

LAST_FETCH_REPORT: list[dict] = []


async def fetch_tech_business():
    LAST_FETCH_REPORT.clear()
    async def fetch(spec):
        diagnostics = []
        try:
            stories = await asyncio.wait_for(fetch_feed(spec.name, spec.url, language=spec.language, diagnostics=diagnostics), timeout=30)
            selected = []
            for story in stories:
                category = classify(story.title, story.raw_data.get('summary',''), story.raw_data.get('tags',[]), focused=False)
                if spec.default_category == 'tecnologia_ia':
                    category = 'tecnologia_ia'
                if category is None and spec.focused:
                    category = spec.default_category
                if category is None:
                    continue
                story.raw_data['profiles'] = {'tech_business': {'category':category}}
                story.raw_data['original_articles'] = [{
                    'story_id':story.id,'title':story.title,'source':story.source,'url':story.url,
                    'summary':story.raw_data.get('summary',''),'language':story.raw_data.get('language','und'),
                    'published_at':story.published_at.isoformat()}]
                selected.append(story)
            LAST_FETCH_REPORT.append({'source':spec.name,'feed_url':spec.url,'language':spec.language,
                                      'source_type':spec.kind,'received':len(stories),'selected':len(selected),
                                      **(diagnostics[-1] if diagnostics else {'status':'empty_or_failed'})})
            return selected
        except Exception as exc:
            LAST_FETCH_REPORT.append({'source':spec.name,'feed_url':spec.url,'status':'failed','error_type':type(exc).__name__,'selected':0})
            return []
    groups = await asyncio.gather(*(fetch(spec) for spec in FEEDS))
    LAST_FETCH_REPORT.sort(key=lambda r:r['source'])
    return [story for group in groups for story in group]
