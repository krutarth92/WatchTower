"""Public contracts for deterministic cross-entity search."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from watchtower.db.models import IntelligenceType, Origin


class SearchEntityType(StrEnum):
    ACTOR = "actor"
    ALIAS = "alias"
    CAMPAIGN = "campaign"
    BEHAVIOR = "behavior"
    TECHNIQUE = "technique"
    OBSERVATION = "observation"
    SOURCE = "source"


class SearchMatchKind(StrEnum):
    EXACT = "exact"
    FULL_TEXT = "full_text"


class SearchResultRead(BaseModel):
    entity_type: SearchEntityType
    id: UUID
    title: str
    summary: str | None
    source_id: UUID | None
    actor_id: UUID | None
    external_id: str | None
    observed_at: datetime | None
    intelligence_type: IntelligenceType | None
    origin: Origin | None
    match_kind: SearchMatchKind
    score: float = Field(ge=0)


class SearchResponse(BaseModel):
    query: str
    data: list[SearchResultRead]
    limit: int
