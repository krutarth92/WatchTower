import hashlib
import json
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import RawEvidence
from watchtower.db.session import build_engine
from watchtower.storage.base import ObjectNotFoundError, ObjectStorageError, ObjectStore
from watchtower.storage.factory import build_object_store

FindingKind = Literal["missing", "mismatched", "storage_error", "orphaned"]


@dataclass(frozen=True, slots=True)
class IntegrityFinding:
    kind: FindingKind
    storage_key: str
    raw_evidence_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    referenced: int
    verified: int
    missing: int
    mismatched: int
    storage_errors: int
    orphaned: int
    findings_truncated: bool
    findings: tuple[IntegrityFinding, ...]

    @property
    def clean(self) -> bool:
        return not (self.missing or self.mismatched or self.storage_errors or self.orphaned)


@dataclass(frozen=True, slots=True)
class _Reference:
    raw_evidence_id: UUID
    storage_key: str
    content_sha256: str
    content_size_bytes: int | None


@dataclass(frozen=True, slots=True)
class _CheckResult:
    reference: _Reference
    kind: FindingKind | None


def audit_raw_evidence(
    session: Session,
    object_store: ObjectStore,
    *,
    batch_size: int = 100,
    concurrency: int = 4,
    max_findings: int = 100,
) -> IntegrityReport:
    if not 1 <= batch_size <= 10_000:
        raise ValueError("batch_size must be between 1 and 10000")
    if not 1 <= concurrency <= 32:
        raise ValueError("concurrency must be between 1 and 32")
    if not 1 <= max_findings <= 10_000:
        raise ValueError("max_findings must be between 1 and 10000")

    counts = {
        "referenced": 0,
        "verified": 0,
        "missing": 0,
        "mismatched": 0,
        "storage_errors": 0,
        "orphaned": 0,
    }
    findings: list[IntegrityFinding] = []
    truncated = False

    statement = (
        select(
            RawEvidence.id,
            RawEvidence.storage_key,
            RawEvidence.content_sha256,
            RawEvidence.content_size_bytes,
        )
        .where(RawEvidence.storage_key.is_not(None))
        .order_by(RawEvidence.id)
        .execution_options(yield_per=batch_size)
    )
    rows = session.execute(statement)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for partition in rows.partitions(batch_size):
            references = [
                _Reference(
                    raw_evidence_id=row.id,
                    storage_key=row.storage_key,
                    content_sha256=row.content_sha256,
                    content_size_bytes=row.content_size_bytes,
                )
                for row in partition
                if row.storage_key is not None
            ]
            for result in executor.map(
                lambda item: _check_reference(object_store, item), references
            ):
                counts["referenced"] += 1
                if result.kind is None:
                    counts["verified"] += 1
                    continue
                counts[result.kind] += 1
                truncated = (
                    _append_finding(
                        findings,
                        IntegrityFinding(
                            kind=result.kind,
                            storage_key=result.reference.storage_key,
                            raw_evidence_id=result.reference.raw_evidence_id,
                        ),
                        max_findings,
                    )
                    or truncated
                )

    try:
        for storage_key in object_store.iter_keys("raw"):
            referenced = session.scalar(
                select(exists().where(RawEvidence.storage_key == storage_key))
            )
            if not referenced:
                counts["orphaned"] += 1
                truncated = (
                    _append_finding(
                        findings,
                        IntegrityFinding(kind="orphaned", storage_key=storage_key),
                        max_findings,
                    )
                    or truncated
                )
    except ObjectStorageError:
        counts["storage_errors"] += 1
        truncated = (
            _append_finding(
                findings,
                IntegrityFinding(kind="storage_error", storage_key="raw/"),
                max_findings,
            )
            or truncated
        )

    return IntegrityReport(
        referenced=counts["referenced"],
        verified=counts["verified"],
        missing=counts["missing"],
        mismatched=counts["mismatched"],
        storage_errors=counts["storage_errors"],
        orphaned=counts["orphaned"],
        findings_truncated=truncated,
        findings=tuple(findings),
    )


def _check_reference(object_store: ObjectStore, reference: _Reference) -> _CheckResult:
    try:
        content = object_store.get(reference.storage_key)
    except ObjectNotFoundError:
        return _CheckResult(reference=reference, kind="missing")
    except ObjectStorageError:
        return _CheckResult(reference=reference, kind="storage_error")
    digest = hashlib.sha256(content).hexdigest()
    size_matches = (
        reference.content_size_bytes is None or len(content) == reference.content_size_bytes
    )
    if digest != reference.content_sha256 or not size_matches:
        return _CheckResult(reference=reference, kind="mismatched")
    return _CheckResult(reference=reference, kind=None)


def _append_finding(
    findings: list[IntegrityFinding], finding: IntegrityFinding, max_findings: int
) -> bool:
    if len(findings) >= max_findings:
        return True
    findings.append(finding)
    return False


def _report_json(report: IntegrityReport) -> str:
    payload = asdict(report)
    payload["clean"] = report.clean
    return json.dumps(payload, default=str, sort_keys=True)


def main(arguments: Iterable[str] | None = None) -> int:
    del arguments
    settings = Settings()  # pyright: ignore[reportCallIssue]
    engine = build_engine(settings)
    try:
        store = build_object_store(settings)
        with Session(engine) as session:
            report = audit_raw_evidence(session, store)
        print(_report_json(report))
        return 0 if report.clean else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
