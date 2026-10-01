"""Transactional ingestion-job execution with bounded retry scheduling."""

import logging
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from watchtower.ingestion.jobs import (
    FailureDisposition,
    IngestionJobService,
    JobClaim,
)

logger = logging.getLogger("watchtower.ingestion.jobs")


class RetryableIngestionError(RuntimeError):
    """The job may succeed if attempted again."""


class PermanentIngestionError(RuntimeError):
    """The job input or deterministic processing cannot succeed on retry."""


class StaleIngestionLeaseError(RuntimeError):
    """The worker lost its durable lease before it could commit results."""


class JobQueue(Protocol):
    def enqueue(self, job_id: UUID, *, delay_ms: int = 0) -> None: ...


class JobProcessor(Protocol):
    def process(self, session: Session, claim: JobClaim) -> UUID | None: ...


class RunDisposition(StrEnum):
    SUCCEEDED = "succeeded"
    RETRY_QUEUED = "retry_queued"
    FAILED = "failed"
    SKIPPED = "skipped"
    STALE = "stale"


class IngestionJobRunner:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        service: IngestionJobService,
        processor: JobProcessor,
        queue: JobQueue,
    ) -> None:
        self._session_factory = session_factory
        self._service = service
        self._processor = processor
        self._queue = queue

    def run(self, job_id: UUID) -> RunDisposition:
        with self._session_factory.begin() as session:
            claim = self._service.claim(session, job_id)
        if claim is None:
            return RunDisposition.SKIPPED
        self._log("ingestion_job_processing", claim, state="processing")
        try:
            with self._session_factory.begin() as session:
                raw_evidence_id = self._processor.process(session, claim)
                owns_lease = self._service.mark_succeeded(session, claim, raw_evidence_id)
                if not owns_lease:
                    raise StaleIngestionLeaseError
        except StaleIngestionLeaseError:
            self._log("ingestion_job_stale_completion", claim, state="processing")
            return RunDisposition.STALE
        except Exception as error:
            retryable = not isinstance(error, PermanentIngestionError)
            reason = self._failure_reason(error)
            with self._session_factory.begin() as session:
                failure = self._service.record_failure(
                    session,
                    claim,
                    reason=reason,
                    retryable=retryable,
                )
            if failure.disposition is FailureDisposition.STALE:
                self._log("ingestion_job_stale_failure", claim, state="processing")
                return RunDisposition.STALE
            if failure.disposition is FailureDisposition.RETRY:
                assert failure.delay_ms is not None
                try:
                    self._queue.enqueue(claim.job_id, delay_ms=failure.delay_ms)
                except Exception as enqueue_error:
                    logger.warning(
                        "ingestion_job_retry_enqueue_failed",
                        extra={
                            "fields": {
                                **self._fields(claim, "queued"),
                                "error_type": type(enqueue_error).__name__,
                            }
                        },
                    )
                self._log("ingestion_job_retry_queued", claim, state="queued")
                return RunDisposition.RETRY_QUEUED
            self._log("ingestion_job_failed", claim, state="failed")
            return RunDisposition.FAILED
        self._log("ingestion_job_succeeded", claim, state="succeeded")
        return RunDisposition.SUCCEEDED

    @staticmethod
    def _failure_reason(error: Exception) -> str:
        if isinstance(error, (RetryableIngestionError, PermanentIngestionError)):
            return str(error)
        return f"Job processor raised {type(error).__name__}."

    @classmethod
    def _log(cls, event: str, claim: JobClaim, *, state: str) -> None:
        logger.info(event, extra={"fields": cls._fields(claim, state)})

    @staticmethod
    def _fields(claim: JobClaim, state: str) -> dict[str, object]:
        return {
            "job_id": str(claim.job_id),
            "source_id": str(claim.source_id),
            "correlation_id": claim.correlation_id,
            "job_kind": claim.job_kind.value,
            "state": state,
            "attempt": claim.attempt,
            "max_attempts": claim.max_attempts,
        }
