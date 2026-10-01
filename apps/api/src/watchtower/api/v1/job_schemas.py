"""Pydantic contracts for operator ingestion jobs."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from watchtower.db.models import IngestionJob, IngestionJobKind, IngestionJobState

CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class IngestionJobSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_kind: IngestionJobKind
    idempotency_key: str = Field(min_length=1, max_length=255)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Idempotency key must contain safe visible text")
        return cleaned


class IngestionJobRead(BaseModel):
    id: UUID
    job_kind: IngestionJobKind
    source_id: UUID
    raw_evidence_id: UUID | None
    state: IngestionJobState
    correlation_id: str
    idempotency_key: str
    attempts: int
    max_attempts: int
    failure_reason: str | None
    next_attempt_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionJobSubmissionData(BaseModel):
    job: IngestionJobRead
    duplicate: bool


class IngestionJobSubmissionResponse(BaseModel):
    data: IngestionJobSubmissionData


class IngestionJobStatusResponse(BaseModel):
    data: IngestionJobRead


class IngestionQueueMetricsRead(BaseModel):
    queued: int = Field(ge=0)
    due: int = Field(ge=0)
    processing: int = Field(ge=0)
    active: int = Field(ge=0)
    capacity: int = Field(gt=0)
    available: int = Field(ge=0)
    oldest_queued_at: datetime | None


class IngestionQueueMetricsResponse(BaseModel):
    data: IngestionQueueMetricsRead


def ingestion_job_read(job: IngestionJob) -> IngestionJobRead:
    return IngestionJobRead(
        id=job.id,
        job_kind=job.job_kind,
        source_id=job.source_id,
        raw_evidence_id=job.raw_evidence_id,
        state=job.state,
        correlation_id=job.correlation_id,
        idempotency_key=job.idempotency_key,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        failure_reason=job.failure_reason,
        next_attempt_at=job.next_attempt_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
