"""Contracts for faithful technical artifact ingestion and reads."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from watchtower.db.models import ArtifactType, ArtifactValidationStatus, Origin


class ArtifactSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    raw_evidence_id: UUID | None = None
    artifact_type: ArtifactType
    origin: Origin
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactSourceRead(BaseModel):
    id: UUID
    name: str
    kind: str
    base_url: str | None


class ArtifactRead(BaseModel):
    id: UUID
    artifact_type: ArtifactType
    origin: Origin
    canonical_id: str
    title: str
    version: str | None
    content_sha256: str
    validation_status: ArtifactValidationStatus
    validation_errors: list[str]
    metadata: dict[str, Any]
    raw_evidence_id: UUID | None
    source: ArtifactSourceRead
    created_at: datetime


class ArtifactDetailRead(ArtifactRead):
    original_content: str
    structured_content: dict[str, Any] | list[Any] | None


class ArtifactCollectionResponse(BaseModel):
    data: list[ArtifactRead]
    limit: int


class ArtifactResponse(BaseModel):
    data: ArtifactDetailRead
