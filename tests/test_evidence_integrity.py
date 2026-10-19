import hashlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from watchtower.db.models import RawEvidence, Source
from watchtower.operations.evidence_integrity import audit_raw_evidence
from watchtower.storage.base import ObjectStorageUnavailableError
from watchtower.storage.local import LocalObjectStore

pytestmark = pytest.mark.integration


def add_reference(
    session: Session,
    store: LocalObjectStore,
    *,
    key: str,
    content: bytes,
) -> RawEvidence:
    source = Source(name=f"Integrity source {uuid4().hex}", kind="dataset")
    session.add(source)
    session.flush()
    stored = store.put_if_absent(key, content)
    raw = RawEvidence(
        source_id=source.id,
        storage_uri=stored.uri,
        storage_key=stored.key,
        content_sha256=hashlib.sha256(content).hexdigest(),
        content_size_bytes=len(content),
        retrieved_at=datetime.now(UTC),
        mime_type="application/octet-stream",
    )
    session.add(raw)
    session.flush()
    return raw


def test_integrity_audit_reports_missing_mismatch_and_orphan_without_writes(
    db_session: Session,
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(tmp_path / "objects", max_bytes=1024)
    valid = add_reference(
        db_session,
        store,
        key=f"raw/{uuid4()}/aa/{'a' * 64}.bin",
        content=b"valid",
    )
    missing = add_reference(
        db_session,
        store,
        key=f"raw/{uuid4()}/bb/{'b' * 64}.bin",
        content=b"missing",
    )
    mismatched = add_reference(
        db_session,
        store,
        key=f"raw/{uuid4()}/cc/{'c' * 64}.bin",
        content=b"original",
    )
    orphan_key = f"raw/{uuid4()}/dd/{'d' * 64}.bin"
    store.put_if_absent(orphan_key, b"orphan")
    missing_key = missing.storage_key
    mismatched_key = mismatched.storage_key
    assert missing_key is not None
    assert mismatched_key is not None
    (tmp_path / "objects").joinpath(*missing_key.split("/")).unlink()
    (tmp_path / "objects").joinpath(*mismatched_key.split("/")).write_bytes(b"changed")

    report = audit_raw_evidence(db_session, store, batch_size=1, concurrency=2)

    assert report.clean is False
    assert report.referenced == 3
    assert report.verified == 1
    assert report.missing == 1
    assert report.mismatched == 1
    assert report.storage_errors == 0
    assert report.orphaned == 1
    assert {(item.kind, item.storage_key) for item in report.findings} == {
        ("missing", missing_key),
        ("mismatched", mismatched_key),
        ("orphaned", orphan_key),
    }
    assert db_session.get(RawEvidence, valid.id) is valid
    assert not store.exists(missing_key)
    assert store.get(mismatched_key) == b"changed"
    assert store.get(orphan_key) == b"orphan"


def test_integrity_audit_reports_object_listing_failure(db_session: Session) -> None:
    store = MagicMock()
    store.iter_keys.side_effect = ObjectStorageUnavailableError("sanitized")

    report = audit_raw_evidence(db_session, store)

    assert report.clean is False
    assert report.storage_errors == 1
    assert report.findings[0].kind == "storage_error"
    assert report.findings[0].storage_key == "raw/"
