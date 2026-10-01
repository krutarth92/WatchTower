"""Typed boundaries for provider-neutral embeddings and grounded synthesis."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from watchtower.db.models import IntelligenceType, Origin


class ResearchIntent(StrEnum):
    ACTOR_OVERVIEW = "actor_overview"
    BEHAVIOR_CHANGE = "behavior_change"
    EVIDENCE_SUPPORT = "evidence_support"


class AnswerStatus(StrEnum):
    GROUNDED = "grounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ResearchQuestion(BaseModel):
    actor_id: UUID
    question: str = Field(min_length=2, max_length=1000)
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> ResearchQuestion:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from must be before or equal to date_to")
        return self


class RetrievedEvidence(BaseModel):
    evidence_id: UUID
    source_id: UUID
    observation_id: UUID
    actor_id: UUID
    citation: str
    excerpt: str
    source_name: str
    source_kind: str
    source_metadata: dict[str, Any]
    observed_at: datetime
    intelligence_type: IntelligenceType
    origin: Origin
    distance: float


class GroundingPrompt(BaseModel):
    system_instructions: str
    question: str
    intent: ResearchIntent
    untrusted_context: list[RetrievedEvidence]


class GroundedClaimDraft(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    intelligence_type: IntelligenceType
    evidence_ids: list[UUID] = Field(min_length=1)


class GroundedDraft(BaseModel):
    answer: str = Field(min_length=1, max_length=12000)
    claims: list[GroundedClaimDraft] = Field(min_length=1)


class CitationRead(BaseModel):
    evidence_id: UUID
    source_id: UUID
    observation_id: UUID
    citation: str
    excerpt: str
    source_name: str
    source_kind: str
    source_metadata: dict[str, Any]
    observed_at: datetime
    intelligence_type: IntelligenceType
    origin: Origin


class GroundedClaimRead(GroundedClaimDraft):
    pass


class ResearchAnswer(BaseModel):
    status: AnswerStatus
    intent: ResearchIntent
    question: str
    answer: str | None
    claims: list[GroundedClaimRead] = Field(default_factory=list)
    citations: list[CitationRead] = Field(default_factory=list)
    retrieved_count: int = Field(ge=0)
    context_tokens_used: int = Field(ge=0)
    synthesis_type: str = "model_interpretation"
    reason: str | None = None


class ResearchAnswerResponse(BaseModel):
    data: ResearchAnswer


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class GroundedModel(Protocol):
    def generate(self, prompt: GroundingPrompt) -> GroundedDraft | dict[str, Any]: ...
