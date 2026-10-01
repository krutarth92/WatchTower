import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from watchtower.db.models import ProcessingState, RawEvidence, RetrievalStatus, Source
from watchtower.ingestion.contracts import CONTROL_CHARACTER, RawEvidenceSubmission
from watchtower.storage.base import ObjectStore

SAFE_FILENAME_CHARACTER = re.compile(r"[^A-Za-z0-9._-]+")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
MEDIA_EXTENSIONS = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/xml": ".xml",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/plain": ".txt",
}


class RawEvidenceIntakeError(ValueError):
    """Base error for connector submissions."""


class SourceNotRegisteredError(RawEvidenceIntakeError):
    """Submission references a source not present in the registry."""


class ContentTooLargeError(RawEvidenceIntakeError):
    """Submission exceeds the configured intake limit."""


class InvalidProcessingTransitionError(RawEvidenceIntakeError):
    """Requested processing transition is not valid from the current state."""


@dataclass(frozen=True, slots=True)
class IntakeResult:
    raw_evidence: RawEvidence
    duplicate: bool


def sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename)
    basename = re.split(r"[/\\]", normalized)[-1]
    cleaned = SAFE_FILENAME_CHARACTER.sub("-", basename).strip(" .-_")
    if not cleaned:
        cleaned = "evidence"
    if cleaned.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned[:255]


class RawEvidenceIntake:
    def __init__(self, object_store: ObjectStore, max_bytes: int) -> None:
        self._object_store = object_store
        self._max_bytes = max_bytes

    def ingest(self, session: Session, submission: RawEvidenceSubmission) -> IntakeResult:
        source = session.get(Source, submission.source_id)
        if source is None:
            raise SourceNotRegisteredError(f"Source {submission.source_id} is not registered")
        if len(submission.content) > self._max_bytes:
            raise ContentTooLargeError(
                f"Content has {len(submission.content)} bytes; limit is {self._max_bytes}"
            )

        digest = hashlib.sha256(submission.content).hexdigest()
        key = self._object_key(submission.source_id, digest, submission.mime_type)
        existing = session.scalar(
            select(RawEvidence).where(
                RawEvidence.source_id == submission.source_id,
                RawEvidence.content_sha256 == digest,
            )
        )
        if existing is not None:
            self._repair_reference_if_needed(existing, key, submission.content)
            return IntakeResult(raw_evidence=existing, duplicate=True)

        stored = self._object_store.put_if_absent(key, submission.content)
        raw_evidence = RawEvidence(
            source_id=source.id,
            storage_uri=stored.uri,
            storage_key=stored.key,
            source_locator=submission.source_locator,
            original_filename=(
                sanitize_filename(submission.filename_hint) if submission.filename_hint else None
            ),
            content_sha256=digest,
            content_size_bytes=stored.size_bytes,
            retrieved_at=submission.fetched_at,
            published_at=submission.published_at,
            mime_type=submission.mime_type,
            source_native_id=submission.source_native_id,
            retrieval_status=RetrievalStatus.SUCCEEDED,
            processing_state=ProcessingState.PENDING,
            evidence_metadata=submission.metadata,
        )
        try:
            with session.begin_nested():
                session.add(raw_evidence)
                session.flush()
        except IntegrityError:
            existing = session.scalar(
                select(RawEvidence).where(
                    RawEvidence.source_id == submission.source_id,
                    RawEvidence.content_sha256 == digest,
                )
            )
            if existing is None:
                raise
            self._repair_reference_if_needed(existing, key, submission.content)
            return IntakeResult(raw_evidence=existing, duplicate=True)
        return IntakeResult(raw_evidence=raw_evidence, duplicate=False)

    def mark_processing(self, raw_evidence: RawEvidence) -> None:
        self._require_state(raw_evidence, ProcessingState.PENDING)
        raw_evidence.processing_state = ProcessingState.PROCESSING
        raw_evidence.processing_error = None
        raw_evidence.processing_attempts += 1

    def mark_succeeded(self, raw_evidence: RawEvidence) -> None:
        self._require_state(raw_evidence, ProcessingState.PROCESSING)
        raw_evidence.processing_state = ProcessingState.SUCCEEDED
        raw_evidence.processing_error = None
        raw_evidence.last_processed_at = datetime.now(UTC)

    def mark_failed(self, raw_evidence: RawEvidence, reason: str) -> None:
        self._require_state(raw_evidence, ProcessingState.PROCESSING)
        cleaned = reason.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise RawEvidenceIntakeError(
                "Failure reason must be non-blank and contain no control characters"
            )
        raw_evidence.processing_state = ProcessingState.FAILED
        raw_evidence.processing_error = cleaned[:2000]
        raw_evidence.last_processed_at = datetime.now(UTC)

    def request_reprocessing(self, raw_evidence: RawEvidence) -> None:
        if raw_evidence.processing_state not in {
            ProcessingState.SUCCEEDED,
            ProcessingState.FAILED,
        }:
            raise InvalidProcessingTransitionError(
                f"Cannot reprocess from {raw_evidence.processing_state.value}"
            )
        raw_evidence.processing_state = ProcessingState.PENDING
        raw_evidence.processing_error = None

    def recover_interrupted(self, raw_evidence: RawEvidence) -> None:
        """Return an abandoned processing attempt to the replayable pending state."""
        self._require_state(raw_evidence, ProcessingState.PROCESSING)
        raw_evidence.processing_state = ProcessingState.PENDING
        raw_evidence.processing_error = None

    def _repair_reference_if_needed(
        self, raw_evidence: RawEvidence, key: str, content: bytes
    ) -> None:
        stored = self._object_store.put_if_absent(raw_evidence.storage_key or key, content)
        raw_evidence.storage_key = stored.key
        raw_evidence.storage_uri = stored.uri
        raw_evidence.content_size_bytes = stored.size_bytes

    @staticmethod
    def _object_key(source_id: UUID, digest: str, mime_type: str) -> str:
        extension = MEDIA_EXTENSIONS.get(mime_type, ".bin")
        return f"raw/{source_id}/{digest[:2]}/{digest}{extension}"

    @staticmethod
    def _require_state(raw_evidence: RawEvidence, required: ProcessingState) -> None:
        if raw_evidence.processing_state is not required:
            raise InvalidProcessingTransitionError(
                f"Expected {required.value}, found {raw_evidence.processing_state.value}"
            )
