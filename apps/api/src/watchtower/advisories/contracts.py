"""Strict request and response contracts for living intelligence advisories."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from watchtower.db.models import AdvisorySectionType, AdvisoryStatus, IntelligenceType

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: AdvisorySectionType
    intelligence_type: IntelligenceType
    content: NonBlank


class RevisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    summary: NonBlank
    created_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    sections: list[SectionInput] = Field(min_length=1)
    evidence_ids: list[UUID] = Field(default_factory=list)
    actor_ids: list[UUID] = Field(default_factory=list)
    campaign_ids: list[UUID] = Field(default_factory=list)
    technique_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_links_and_sections(self) -> RevisionInput:
        if len({item.section_type for item in self.sections}) != len(self.sections):
            raise ValueError("section_type values must be unique")
        for field_name in ("evidence_ids", "actor_ids", "campaign_ids", "technique_ids"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} values must be unique")
        return self


class AdvisoryCreate(RevisionInput):
    slug: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=200,
            pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        ),
    ]


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    published_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]


class AdvisoryUpdateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_at: datetime
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    summary: NonBlank
    intelligence_type: IntelligenceType
    created_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    evidence_ids: list[UUID] = Field(default_factory=list)

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def evidence_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("evidence_ids values must be unique")
        return value


class EvidenceLinkRead(BaseModel):
    id: UUID
    citation: str
    excerpt: str | None
    source_id: UUID


class NamedLinkRead(BaseModel):
    id: UUID
    name: str


class ActorLinkRead(BaseModel):
    id: UUID
    canonical_name: str


class TechniqueLinkRead(NamedLinkRead):
    external_id: str


class SectionRead(BaseModel):
    section_type: AdvisorySectionType
    position: int
    intelligence_type: IntelligenceType
    content: str


class RevisionRead(BaseModel):
    id: UUID
    version: int
    title: str
    summary: str
    created_by: str
    created_at: datetime
    published_at: datetime | None
    published_by: str | None
    sections: list[SectionRead]
    evidence: list[EvidenceLinkRead]
    actors: list[ActorLinkRead]
    campaigns: list[NamedLinkRead]
    techniques: list[TechniqueLinkRead]


class UpdateRead(BaseModel):
    id: UUID
    sequence: int
    revision_version: int
    occurred_at: datetime
    title: str
    summary: str
    intelligence_type: IntelligenceType
    created_by: str
    created_at: datetime
    evidence: list[EvidenceLinkRead]


class AdvisoryRead(BaseModel):
    id: UUID
    slug: str
    status: AdvisoryStatus
    published_revision: int | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    revision: RevisionRead
    updates: list[UpdateRead] = Field(default_factory=list)


class AdvisorySummaryRead(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str
    published_revision: int
    published_at: datetime
    latest_update_at: datetime | None


class AdvisoryResponse(BaseModel):
    data: AdvisoryRead


class AdvisoryCollectionResponse(BaseModel):
    data: list[AdvisorySummaryRead]
    limit: int


class UpdateCollectionResponse(BaseModel):
    data: list[UpdateRead]
    after_sequence: int
    limit: int
