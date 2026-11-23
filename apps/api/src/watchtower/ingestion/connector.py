"""Shared source-connector outcomes and bounded metrics."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ConnectorRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    SOURCE_UNAVAILABLE = "source_unavailable"


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
