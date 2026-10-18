"""Public publisher RSS only. Reports live availability without inventing results."""
from __future__ import annotations

import asyncio
from techslop.ingest.international import fetch_feed
from techslop.profiles.tech_business import FEEDS, classify
from techslop.profiles.business_quality import assess

LAST_FETCH_REPORT: list[dict] = []


async def fetch_tech_business():
    LAST_FETCH_REPORT.clear()
    async def fetch(spec):
        diagnostics = []
        try:
            stories = await asyncio.wait_for(fetch_feed(spec.name, spec.url, language=spec.language, diagnostics=diagnostics), timeout=30)
            selected, assessments = [], []
            for story in stories:
                quality = assess(story)
                assessments.append({'story_id': story.id, 'title': story.title,
                                    'published_at': story.published_at.isoformat(), **quality})
                category = classify(story.title, story.raw_data.get('summary',''), story.raw_data.get('tags',[]), focused=False)
                if spec.default_category == 'tecnologia_ia':
                    category = 'tecnologia_ia'
                if category is None and quality['eligible']:
                    category = ('economia_mercados' if quality['evidence_terms']['economy'] else
                                'empresas_negocios' if quality['evidence_terms']['business_action'] or quality['evidence_terms']['consumer'] else
                                'tecnologia_ia')
                if category is None:
                    continue
                if not quality['eligible']:
                    continue
                story.raw_data['business_quality'] = quality
                story.raw_data['profiles'] = {'tech_business': {'category':category}}
                story.raw_data['original_articles'] = [{
                    'story_id':story.id,'title':story.title,'source':story.source,'url':story.url,
                    'summary':story.raw_data.get('summary',''),'language':story.raw_data.get('language','und'),
                    'published_at':story.published_at.isoformat()}]
                selected.append(story)
            LAST_FETCH_REPORT.append({'source':spec.name,'feed_url':spec.url,'language':spec.language,
                                      'source_type':spec.kind,'received':len(stories),'selected':len(selected),'assessments':assessments,
                                      **(diagnostics[-1] if diagnostics else {'status':'empty_or_failed'})})
            return selected
        except Exception as exc:
            LAST_FETCH_REPORT.append({'source':spec.name,'feed_url':spec.url,'status':'failed','error_type':type(exc).__name__,'selected':0})
            return []
    groups = await asyncio.gather(*(fetch(spec) for spec in FEEDS))
    LAST_FETCH_REPORT.sort(key=lambda r:r['source'])
    return [story for group in groups for story in group]
