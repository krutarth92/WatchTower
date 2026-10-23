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
    INDICATOR = "indicator"
    VULNERABILITY = "vulnerability"


class SearchMatchKind(StrEnum):
    EXACT = "exact"
    FULL_TEXT = "full_text"


class RelatedActorRead(BaseModel):
    id: UUID
    canonical_name: str
    description: str | None = None
    latest_observed_at: datetime | None = None


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
    indicator_type: str | None = None
    indicator_value: str | None = None
    severity: str | None = None
    cvss_score: float | None = None
    related_actors: list[RelatedActorRead] = Field(default_factory=list)
    related_actors_truncated: bool = False
    match_kind: SearchMatchKind
    score: float = Field(ge=0)


class SearchResponse(BaseModel):
    query: str
    data: list[SearchResultRead]
    limit: int
    next_cursor: str | None


class ActorDiscoveryRead(BaseModel):
    id: UUID
    canonical_name: str
    description: str | None
    latest_observed_at: datetime | None
    published_observation_count: int = Field(ge=0)
    published_alias_count: int = Field(ge=0)
    popularity_score: int = Field(ge=0)


class ActorDiscoveryResponse(BaseModel):
    recent: list[ActorDiscoveryRead]
    popular: list[ActorDiscoveryRead]
    limit: int
