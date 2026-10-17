"""Validated JSON contract for editorial scripts, with no model calls or rendering."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Subtitle(Contract):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str = Field(min_length=1)


class Animation(Contract):
    technique: Literal['map', 'timeline', 'typography', 'chart', 'licensed_image', 'vector_motion']
    description: str = Field(min_length=1)
    asset_origin: Literal['original_local', 'licensed_pending_review'] = 'original_local'
    factual_claim_ids: list[str] = Field(default_factory=list)


class Scene(Contract):
    id: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    narration_es: str = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)
    subtitles: list[Subtitle] = Field(min_length=1)
    animation: Animation

    @model_validator(mode='after')
    def timings(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError('Scene end must follow start')
        previous = self.start_seconds
        for subtitle in self.subtitles:
            if not (self.start_seconds <= subtitle.start_seconds < subtitle.end_seconds <= self.end_seconds):
                raise ValueError('Subtitle must be contained in scene')
            if subtitle.start_seconds < previous:
                raise ValueError('Subtitles must be ordered and non-overlapping')
            previous = subtitle.end_seconds
        return self


class EditorialScript(Contract):
    schema_version: Literal['1.0'] = '1.0'
    event_id: str = Field(min_length=1)
    language: Literal['es'] = 'es'
    duration_seconds: float = Field(ge=45, le=75)
    editorial_status: Literal['draft', 'reviewed'] = 'draft'
    publication_approved: Literal[False] = False
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode='after')
    def timeline(self):
        previous = 0.0
        scene_ids = set()
        for scene in self.scenes:
            if scene.id in scene_ids or abs(scene.start_seconds - previous) > 0.001:
                raise ValueError('Scene IDs must be unique and scenes contiguous from zero')
            previous = scene.end_seconds
            scene_ids.add(scene.id)
        if abs(previous - self.duration_seconds) > 0.001:
            raise ValueError('Final scene must end at duration_seconds')
        return self


def validate_script(data: dict, dossier: dict) -> EditorialScript:
    """Validate timing and traceability; human review still verifies Spanish and facts."""
    script = EditorialScript.model_validate(data)
    if script.event_id != dossier['event_id']:
        raise ValueError('Script event does not match dossier')
    claims = {c['id']: c for c in dossier['pending_claims']}
    urls = {s['url'] for s in dossier['sources']}
    for scene in script.scenes:
        if not set(scene.source_urls) <= urls:
            raise ValueError('Scene has URLs absent from dossier')
        if not set(scene.claim_ids) <= claims.keys():
            raise ValueError('Scene references unknown claims')
        if not set(scene.animation.factual_claim_ids) <= set(scene.claim_ids):
            raise ValueError('Animation must reference claims attached to its scene')
        for claim_id in scene.claim_ids:
            if not set(claims[claim_id]['source_urls']) & set(scene.source_urls):
                raise ValueError('Scene claim lacks its original source URL')
    return script
