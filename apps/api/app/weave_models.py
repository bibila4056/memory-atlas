"""Typed Weaving contracts: Memory Atoms → Moments → Story Bundle (BundleWeaver-lite).

Model-produced objects may only reference IDs that application code supplied;
`weaver.validate_*` enforces that before anything is persisted.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from .models import ContractModel

ProviderMode = Literal['live', 'fixture', 'heuristic']


class ProviderInfo(ContractModel):
    reasoning: ProviderMode
    reasoning_model: str | None = None
    embeddings: Literal['siglip2', 'fallback']
    embedding_model: str | None = None
    cross_modal: bool = Field(description='True when text queries and images share one embedding space (SigLIP 2).')


class Detail(ContractModel):
    label: str = Field(min_length=1, max_length=40, description='What is visibly there, in plain words (e.g. "churros", "person").')
    box: tuple[float, float, float, float] = Field(description='Normalized [x0, y0, x1, y1] within the photo.')


class MemoryAtom(ContractModel):
    id: str
    source_ids: list[UUID] = Field(min_length=1)
    event: str = Field(min_length=1, max_length=120)
    people: list[str] = []
    place: str | None = None
    objects: list[str] = []
    moods: list[str] = []
    themes: list[str] = []
    captured_at: datetime | None = None
    salience: float = Field(ge=0, le=1)
    verbatim_text: str | None = None
    must_preserve: bool = True
    subject_kind: Literal['object', 'scene'] | None = None
    details: list[Detail] = []


class DuplicateGroup(ContractModel):
    id: str
    source_ids: list[UUID] = Field(min_length=2)
    kept_source_id: UUID
    reason: Literal['exact', 'perceptual', 'embedding']


class Moment(ContractModel):
    id: str
    title: str
    atom_ids: list[str] = Field(min_length=1)
    source_ids: list[UUID] = Field(min_length=1)
    image_source_ids: list[UUID] = []
    summary: str
    people: list[str] = []
    place: str | None = None
    moods: list[str] = []
    salience: float = Field(ge=0, le=1)
    time_range: tuple[datetime, datetime] | None = None


# ── structured-model outputs (validated against supplied IDs) ─────────────
class AtomDraft(ContractModel):
    source_ids: list[str] = Field(min_length=1)
    event: str
    people: list[str] = []
    place: str | None = None
    objects: list[str] = []
    moods: list[str] = []
    themes: list[str] = []
    salience: float = Field(ge=0, le=1)
    subject_kind: Literal['object', 'scene'] | None = Field(default=None, description='object: one clear subject distinct from its background; scene: blended scenery.')
    details: list[Detail] = Field(default=[], max_length=4, description='Up to 4 visible things worth pointing at, with boxes.')


class AtomizerOutput(ContractModel):
    atoms: list[AtomDraft]


class RoleIntent(ContractModel):
    role: str = Field(min_length=1, max_length=40)
    intent: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=120, description='Short visual description used for embedding retrieval.')


class StoryIntent(ContractModel):
    intent: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=80)
    keywords: list[str] = Field(default=[], max_length=8)
    roles: list[RoleIntent] = Field(min_length=2, max_length=5, description='First role is always the Anchor.')


class VerifierReport(ContractModel):
    coverage: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    complementarity: int = Field(ge=1, le=5)
    groundedness: int = Field(ge=1, le=5)
    visual_diversity: int = Field(ge=1, le=5)
    weakest_moment_id: str | None = None
    replacement_moment_id: str | None = None
    rationale: str = Field(max_length=400)


# ── weaving result ────────────────────────────────────────────────────────
class RoleCandidates(ContractModel):
    role: str
    intent: str
    query: str
    candidate_moment_ids: list[str] = Field(max_length=3)
    scores: list[float]


class BundleScore(ContractModel):
    total: float
    role_coverage: float
    salience: float
    visual_diversity: float
    emotional_coverage: float
    temporal_coverage: float
    grounding: float
    redundancy_penalty: float


class ScoredBundle(ContractModel):
    seed: Literal['anchor', 'alternative', 'baseline']
    moment_ids: list[str]
    roles: dict[str, str] = Field(description='moment_id → narrative role')
    score: BundleScore
    expansion_log: list[str] = []


class StageTiming(ContractModel):
    stage: str
    ms: int


class WeaveResult(ContractModel):
    schema_version: Literal['0.1.0'] = '0.1.0'
    session_id: UUID
    created_at: datetime
    providers: ProviderInfo
    atoms: list[MemoryAtom]
    duplicate_groups: list[DuplicateGroup]
    moments: list[Moment]
    story: StoryIntent
    role_candidates: list[RoleCandidates]
    seeds: list[ScoredBundle] = Field(min_length=1, max_length=2)
    selected: ScoredBundle
    verifier: VerifierReport
    verifier_mode: ProviderMode
    replacement: str | None = Field(default=None, description='"old → new" when the one allowed replacement was applied.')
    baseline: ScoredBundle
    palette: list[str] = Field(min_length=3, max_length=6)
    uses_timeline: bool
    art: 'ArtDirectionOut | None' = None
    stickers: list['StickerPickOut'] = []
    day: date | None = Field(default=None, description='The day most photos were taken on; the memory is filed under it.')
    timings: list[StageTiming]


class WeaveRequest(ContractModel):
    session_id: UUID


class ArtRequestOut(ContractModel):
    source_id: str
    moment_id: str
    tool: Literal['tape_collage', 'doodle', 'scene_extension']
    treatment: Literal['DISTILL', 'EXTEND']
    reason: str
    placement: Literal['beside_original', 'replaces_print_zone']


class AnnotationOut(ContractModel):
    text: str
    source_ids: list[str]
    target_source_id: str
    box: tuple[float, float, float, float]


class ArtDirectionOut(ContractModel):
    requests: list[ArtRequestOut]
    annotations: list[AnnotationOut]


class ClarifyQuestion(ContractModel):
    id: str
    source_id: str
    text: str
    suggestions: list[str] = []


class PhotoSeen(ContractModel):
    source_id: str
    captured_at: datetime | None = None
    subject_kind: Literal['object', 'scene'] | None = None
    labels: list[str] = []
    people: list[str] = []


class VoiceHeard(ContractModel):
    source_id: str
    shown_as_text: bool = Field(description='True for "Turn into words"; False = understood quietly, stays as your voice on the page.')
    status: Literal['transcribed', 'unavailable', 'failed']
    text: str | None = None
    detail: str | None = None


class ClarifyResult(ContractModel):
    """The 'understand' step: what each photo shows, what each voice note says, and ≤N questions for what can't be seen."""
    questions: list[ClarifyQuestion] = Field(max_length=3)
    photos: list[PhotoSeen] = []
    voices: list[VoiceHeard] = []


class StickerPickOut(ContractModel):
    id: str
    label: str
    src: str
    kind: str
    chosen: bool
    score: float
    matched: list[str]
    color_fit: float
    reason: str


WeaveResult.model_rebuild()
