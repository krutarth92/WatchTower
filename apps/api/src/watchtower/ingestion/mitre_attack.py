"""Fixed-source MITRE ATT&CK Enterprise STIX reference connector."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from time import monotonic
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from watchtower.db.models import ProcessingState, Source
from watchtower.ingestion.contracts import RawEvidenceSubmission, SourceRegistration
from watchtower.ingestion.normalization import NormalizationEmitter, NormalizationRecord
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.ingestion.source_registry import SourceRegistry

ATTACK_VERSION = "19.2"
ATTACK_DOMAIN = "enterprise-attack"
ATTACK_FILENAME = f"enterprise-attack-{ATTACK_VERSION}.json"
ATTACK_URL = (
    f"https://raw.githubusercontent.com/mitre-attack/attack-stix-data/v{ATTACK_VERSION}/"
    f"{ATTACK_DOMAIN}/{ATTACK_FILENAME}"
)
ATTACK_RELEASED_AT = datetime(2026, 8, 5, tzinfo=UTC)
ATTACK_NOTICE = (
    "© 2026 The MITRE Corporation. This work is reproduced and distributed with the "
    "permission of The MITRE Corporation."
)
ALLOWED_MEDIA_TYPES = {"application/json", "application/octet-stream", "text/plain"}
BUNDLE_ID = re.compile(r"^bundle--[0-9a-fA-F-]{36}$")
STIX_ID = re.compile(r"^[a-z][a-z0-9-]{0,99}--[0-9a-fA-F-]{36}$")


class ConnectorRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    SOURCE_UNAVAILABLE = "source_unavailable"


class MitreAttackFetchError(RuntimeError):
    """The fixed upstream could not provide an acceptable response."""


class InvalidAttackBundleError(ValueError):
    """The retrieved bytes are not a structurally valid STIX bundle."""


@dataclass(frozen=True, slots=True)
class FetchResult:
    content: bytes
    fetched_at: datetime
    media_type: str
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectorIssue:
    object_index: int | None
    source_native_id: str | None
    error_type: str
    detail: str


@dataclass(frozen=True, slots=True)
class ConnectorMetrics:
    bytes_retrieved: int
    objects_seen: int
    objects_emitted: int
    objects_failed: int
    duration_ms: int


@dataclass(frozen=True, slots=True)
class ConnectorRunResult:
    status: ConnectorRunStatus
    source_id: UUID
    raw_evidence_id: UUID | None
    duplicate: bool
    metrics: ConnectorMetrics
    issues: tuple[ConnectorIssue, ...] = ()


def register_mitre_attack_source(
    session: Session, registry: SourceRegistry | None = None
) -> Source:
    registration = SourceRegistration.model_validate(
        {
            "name": "MITRE ATT&CK Enterprise",
            "kind": "dataset",
            "base_url": "https://github.com/mitre-attack/attack-stix-data/",
            "policy_notes": f"Versioned STIX 2.1 import. {ATTACK_NOTICE}",
            "license_name": "MITRE ATT&CK License",
            "license_url": (
                "https://github.com/mitre-attack/attack-stix-data/blob/master/LICENSE.txt"
            ),
            "metadata": {"domain": ATTACK_DOMAIN, "format": "STIX 2.1"},
        }
    )
    return (registry or SourceRegistry()).register(session, registration).source


class MitreAttackFetcher:
    """Retrieve the single approved ATT&CK URL with bounded HTTP behavior."""

    def __init__(
        self,
        max_bytes: int,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._transport = transport
        self._timeout = timeout or httpx.Timeout(30.0, connect=10.0, pool=10.0, write=10.0)

    def fetch(self) -> FetchResult:
        try:
            with httpx.Client(
                follow_redirects=False,
                timeout=self._timeout,
                transport=self._transport,
                trust_env=False,
            ) as client:
                with client.stream(
                    "GET",
                    ATTACK_URL,
                    headers={"Accept": "application/json", "Accept-Encoding": "identity"},
                ) as response:
                    if response.is_redirect:
                        raise MitreAttackFetchError("Upstream redirects are not accepted")
                    if response.status_code != 200:
                        raise MitreAttackFetchError(
                            f"Upstream returned HTTP {response.status_code}"
                        )
                    media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if media_type not in ALLOWED_MEDIA_TYPES:
                        raise MitreAttackFetchError(
                            f"Upstream media type {media_type or 'missing'} is not accepted"
                        )
                    content_encoding = response.headers.get("content-encoding", "identity").lower()
                    if content_encoding != "identity":
                        raise MitreAttackFetchError("Encoded upstream payloads are not accepted")
                    content_length = response.headers.get("content-length")
                    if content_length is not None:
                        try:
                            declared_size = int(content_length)
                        except ValueError as error:
                            raise MitreAttackFetchError(
                                "Upstream Content-Length is invalid"
                            ) from error
                        if declared_size > self._max_bytes:
                            raise MitreAttackFetchError(
                                f"Upstream payload exceeds {self._max_bytes} bytes"
                            )
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_bytes:
                            raise MitreAttackFetchError(
                                f"Upstream payload exceeds {self._max_bytes} bytes"
                            )
                    if not body:
                        raise MitreAttackFetchError("Upstream payload is empty")
                    return FetchResult(
                        content=bytes(body),
                        fetched_at=datetime.now(UTC),
                        media_type="application/json",
                        etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"),
                    )
        except MitreAttackFetchError:
            raise
        except httpx.HTTPError as error:
            raise MitreAttackFetchError(
                f"Upstream request failed with {type(error).__name__}"
            ) from error


class MitreAttackConnector:
    def __init__(
        self,
        intake: RawEvidenceIntake,
        emitter: NormalizationEmitter,
        *,
        registry: SourceRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._intake = intake
        self._emitter = emitter
        self._registry = registry or SourceRegistry()
        self._logger = logger or logging.getLogger("watchtower.ingestion.mitre_attack")

    def run_live(self, session: Session, fetcher: MitreAttackFetcher) -> ConnectorRunResult:
        started = monotonic()
        source_id = self._register_source(session)
        try:
            fetched = fetcher.fetch()
        except MitreAttackFetchError as error:
            issue = ConnectorIssue(None, None, type(error).__name__, str(error))
            result = ConnectorRunResult(
                status=ConnectorRunStatus.SOURCE_UNAVAILABLE,
                source_id=source_id,
                raw_evidence_id=None,
                duplicate=False,
                metrics=ConnectorMetrics(0, 0, 0, 0, self._duration_ms(started)),
                issues=(issue,),
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
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> ConnectorRunResult:
        """Exercise the same ingestion path with inert local fixture bytes."""
        started = monotonic()
        source_id = self._register_source(session)
        fetched = FetchResult(content, fetched_at, "application/json", etag, last_modified)
        return self._process(session, source_id, fetched, started)

    def _process(
        self,
        session: Session,
        source_id: UUID,
        fetched: FetchResult,
        started: float,
    ) -> ConnectorRunResult:
        submission = RawEvidenceSubmission(
            source_id=source_id,
            content=fetched.content,
            source_locator=ATTACK_URL,
            fetched_at=fetched.fetched_at,
            published_at=ATTACK_RELEASED_AT,
            mime_type="application/json",
            filename_hint=ATTACK_FILENAME,
            metadata={
                "attack_domain": ATTACK_DOMAIN,
                "attack_version": ATTACK_VERSION,
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
            bundle_id, objects = self._parse_bundle(fetched.content)
        except InvalidAttackBundleError as error:
            self._intake.mark_failed(raw, str(error))
            session.flush()
            issue = ConnectorIssue(None, None, type(error).__name__, str(error))
            result = ConnectorRunResult(
                ConnectorRunStatus.FAILED,
                source_id,
                raw.id,
                intake_result.duplicate,
                ConnectorMetrics(len(fetched.content), 0, 0, 1, self._duration_ms(started)),
                (issue,),
            )
            self._log_result(result)
            return result

        raw.source_native_id = bundle_id
        raw.evidence_metadata = {**raw.evidence_metadata, "bundle_id": bundle_id}
        issues: list[ConnectorIssue] = []
        emitted = 0
        for index, item in enumerate(objects):
            try:
                object_id, object_type, payload = self._validate_object(item, index)
                self._emitter.emit(
                    NormalizationRecord(
                        source_id=source_id,
                        raw_evidence_id=raw.id,
                        source_native_id=object_id,
                        object_type=object_type,
                        object_index=index,
                        payload=payload,
                    )
                )
                emitted += 1
            except Exception as error:
                object_id = item.get("id") if isinstance(item, dict) else None
                issues.append(
                    ConnectorIssue(
                        index,
                        object_id if isinstance(object_id, str) else None,
                        type(error).__name__,
                        self._safe_issue_detail(error),
                    )
                )

        if issues:
            self._intake.mark_failed(
                raw,
                f"{len(issues)} of {len(objects)} STIX objects failed "
                "at the normalization boundary",
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
                len(objects),
                emitted,
                len(issues),
                self._duration_ms(started),
            ),
            tuple(issues),
        )
        self._log_result(result)
        return result

    def _register_source(self, session: Session) -> UUID:
        return register_mitre_attack_source(session, self._registry).id

    @staticmethod
    def _parse_bundle(content: bytes) -> tuple[str, list[Any]]:
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidAttackBundleError("Payload is not valid UTF-8 JSON") from error
        if not isinstance(parsed, dict) or parsed.get("type") != "bundle":
            raise InvalidAttackBundleError("Payload must be a STIX bundle object")
        bundle_id = parsed.get("id")
        if not isinstance(bundle_id, str) or not BUNDLE_ID.fullmatch(bundle_id):
            raise InvalidAttackBundleError("Bundle has an invalid STIX identifier")
        objects = parsed.get("objects")
        if not isinstance(objects, list):
            raise InvalidAttackBundleError("Bundle objects must be an array")
        return bundle_id, objects

    @staticmethod
    def _validate_object(item: Any, index: int) -> tuple[str, str, dict[str, Any]]:
        if not isinstance(item, dict):
            raise InvalidAttackBundleError(f"Object {index} must be a JSON object")
        object_id = item.get("id")
        object_type = item.get("type")
        if not isinstance(object_id, str) or not STIX_ID.fullmatch(object_id):
            raise InvalidAttackBundleError(f"Object {index} has an invalid STIX identifier")
        if not isinstance(object_type, str) or not object_id.startswith(f"{object_type}--"):
            raise InvalidAttackBundleError(f"Object {index} type does not match its identifier")
        return object_id, object_type, item

    @staticmethod
    def _safe_issue_detail(error: Exception) -> str:
        if isinstance(error, InvalidAttackBundleError):
            return str(error)[:500]
        return f"Normalization emitter raised {type(error).__name__}"

    @staticmethod
    def _duration_ms(started: float) -> int:
        return max(0, round((monotonic() - started) * 1000))

    def _log_result(self, result: ConnectorRunResult) -> None:
        self._logger.info(
            "mitre_attack_connector_run",
            extra={
                "fields": {
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
