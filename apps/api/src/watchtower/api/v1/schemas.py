"""Pydantic response contracts for actor-centric reads."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from watchtower.db.models import IntelligenceType, Origin


class SourceRead(BaseModel):
    id: UUID
    name: str
    kind: str
    base_url: str | None


class ActorRead(BaseModel):
    id: UUID
    canonical_name: str
    description: str | None


class ActorResponse(BaseModel):
    data: ActorRead


class ActorSearchRead(ActorRead):
    matched_names: list[str] = Field(default_factory=list)


class ActorSearchResponse(BaseModel):
    data: list[ActorSearchRead]
    limit: int


class AliasRead(BaseModel):
    id: UUID
    name: str
    source_native_id: str | None
    confidence: int | None
    source: SourceRead


class AliasCollection(BaseModel):
    items: list[AliasRead]
    truncated: bool


class AliasResponse(BaseModel):
    data: AliasCollection


class BehaviorRead(BaseModel):
    id: UUID
    name: str
    description: str | None


class TechniqueRead(BaseModel):
    id: UUID
    external_id: str
    name: str
    description: str | None
    source: SourceRead


class EvidenceRead(BaseModel):
    id: UUID
    citation: str
    excerpt: str | None
    locator: str | None
    captured_at: datetime | None
    confidence: int | None
    origin: Origin
    raw_evidence_id: UUID | None
    source: SourceRead


class ObservationRead(BaseModel):
    id: UUID
    source_native_id: str | None
    title: str
    summary: str
    observed_at: datetime
    first_seen: datetime | None
    last_seen: datetime | None
    confidence: int | None
    intelligence_type: IntelligenceType
    origin: Origin
    raw_evidence_id: UUID | None
    source: SourceRead
    evidence: list[EvidenceRead]
    behaviors: list[BehaviorRead]
    techniques: list[TechniqueRead]
    evidence_truncated: bool
    behaviors_truncated: bool
    techniques_truncated: bool


class TimelineEvent(ObservationRead):
    event_type: Literal["observation"] = "observation"


class CursorPage(BaseModel):
    limit: int
    next_cursor: str | None


class ObservationPageResponse(BaseModel):
    data: list[ObservationRead]
    page: CursorPage


class TimelinePageResponse(BaseModel):
    data: list[TimelineEvent]
    page: CursorPage


class AssociationCollection(BaseModel):
    behaviors: list[BehaviorRead]
    techniques: list[TechniqueRead]
    behaviors_truncated: bool
    techniques_truncated: bool


class AssociationResponse(BaseModel):
    data: AssociationCollection


class ReferenceCollection(BaseModel):
    sources: list[SourceRead]
    evidence: list[EvidenceRead]
    sources_truncated: bool
    evidence_truncated: bool


class ReferenceResponse(BaseModel):
    data: ReferenceCollection
