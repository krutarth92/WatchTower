"""Strict fixed-URL retrieval and replay-safe source-object ingestion."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from watchtower.db.models import ProcessingState
from watchtower.ingestion.connector import (
    ConnectorIssue,
    ConnectorMetrics,
    ConnectorRunResult,
    ConnectorRunStatus,
)
from watchtower.ingestion.contracts import RawEvidenceSubmission, SourceRegistration
from watchtower.ingestion.normalization import NormalizationEmitter, NormalizationRecord
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.ingestion.source_registry import SourceRegistry


class FixedSourceFetchError(RuntimeError):
    """The fixed upstream could not provide an acceptable response."""


class InvalidSourcePayloadError(ValueError):
    """Retrieved bytes do not match the approved source contract."""


@dataclass(frozen=True, slots=True)
class FixedSourceFetchResult:
    content: bytes
    fetched_at: datetime
    media_type: str
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class SourceObject:
    source_native_id: str
    object_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParsedSourcePayload:
    source_native_id: str
    published_at: datetime | None
    metadata: dict[str, Any]
    objects: tuple[SourceObject, ...]


class SourcePayloadParser(Protocol):
    def parse(self, content: bytes, *, fetched_at: datetime) -> ParsedSourcePayload: ...


@dataclass(frozen=True, slots=True)
class FixedSourceDefinition:
    key: str
    url: str
    filename: str
    accepted_media_types: frozenset[str]
    registration: SourceRegistration


class FixedSourceFetcher:
    """Retrieve one allowlisted URL without redirects, compression or ambient proxies."""

    def __init__(
        self,
        definition: FixedSourceDefinition,
        max_bytes: int,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._definition = definition
        self._max_bytes = max_bytes
        self._transport = transport
        self._timeout = timeout or httpx.Timeout(30.0, connect=10.0, pool=10.0, write=10.0)

    def fetch(self) -> FixedSourceFetchResult:
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=self._timeout,
                transport=self._transport,
                trust_env=False,
            ) as client:
                with client.stream(
                    "GET",
                    self._definition.url,
                    headers={
                        "Accept": ", ".join(sorted(self._definition.accepted_media_types)),
                        "Accept-Encoding": "identity",
                        "User-Agent": "WATCHTOWER-source-ingestion/1.0",
                    },
                ) as response:
                    if response.is_redirect:
                        raise FixedSourceFetchError("Upstream redirects are not accepted")
                    if response.status_code != 200:
                        raise FixedSourceFetchError(
                            f"Upstream returned HTTP {response.status_code}"
                        )
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if media_type not in self._definition.accepted_media_types:
                        raise FixedSourceFetchError(
                            f"Upstream media type {media_type or 'missing'} is not accepted"
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise FixedSourceFetchError("Encoded upstream payloads are not accepted")
                    declared = response.headers.get("content-length")
                    if declared is not None:
                        try:
                            declared_size = int(declared)
                        except ValueError as error:
                            raise FixedSourceFetchError(
                                "Upstream Content-Length is invalid"
                            ) from error
                        if declared_size > self._max_bytes:
                            raise FixedSourceFetchError(
                                f"Upstream payload exceeds {self._max_bytes} bytes"
                            )
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_bytes:
                            raise FixedSourceFetchError(
                                f"Upstream payload exceeds {self._max_bytes} bytes"
                            )
                    if not body:
                        raise FixedSourceFetchError("Upstream payload is empty")
                    return FixedSourceFetchResult(
                        content=bytes(body),
                        fetched_at=datetime.now(UTC),
                        media_type=media_type,
                        etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"),
                    )
        except FixedSourceFetchError:
            raise
        except httpx.HTTPError as error:
            raise FixedSourceFetchError(
                f"Upstream request failed with {type(error).__name__}"
            ) from error


class FixedSourceConnector:
    def __init__(
        self,
        definition: FixedSourceDefinition,
        parser: SourcePayloadParser,
        intake: RawEvidenceIntake,
        emitter: NormalizationEmitter,
        *,
        registry: SourceRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._definition = definition
        self._parser = parser
        self._intake = intake
        self._emitter = emitter
        self._registry = registry or SourceRegistry()
        self._logger = logger or logging.getLogger(
            f"watchtower.ingestion.{definition.key.replace('-', '_')}"
        )

    def run_live(self, session: Session, fetcher: FixedSourceFetcher) -> ConnectorRunResult:
        started = monotonic()
        source_id = self._register_source(session)
        try:
            fetched = fetcher.fetch()
        except FixedSourceFetchError as error:
            result = ConnectorRunResult(
                ConnectorRunStatus.SOURCE_UNAVAILABLE,
                source_id,
                None,
                False,
                ConnectorMetrics(0, 0, 0, 0, self._duration_ms(started)),
                (ConnectorIssue(None, None, type(error).__name__, str(error)),),
            )
            self._log_result(result)
            return result
        return self._process(session, source_id, fetched, started)

    def run_fixture(
        self,
        session: Session,
        content: bytes,
        *,
        fetched_at: datetime,
        media_type: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> ConnectorRunResult:
        started = monotonic()
        source_id = self._register_source(session)
        fetched = FixedSourceFetchResult(
            content,
            fetched_at,
            media_type or next(iter(self._definition.accepted_media_types)),
            etag,
            last_modified,
        )
        return self._process(session, source_id, fetched, started)

    def _process(
        self,
        session: Session,
        source_id: UUID,
        fetched: FixedSourceFetchResult,
        started: float,
    ) -> ConnectorRunResult:
        submission = RawEvidenceSubmission(
            source_id=source_id,
            content=fetched.content,
            source_locator=self._definition.url,
            fetched_at=fetched.fetched_at,
            mime_type=fetched.media_type,
            filename_hint=self._definition.filename,
            metadata={
                "integration_key": self._definition.key,
                "etag": fetched.etag,
                "last_modified": fetched.last_modified,
            },
        )
        intake_result = self._intake.ingest(session, submission)
        raw = intake_result.raw_evidence
        if intake_result.duplicate and raw.processing_state is ProcessingState.SUCCEEDED:
            result = ConnectorRunResult(
                ConnectorRunStatus.SKIPPED,
                source_id,
                raw.id,
                True,
                ConnectorMetrics(len(fetched.content), 0, 0, 0, self._duration_ms(started)),
            )
            self._log_result(result)
            return result
        if raw.processing_state is ProcessingState.FAILED:
            self._intake.request_reprocessing(raw)
        elif raw.processing_state is ProcessingState.PROCESSING:
            self._intake.recover_interrupted(raw)
        self._intake.mark_processing(raw)

        try:
            parsed = self._parser.parse(fetched.content, fetched_at=fetched.fetched_at)
            if not parsed.objects:
                raise InvalidSourcePayloadError("Approved source payload contained no objects")
            if parsed.published_at is not None and parsed.published_at > fetched.fetched_at:
                raise InvalidSourcePayloadError(
                    "Approved source publication timestamp is later than the fetch time"
                )
        except InvalidSourcePayloadError as error:
            self._intake.mark_failed(raw, str(error))
            session.flush()
            result = ConnectorRunResult(
                ConnectorRunStatus.FAILED,
                source_id,
                raw.id,
                intake_result.duplicate,
                ConnectorMetrics(len(fetched.content), 0, 0, 1, self._duration_ms(started)),
                (ConnectorIssue(None, None, type(error).__name__, str(error)),),
            )
            self._log_result(result)
            return result

        raw.source_native_id = parsed.source_native_id
        raw.published_at = parsed.published_at
        raw.evidence_metadata = {
            **raw.evidence_metadata,
            **parsed.metadata,
            "source_native_id": parsed.source_native_id,
        }
        issues: list[ConnectorIssue] = []
        emitted = 0
        for index, item in enumerate(parsed.objects):
            try:
                self._emitter.emit(
                    NormalizationRecord(
                        source_id=source_id,
                        raw_evidence_id=raw.id,
                        source_native_id=item.source_native_id,
                        object_type=item.object_type,
                        object_index=index,
                        payload=item.payload,
                    )
                )
                emitted += 1
            except Exception as error:
                issues.append(
                    ConnectorIssue(
                        index,
                        item.source_native_id,
                        type(error).__name__,
                        self._safe_issue_detail(error),
                    )
                )

        if issues:
            self._intake.mark_failed(
                raw,
                f"{len(issues)} of {len(parsed.objects)} source objects failed at the "
                "normalization boundary",
            )
            status = ConnectorRunStatus.FAILED
        else:
            self._intake.mark_succeeded(raw)
            status = ConnectorRunStatus.SUCCEEDED
        session.flush()
        result = ConnectorRunResult(
            status,
            source_id,
            raw.id,
            intake_result.duplicate,
            ConnectorMetrics(
                len(fetched.content),
                len(parsed.objects),
                emitted,
                len(issues),
                self._duration_ms(started),
            ),
            tuple(issues),
        )
        self._log_result(result)
        return result

    def _register_source(self, session: Session) -> UUID:
        return self._registry.register(session, self._definition.registration).source.id

    @staticmethod
    def _safe_issue_detail(error: Exception) -> str:
        if isinstance(error, (InvalidSourcePayloadError, ValueError)):
            return str(error)[:500]
        return f"Normalization emitter raised {type(error).__name__}"

    @staticmethod
    def _duration_ms(started: float) -> int:
        return max(0, round((monotonic() - started) * 1000))

    def _log_result(self, result: ConnectorRunResult) -> None:
        self._logger.info(
            "fixed_source_connector_run",
            extra={
                "fields": {
                    "integration_key": self._definition.key,
                    "status": result.status.value,
                    "source_id": str(result.source_id),
                    "raw_evidence_id": (
                        str(result.raw_evidence_id) if result.raw_evidence_id else None
                    ),
                    "duplicate": result.duplicate,
                    "bytes_retrieved": result.metrics.bytes_retrieved,
                    "objects_seen": result.metrics.objects_seen,
                    "objects_emitted": result.metrics.objects_emitted,
                    "objects_failed": result.metrics.objects_failed,
                    "duration_ms": result.metrics.duration_ms,
                }
            },
        )


SourceRegistrationFactory = Callable[[], SourceRegistration]
