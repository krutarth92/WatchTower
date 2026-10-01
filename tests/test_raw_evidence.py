from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import ProcessingState, RawEvidence
from watchtower.ingestion.contracts import RawEvidenceSubmission, SourceRegistration
from watchtower.ingestion.raw_evidence import (
    ContentTooLargeError,
    InvalidProcessingTransitionError,
    RawEvidenceIntake,
    SourceNotRegisteredError,
)
from watchtower.ingestion.source_registry import SourceConflictError, SourceRegistry
from watchtower.storage.base import ObjectCollisionError, StoredObjectTooLargeError
from watchtower.storage.local import LocalObjectStore, UnsafeObjectKeyError

pytestmark = pytest.mark.integration


def register_source(session: Session, suffix: str = "") -> SourceRegistration:
    registration = SourceRegistration.model_validate(
        {
            "name": f"Fixture Feed {uuid4().hex}{suffix}",
            "kind": "dataset",
            "base_url": "https://example.test/feed/",
            "policy_notes": "Fixture use only",
            "license_name": "Test License",
            "license_url": "https://example.test/license/",
            "metadata": {"tier": "test"},
        }
    )
    SourceRegistry().register(session, registration)
    return registration


def source_id_for(session: Session, registration: SourceRegistration) -> UUID:
    result = SourceRegistry().register(session, registration)
    assert result.duplicate is True
    return result.source.id


def make_submission(source_id: UUID, content: bytes = b'{"fixture":1}') -> RawEvidenceSubmission:
    return RawEvidenceSubmission(
        source_id=source_id,
        content=content,
        source_locator="https://example.test/feed/current.json",
        fetched_at=datetime(2026, 9, 27, 8, 0, tzinfo=UTC),
        published_at=datetime(2026, 9, 26, 8, 0, tzinfo=UTC),
        mime_type="application/json",
        filename_hint="../../CON",
        source_native_id="fixture-current",
        metadata={"etag": "fixture-etag"},
    )


def test_source_registration_is_idempotent_and_conflicts_are_explicit(
    db_session: Session,
) -> None:
    registration = register_source(db_session)
    duplicate = SourceRegistry().register(db_session, registration)
    assert duplicate.duplicate is True
    assert duplicate.source.policy_notes == "Fixture use only"
    assert duplicate.source.license_name == "Test License"

    conflict = registration.model_copy(update={"kind": "publisher"})
    with pytest.raises(SourceConflictError):
        SourceRegistry().register(db_session, conflict)


def test_new_duplicate_and_changed_raw_evidence(db_session: Session, tmp_path: Path) -> None:
    registration = register_source(db_session)
    source_id = source_id_for(db_session, registration)
    store = LocalObjectStore(tmp_path / "objects", max_bytes=1024)
    intake = RawEvidenceIntake(store, max_bytes=1024)

    first = intake.ingest(db_session, make_submission(source_id))
    assert first.duplicate is False
    assert first.raw_evidence.original_filename == "_CON"
    assert first.raw_evidence.storage_key is not None
    assert first.raw_evidence.storage_key.startswith(f"raw/{source_id}/")
    assert first.raw_evidence.storage_key.endswith(".json")
    assert store.get(first.raw_evidence.storage_key) == b'{"fixture":1}'
    assert first.raw_evidence.content_size_bytes == 13
    assert first.raw_evidence.processing_state is ProcessingState.PENDING

    stored_path = (tmp_path / "objects").joinpath(*first.raw_evidence.storage_key.split("/"))
    stored_path.unlink()
    assert not store.exists(first.raw_evidence.storage_key)
    duplicate = intake.ingest(db_session, make_submission(source_id))
    assert duplicate.duplicate is True
    assert duplicate.raw_evidence.id == first.raw_evidence.id
    assert store.get(first.raw_evidence.storage_key) == b'{"fixture":1}'
    assert db_session.scalar(select(func.count()).select_from(RawEvidence)) == 1

    changed = intake.ingest(db_session, make_submission(source_id, b'{"fixture":2}'))
    assert changed.duplicate is False
    assert changed.raw_evidence.id != first.raw_evidence.id
    assert changed.raw_evidence.content_sha256 != first.raw_evidence.content_sha256
    assert db_session.scalar(select(func.count()).select_from(RawEvidence)) == 2


def test_same_content_from_different_sources_keeps_provenance(
    db_session: Session, tmp_path: Path
) -> None:
    first_registration = register_source(db_session, "-one")
    second_registration = register_source(db_session, "-two")
    first_source = source_id_for(db_session, first_registration)
    second_source = source_id_for(db_session, second_registration)
    intake = RawEvidenceIntake(LocalObjectStore(tmp_path / "objects", 1024), 1024)

    first = intake.ingest(db_session, make_submission(first_source, b"same"))
    second = intake.ingest(db_session, make_submission(second_source, b"same"))

    assert first.raw_evidence.id != second.raw_evidence.id
    assert first.raw_evidence.content_sha256 == second.raw_evidence.content_sha256
    assert first.raw_evidence.storage_key != second.raw_evidence.storage_key


def test_content_limits_unknown_sources_and_metadata_validation(
    db_session: Session, tmp_path: Path
) -> None:
    registration = register_source(db_session)
    source_id = source_id_for(db_session, registration)
    intake = RawEvidenceIntake(LocalObjectStore(tmp_path / "objects", 8), 8)

    with pytest.raises(ContentTooLargeError):
        intake.ingest(db_session, make_submission(source_id, b"123456789"))
    with pytest.raises(SourceNotRegisteredError):
        intake.ingest(db_session, make_submission(uuid4(), b"ok"))
    valid = {
        "source_id": source_id,
        "content": b"ok",
        "source_locator": "https://example.test/source",
        "fetched_at": datetime(2026, 1, 1, tzinfo=UTC),
        "mime_type": "text/plain",
        "metadata": {"valid": True},
    }
    invalid_fields = [
        {"fetched_at": datetime(2026, 1, 1)},
        {"mime_type": "text/plain; charset=utf-8"},
        {"metadata": {"invalid": {"set"}}},
        {"source_locator": "https://example.test/\x00unsafe"},
    ]
    for invalid in invalid_fields:
        with pytest.raises(ValidationError):
            RawEvidenceSubmission.model_validate(valid | invalid)


def test_processing_state_supports_failure_and_replay(db_session: Session, tmp_path: Path) -> None:
    registration = register_source(db_session)
    source_id = source_id_for(db_session, registration)
    intake = RawEvidenceIntake(LocalObjectStore(tmp_path / "objects", 1024), 1024)
    raw = intake.ingest(db_session, make_submission(source_id)).raw_evidence

    intake.mark_processing(raw)
    assert raw.processing_attempts == 1
    intake.mark_failed(raw, "Parser rejected fixture")
    assert raw.processing_state is ProcessingState.FAILED
    assert raw.last_processed_at is not None
    intake.request_reprocessing(raw)
    intake.mark_processing(raw)
    intake.mark_succeeded(raw)
    assert raw.processing_state is ProcessingState.SUCCEEDED
    assert raw.processing_attempts == 2
    assert raw.processing_error is None
    with pytest.raises(InvalidProcessingTransitionError):
        intake.mark_succeeded(raw)


def test_local_object_store_rejects_unsafe_keys_collisions_and_oversize(
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(tmp_path / "objects", max_bytes=16)
    with pytest.raises(UnsafeObjectKeyError):
        store.put_if_absent("../outside", b"data")
    with pytest.raises(UnsafeObjectKeyError):
        store.put_if_absent(r"raw\unsafe.bin", b"data")
    with pytest.raises(StoredObjectTooLargeError):
        store.put_if_absent("raw/large.bin", b"x" * 17)

    reference = store.put_if_absent("raw/safe.bin", b"do-not-execute")
    assert reference.uri.startswith("file:")
    assert store.get(reference.key) == b"do-not-execute"
    with pytest.raises(ObjectCollisionError):
        store.put_if_absent(reference.key, b"different")
