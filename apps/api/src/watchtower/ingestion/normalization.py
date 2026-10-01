"""Replay-safe staged normalization with durable per-record outcomes."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import (
    IntelligenceType,
    NormalizationLedger,
    NormalizationStage,
    NormalizationStatus,
    Observation,
    Origin,
    RawEvidence,
)


@dataclass(frozen=True, slots=True)
class NormalizationRecord:
    """One source-native object with immutable raw provenance."""

    source_id: UUID
    raw_evidence_id: UUID
    source_native_id: str
    object_type: str
    object_index: int
    payload: dict[str, Any]


class NormalizationEmitter(Protocol):
    def emit(self, record: NormalizationRecord) -> None: ...


class CanonicalObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: UUID
    raw_evidence_id: UUID
    source_native_id: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1)
    observed_at: datetime
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("source_native_id", "title", "summary")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be blank")
        return cleaned

    @field_validator("observed_at", "first_seen", "last_seen")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_time_range(self) -> "CanonicalObservation":
        if (
            self.first_seen is not None
            and self.last_seen is not None
            and self.first_seen > self.last_seen
        ):
            raise ValueError("first_seen cannot be later than last_seen")
        return self


class UnsupportedSourceRecord(ValueError):
    """A valid source object is outside the approved canonical mapping."""


class RejectedSourceRecord(ValueError):
    """A supported source object is malformed or conflicts with canonical data."""


class NormalizationPipelineError(RuntimeError):
    """A record failed and its controlled state was stored in the ledger."""


class SourceRecordParser[ParsedRecordT](Protocol):
    def parse(self, record: NormalizationRecord) -> ParsedRecordT: ...


class CanonicalNormalizer[ParsedRecordT](Protocol):
    def normalize(
        self, parsed: ParsedRecordT, record: NormalizationRecord
    ) -> CanonicalObservation: ...


class DeduplicationAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    KEEP = "keep"


@dataclass(frozen=True, slots=True)
class DeduplicationDecision:
    action: DeduplicationAction
    existing: Observation | None
    reason: str | None = None


class ObservationRepository(Protocol):
    def deduplicate(
        self, session: Session, canonical: CanonicalObservation, fingerprint: str
    ) -> DeduplicationDecision: ...

    def persist(
        self,
        session: Session,
        canonical: CanonicalObservation,
        fingerprint: str,
        decision: DeduplicationDecision,
    ) -> Observation: ...


class SqlAlchemyObservationRepository:
    def deduplicate(
        self, session: Session, canonical: CanonicalObservation, fingerprint: str
    ) -> DeduplicationDecision:
        existing = session.scalar(
            select(Observation).where(
                Observation.source_id == canonical.source_id,
                Observation.source_native_id == canonical.source_native_id,
            )
        )
        if existing is None:
            return DeduplicationDecision(DeduplicationAction.CREATE, None)
        normalization = existing.observation_metadata.get("normalization")
        existing_fingerprint = (
            normalization.get("fingerprint") if isinstance(normalization, dict) else None
        )
        if canonical.observed_at < existing.observed_at:
            return DeduplicationDecision(
                DeduplicationAction.KEEP,
                existing,
                "existing observation has a newer source timestamp",
            )
        if canonical.observed_at == existing.observed_at:
            if existing_fingerprint == fingerprint:
                return DeduplicationDecision(
                    DeduplicationAction.KEEP,
                    existing,
                    "canonical observation already exists",
                )
            raise RejectedSourceRecord(
                "conflicting canonical content has the same source timestamp"
            )
        return DeduplicationDecision(DeduplicationAction.UPDATE, existing)

    def persist(
        self,
        session: Session,
        canonical: CanonicalObservation,
        fingerprint: str,
        decision: DeduplicationDecision,
    ) -> Observation:
        if decision.action is DeduplicationAction.KEEP:
            assert decision.existing is not None
            return decision.existing
        metadata: dict[str, Any] = {
            "normalization": {"fingerprint": fingerprint, "pipeline_version": 1},
            "source": canonical.metadata,
        }
        with session.begin_nested():
            if decision.action is DeduplicationAction.CREATE:
                observation = Observation(
                    source_id=canonical.source_id,
                    raw_evidence_id=canonical.raw_evidence_id,
                    source_native_id=canonical.source_native_id,
                    title=canonical.title,
                    summary=canonical.summary,
                    observed_at=canonical.observed_at,
                    first_seen=canonical.first_seen,
                    last_seen=canonical.last_seen,
                    confidence=canonical.confidence,
                    intelligence_type=IntelligenceType.OBSERVED,
                    origin=Origin.IMPORTED,
                    observation_metadata=metadata,
                )
                session.add(observation)
            else:
                assert decision.existing is not None
                observation = decision.existing
                observation.raw_evidence_id = canonical.raw_evidence_id
                observation.title = canonical.title
                observation.summary = canonical.summary
                observation.observed_at = canonical.observed_at
                observation.first_seen = canonical.first_seen
                observation.last_seen = canonical.last_seen
                observation.confidence = canonical.confidence
                observation.observation_metadata = metadata
            session.flush()
        return observation


class NormalizationPipeline[ParsedRecordT]:
    """Transaction-scoped emitter used directly by source connectors."""

    def __init__(
        self,
        session: Session,
        parser: SourceRecordParser[ParsedRecordT],
        normalizer: CanonicalNormalizer[ParsedRecordT],
        repository: ObservationRepository | None = None,
        stage_recorder: Callable[[NormalizationStage, float], None] | None = None,
    ) -> None:
        self._session = session
        self._parser = parser
        self._normalizer = normalizer
        self._repository = repository or SqlAlchemyObservationRepository()
        self._stage_recorder = stage_recorder

    def emit(self, record: NormalizationRecord) -> None:
        payload_hash = self._payload_hash(record.payload)
        ledger = self._begin_attempt(record, payload_hash)
        try:
            parsed = self._run_stage(
                ledger,
                NormalizationStage.PARSE,
                lambda: self._parser.parse(record),
            )

            canonical = self._run_stage(
                ledger,
                NormalizationStage.NORMALIZE,
                lambda: self._normalizer.normalize(parsed, record),
            )

            def validate() -> str:
                self._validate_provenance(record, canonical)
                return self._canonical_fingerprint(canonical)

            fingerprint = self._run_stage(ledger, NormalizationStage.VALIDATE, validate)

            decision = self._run_stage(
                ledger,
                NormalizationStage.DEDUPLICATE,
                lambda: self._repository.deduplicate(self._session, canonical, fingerprint),
            )

            observation = self._run_stage(
                ledger,
                NormalizationStage.PERSIST,
                lambda: self._repository.persist(
                    self._session,
                    canonical,
                    fingerprint,
                    decision,
                ),
            )
        except UnsupportedSourceRecord as error:
            self._finish(ledger, NormalizationStatus.REJECTED, str(error))
            return
        except RejectedSourceRecord as error:
            reason = self._bounded_reason(str(error))
            self._finish(ledger, NormalizationStatus.REJECTED, reason)
            raise NormalizationPipelineError(reason) from error
        except Exception as error:
            reason = f"{ledger.stage.value} stage raised {type(error).__name__}"
            self._finish(ledger, NormalizationStatus.FAILED, reason)
            raise NormalizationPipelineError(reason) from error

        ledger.observation_id = observation.id
        if decision.action is DeduplicationAction.KEEP:
            self._finish(ledger, NormalizationStatus.DEDUPLICATED, decision.reason)
        else:
            self._finish(ledger, NormalizationStatus.SUCCEEDED, None)

    def _run_stage[ResultT](
        self,
        ledger: NormalizationLedger,
        stage: NormalizationStage,
        operation: Callable[[], ResultT],
    ) -> ResultT:
        ledger.stage = stage
        if self._stage_recorder is None:
            return operation()
        started = perf_counter()
        try:
            return operation()
        finally:
            self._stage_recorder(stage, (perf_counter() - started) * 1000)

    def _begin_attempt(self, record: NormalizationRecord, payload_hash: str) -> NormalizationLedger:
        ledger = self._session.scalar(
            select(NormalizationLedger).where(
                NormalizationLedger.raw_evidence_id == record.raw_evidence_id,
                NormalizationLedger.object_index == record.object_index,
            )
        )
        if ledger is None:
            ledger = NormalizationLedger(
                source_id=record.source_id,
                raw_evidence_id=record.raw_evidence_id,
                source_native_id=record.source_native_id,
                object_type=record.object_type,
                object_index=record.object_index,
                payload_sha256=payload_hash,
                status=NormalizationStatus.PROCESSING,
                stage=NormalizationStage.PARSE,
                attempts=1,
            )
            self._session.add(ledger)
            self._session.flush()
            return ledger
        if (
            ledger.source_id != record.source_id
            or ledger.source_native_id != record.source_native_id
            or ledger.object_type != record.object_type
            or ledger.payload_sha256 != payload_hash
        ):
            raise NormalizationPipelineError(
                "Raw evidence object index conflicts with its recorded normalization identity"
            )
        ledger.status = NormalizationStatus.PROCESSING
        ledger.stage = NormalizationStage.PARSE
        ledger.reason = None
        ledger.attempts += 1
        ledger.processed_at = None
        self._session.flush()
        return ledger

    def _validate_provenance(
        self, record: NormalizationRecord, canonical: CanonicalObservation
    ) -> None:
        raw = self._session.get(RawEvidence, record.raw_evidence_id)
        if raw is None or raw.source_id != record.source_id:
            raise RejectedSourceRecord("raw evidence does not match the source provenance")
        if canonical.source_id != record.source_id:
            raise RejectedSourceRecord("canonical source does not match record provenance")
        if canonical.raw_evidence_id != record.raw_evidence_id:
            raise RejectedSourceRecord("canonical raw evidence does not match record provenance")
        if canonical.source_native_id != record.source_native_id:
            raise RejectedSourceRecord("canonical native ID does not match source record")

    def _finish(
        self,
        ledger: NormalizationLedger,
        status: NormalizationStatus,
        reason: str | None,
    ) -> None:
        ledger.status = status
        ledger.reason = self._bounded_reason(reason) if reason else None
        ledger.processed_at = datetime.now(UTC)
        self._session.flush()

    @staticmethod
    def _payload_hash(payload: dict[str, Any]) -> str:
        try:
            encoded = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        except (TypeError, ValueError) as error:
            raise NormalizationPipelineError("Source payload is not canonical JSON") from error
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _canonical_fingerprint(canonical: CanonicalObservation) -> str:
        payload = canonical.model_dump(mode="json", exclude={"raw_evidence_id"})
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _bounded_reason(reason: str) -> str:
        cleaned = " ".join(reason.split())
        return (cleaned or "normalization failed")[:2000]
