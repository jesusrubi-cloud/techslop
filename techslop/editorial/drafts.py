"""Offline, evidence-linked assembly; never supplies missing facts or translations."""
from __future__ import annotations
from techslop.editorial.script_format import validate_script


def prepare_draft(dossier: dict, copy: list[dict], format: str) -> dict:
    if format not in {'quick', 'explained'}:
        raise ValueError('Choose quick or explained')
    sections = ['event', 'context', 'consequences', 'closing']
    if [item.get('section') for item in copy] != sections:
        raise ValueError('Provide event, context, consequences and closing, in order')
    # Copy is editorial input, never generated from an unverified headline.
    # Explicit conditional analysis prevents silently representing an outlook as evidence.
    if not copy[-1].get('conditional_outlook_es', '').startswith('Si '):
        raise ValueError('Closing needs conditional_outlook_es starting with Si (scenario, not certainty)')
    duration = 40 if format == 'quick' else 68
    scenes = []
    for index, item in enumerate(copy):
        text = item['narration_es'].strip()
        if item['section'] == 'closing':
            text += ' ' + item['conditional_outlook_es'].strip()
        start, end = index * duration / 4, (index + 1) * duration / 4
        scenes.append({'id': item['section'], 'section': item['section'],
                       'start_seconds': start, 'end_seconds': end, 'narration_es': text,
                       'claim_ids': item['claim_ids'], 'source_urls': item['source_urls'],
                       'subtitles': [{'start_seconds': start, 'end_seconds': end, 'text': text}],
                       'animation': {'technique': 'typography', 'description': 'Texto original con movimiento suave; sin cifras ni imágenes añadidas.'}})
    data = {'event_id': dossier['event_id'], 'format': format, 'duration_seconds': duration,
            'editorial_status': 'draft', 'publication_approved': False, 'scenes': scenes}
    return validate_script(data, dossier).model_dump()
