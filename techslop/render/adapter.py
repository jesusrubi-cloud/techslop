"""Translate the editorial contract into an audio-driven, renderer-ready timeline."""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from techslop.editorial.script_format import EditorialScript, validate_script

KINDS = {'intro', 'explanation', 'chart', 'closing'}


@dataclass(frozen=True)
class RenderScene:
    id: str
    kind: str
    title: str
    text: str
    start: float
    duration: float
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class RenderPlan:
    scenes: tuple[RenderScene, ...]
    duration: float
    audio_mode: str
    demo: bool
    chart_values: tuple[float, ...]


def adapt(data: dict, dossier: dict, presentation: dict, durations: list[float], audio_mode: str) -> tuple[EditorialScript, RenderPlan]:
    script = validate_script(data, dossier)
    demo = dossier.get('content_type') == 'fictional_demonstration'
    if not demo and (script.editorial_status != 'reviewed' or dossier.get('independent_corroboration', {}).get('status') != 'verified'):
        raise ValueError('Real news requires reviewed script and independent corroboration; use an explicit fictional demonstration otherwise')
    if len(durations) != len(script.scenes) or any(not math.isfinite(d) or d <= 0 for d in durations):
        raise ValueError('One positive measured audio duration is required per scene')
    if audio_mode not in {'edge_es_MX', 'test_tone'}:
        raise ValueError('Unsupported audio mode')
    if set(presentation) != {s.id for s in script.scenes}:
        raise ValueError('Presentation must describe exactly the script scenes')
    scenes = []
    start = 0.0
    for scene, duration in zip(script.scenes, durations, strict=True):
        visual = presentation[scene.id]
        if set(visual) - {'kind', 'title', 'text', 'chart_metric'}:
            raise ValueError('Unsupported visual fields; no arbitrary statistics or assets')
        if visual['kind'] not in KINDS:
            raise ValueError('Unknown scene kind')
        if visual['kind'] == 'chart' and visual.get('chart_metric') != 'measured_audio_seconds':
            raise ValueError('Only locally verified audio-duration charts are implemented')
        if scene.animation.asset_origin != 'original_local' or scene.animation.technique in {'map', 'licensed_image'}:
            raise ValueError('Maps and external images are not implemented; no fabricated assets')
        scenes.append(RenderScene(scene.id, visual['kind'], visual['title'], visual['text'], start, duration, tuple(scene.source_urls)))
        start += duration
    if not 45 <= start <= 75:
        raise ValueError(f'Measured audio totals {start:.2f}s; revise narration to fit 45–75s. Audio is never silently stretched')
    return script, RenderPlan(tuple(scenes), start, audio_mode, demo, tuple(durations))


def word_timestamps(script: EditorialScript, plan: RenderPlan, boundaries: list[list[dict]]) -> tuple[list[dict], str]:
    """Use service word boundaries or visibly documented estimates, scene by scene."""
    result = []
    estimated = False
    if len(boundaries) != len(plan.scenes):
        raise ValueError('Boundary list must match scenes')
    for scene, source, measured in zip(plan.scenes, script.scenes, boundaries, strict=True):
        cue_text = ' '.join(cue.text for cue in source.subtitles)
        matching_text = re.findall(r'\w+', cue_text.casefold()) == re.findall(r'\w+', source.narration_es.casefold())
        if measured and matching_text:
            words = measured
            if any(not (0 <= w['start'] < w['end'] <= scene.duration + 0.05) for w in words):
                raise ValueError('Word boundaries outside measured audio')
        else:
            estimated = True
            words = []
            scale = scene.duration / (source.end_seconds - source.start_seconds)
            for cue in source.subtitles:
                start = (cue.start_seconds - source.start_seconds) * scale
                end = (cue.end_seconds - source.start_seconds) * scale
                split = cue.text.split()
                if not split:
                    continue
                step = (end - start) / len(split)
                words.extend({'word': w, 'start': start + i * step, 'end': start + (i + 1) * step}
                             for i, w in enumerate(split))
        result.extend({'word': w['word'], 'start': scene.start + w['start'], 'end': scene.start + min(w['end'], scene.duration)} for w in words)
    return result, 'scaled_contract_reading_cues' if estimated else 'edge_word_boundaries'
