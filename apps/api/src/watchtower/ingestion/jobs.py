"""Durable ingestion-job state machine."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from watchtower.db.models import (
    IngestionJob,
    IngestionJobKind,
    IngestionJobState,
    Source,
)

CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class IngestionJobError(RuntimeError):
    """Base error for controlled job-state failures."""


class IngestionJobNotFoundError(IngestionJobError):
    """A requested job does not exist."""


class IngestionJobTransitionError(IngestionJobError):
    """A requested state transition is not valid."""


class IngestionBackpressureError(IngestionJobError):
    """The durable active-job limit has been reached."""


class FailureDisposition(StrEnum):
    RETRY = "retry"
    FAILED = "failed"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    job: IngestionJob
    duplicate: bool


@dataclass(frozen=True, slots=True)
class JobClaim:
    job_id: UUID
    job_kind: IngestionJobKind
    source_id: UUID
    correlation_id: str
    attempt: int
    max_attempts: int
    lease_token: UUID


@dataclass(frozen=True, slots=True)
class FailureResult:
    disposition: FailureDisposition
    delay_ms: int | None = None


@dataclass(frozen=True, slots=True)
class QueueMetrics:
    queued: int
    due: int
    processing: int
    capacity: int
    oldest_queued_at: datetime | None

    @property
    def active(self) -> int:
        return self.queued + self.processing

    @property
    def available(self) -> int:
        return max(0, self.capacity - self.active)


class IngestionJobService:
    def __init__(
        self,
        *,
        lease_seconds: int,
        retry_base_seconds: int,
        max_active_jobs: int = 1000,
        recovery_batch_size: int = 100,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._lease_seconds = lease_seconds
        self._retry_base_seconds = retry_base_seconds
        self._max_active_jobs = max_active_jobs
        self._recovery_batch_size = recovery_batch_size
        self._clock = clock or (lambda: datetime.now(UTC))

    def submit(
        self,
        session: Session,
        *,
        job_kind: IngestionJobKind,
        source: Source,
        correlation_id: str,
        idempotency_key: str,
        max_attempts: int,
    ) -> SubmissionResult:
        clean_correlation = self._clean_required(correlation_id, 128, "correlation ID")
        clean_key = self._clean_required(idempotency_key, 255, "idempotency key")
        session.scalar(select(func.pg_advisory_xact_lock(1465140040)))
        existing = session.scalar(
            select(IngestionJob).where(
                IngestionJob.job_kind == job_kind,
                IngestionJob.idempotency_key == clean_key,
            )
        )
        if existing is not None:
            return SubmissionResult(existing, True)
        metrics = self.queue_metrics(session)
        if metrics.active >= metrics.capacity:
            raise IngestionBackpressureError(
                f"The ingestion backlog reached its {metrics.capacity}-job capacity."
            )
        job = IngestionJob(
            job_kind=job_kind,
            source_id=source.id,
            state=IngestionJobState.QUEUED,
            correlation_id=clean_correlation,
            idempotency_key=clean_key,
            attempts=0,
            max_attempts=max_attempts,
            next_attempt_at=self._now(),
        )
        try:
            with session.begin_nested():
                session.add(job)
                session.flush()
        except IntegrityError:
            existing = session.scalar(
                select(IngestionJob).where(
                    IngestionJob.job_kind == job_kind,
                    IngestionJob.idempotency_key == clean_key,
                )
            )
            if existing is None:
                raise
            return SubmissionResult(existing, True)
        return SubmissionResult(job, False)

    def get(self, session: Session, job_id: UUID) -> IngestionJob:
        job = session.get(IngestionJob, job_id)
        if job is None:
            raise IngestionJobNotFoundError("Ingestion job was not found")
        return job

    def claim(self, session: Session, job_id: UUID) -> JobClaim | None:
        job = self._locked_job(session, job_id)
        now = self._now()
        if job.state is not IngestionJobState.QUEUED:
            return None
        if job.next_attempt_at is not None and job.next_attempt_at > now:
            return None
        if job.attempts >= job.max_attempts:
            job.state = IngestionJobState.FAILED
            job.failure_reason = "Retry attempts were exhausted before the job could be claimed."
            job.next_attempt_at = None
            job.finished_at = now
            session.flush()
            return None
        lease_token = uuid4()
        job.state = IngestionJobState.PROCESSING
        job.attempts += 1
        job.started_at = now
        job.next_attempt_at = None
        job.lease_expires_at = now + timedelta(seconds=self._lease_seconds)
        job.lease_token = lease_token
        session.flush()
        return JobClaim(
            job_id=job.id,
            job_kind=job.job_kind,
            source_id=job.source_id,
            correlation_id=job.correlation_id,
            attempt=job.attempts,
            max_attempts=job.max_attempts,
            lease_token=lease_token,
        )

    def mark_succeeded(
        self,
        session: Session,
        claim: JobClaim,
        raw_evidence_id: UUID | None,
    ) -> bool:
        job = self._locked_job(session, claim.job_id)
        if not self._owns_lease(job, claim):
            return False
        job.state = IngestionJobState.SUCCEEDED
        job.raw_evidence_id = raw_evidence_id
        job.failure_reason = None
        job.next_attempt_at = None
        job.lease_expires_at = None
        job.lease_token = None
        job.finished_at = self._now()
        session.flush()
        return True

    def record_failure(
        self,
        session: Session,
        claim: JobClaim,
        *,
        reason: str,
        retryable: bool,
    ) -> FailureResult:
        job = self._locked_job(session, claim.job_id)
        if not self._owns_lease(job, claim):
            return FailureResult(FailureDisposition.STALE)
        job.failure_reason = self._bounded_reason(reason)
        job.lease_expires_at = None
        job.lease_token = None
        if retryable and job.attempts < job.max_attempts:
            delay_seconds = min(
                self._retry_base_seconds * (2 ** max(0, job.attempts - 1)),
                3600,
            )
            job.state = IngestionJobState.QUEUED
            job.next_attempt_at = self._now() + timedelta(seconds=delay_seconds)
            job.finished_at = None
            session.flush()
            return FailureResult(FailureDisposition.RETRY, delay_seconds * 1000)
        job.state = IngestionJobState.FAILED
        job.next_attempt_at = None
        job.finished_at = self._now()
        session.flush()
        return FailureResult(FailureDisposition.FAILED)

    def queue_metrics(self, session: Session) -> QueueMetrics:
        now = self._now()
        row = session.execute(
            select(
                func.count(IngestionJob.id)
                .filter(IngestionJob.state == IngestionJobState.QUEUED)
                .label("queued"),
                func.count(IngestionJob.id)
                .filter(
                    IngestionJob.state == IngestionJobState.QUEUED,
                    IngestionJob.next_attempt_at <= now,
                )
                .label("due"),
                func.count(IngestionJob.id)
                .filter(IngestionJob.state == IngestionJobState.PROCESSING)
                .label("processing"),
                func.min(IngestionJob.created_at)
                .filter(IngestionJob.state == IngestionJobState.QUEUED)
                .label("oldest_queued_at"),
            )
        ).one()
        return QueueMetrics(
            queued=int(row.queued),
            due=int(row.due),
            processing=int(row.processing),
            capacity=self._max_active_jobs,
            oldest_queued_at=row.oldest_queued_at,
        )

    def recover_expired(self, session: Session, *, limit: int | None = None) -> list[UUID]:
        now = self._now()
        batch_size = limit if limit is not None else self._recovery_batch_size
        jobs = session.scalars(
            select(IngestionJob)
            .where(
                IngestionJob.state == IngestionJobState.PROCESSING,
                IngestionJob.lease_expires_at <= now,
            )
            .order_by(IngestionJob.lease_expires_at, IngestionJob.id)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        ).all()
        recovered: list[UUID] = []
        for job in jobs:
            job.state = IngestionJobState.QUEUED
            job.failure_reason = "Worker lease expired; job queued for replay."
            job.next_attempt_at = now
            job.lease_expires_at = None
            job.lease_token = None
            job.finished_at = None
            recovered.append(job.id)
        session.flush()
        return recovered

    def due_job_ids(self, session: Session, *, limit: int | None = None) -> list[UUID]:
        batch_size = limit if limit is not None else self._recovery_batch_size
        return list(
            session.scalars(
                select(IngestionJob.id)
                .where(
                    IngestionJob.state == IngestionJobState.QUEUED,
                    IngestionJob.next_attempt_at <= self._now(),
                )
                .order_by(IngestionJob.next_attempt_at, IngestionJob.id)
                .limit(batch_size)
            ).all()
        )

    def _locked_job(self, session: Session, job_id: UUID) -> IngestionJob:
        job = session.scalar(
            select(IngestionJob).where(IngestionJob.id == job_id).with_for_update()
        )
        if job is None:
            raise IngestionJobNotFoundError("Ingestion job was not found")
        return job

    @staticmethod
    def _owns_lease(job: IngestionJob, claim: JobClaim) -> bool:
        return (
            job.state is IngestionJobState.PROCESSING
            and job.lease_token == claim.lease_token
            and job.attempts == claim.attempt
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise IngestionJobError("Job clock must return a timezone-aware datetime")
        return value.astimezone(UTC)

    @staticmethod
    def _clean_required(value: str, maximum: int, label: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > maximum or CONTROL_CHARACTER.search(cleaned):
            raise IngestionJobError(f"Invalid {label}")
        return cleaned

    @staticmethod
    def _bounded_reason(reason: str) -> str:
        cleaned = " ".join(reason.split())
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            return "Ingestion job failed."
        return cleaned[:2000]
