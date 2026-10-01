import json
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from watchtower.artifacts.contracts import ArtifactSubmission
from watchtower.artifacts.service import ArtifactError, ArtifactService
from watchtower.core.config import Settings
from watchtower.db.models import (
    ArtifactType,
    ArtifactValidationStatus,
    Origin,
    RawEvidence,
    Source,
)
from watchtower.db.session import get_session
from watchtower.main import create_app

pytestmark = pytest.mark.integration

VALID_STIX = json.dumps(
    {
        "type": "attack-pattern",
        "spec_version": "2.1",
        "id": "attack-pattern--00000000-0000-4000-8000-000000000011",
        "created": "2026-01-01T00:00:00.000Z",
        "modified": "2026-01-01T00:00:00.000Z",
        "name": "PowerShell execution pattern",
        "description": "A standard STIX object used by the artifact tests.",
    },
    indent=2,
)
VALID_STIX_BUNDLE = json.dumps(
    {
        "type": "bundle",
        "id": "bundle--00000000-0000-4000-8000-000000000014",
        "objects": [json.loads(VALID_STIX)],
    }
)
VALID_SIGMA = """title: Suspicious PowerShell Download
id: 00000000-0000-4000-8000-000000000012
status: test
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith: '\\powershell.exe'
    CommandLine|contains: 'DownloadString'
  condition: selection
level: medium
"""
VALID_ATTACK = json.dumps(
    {
        "type": "attack-pattern",
        "spec_version": "2.1",
        "id": "attack-pattern--00000000-0000-4000-8000-000000000013",
        "created": "2026-01-01T00:00:00.000Z",
        "modified": "2026-01-02T00:00:00.000Z",
        "name": "PowerShell",
        "x_mitre_version": "1.4",
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": "T1059.001",
                "url": "https://attack.mitre.org/techniques/T1059/001/",
            }
        ],
    }
)


def seed_provenance(db_session: Session) -> tuple[Source, RawEvidence]:
    source = Source(name=f"Task11 Source {uuid4()}", kind="dataset")
    raw = RawEvidence(
        source=source,
        storage_uri=f"local://task11/{uuid4()}",
        content_sha256="a" * 64,
        retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
        mime_type="application/json",
    )
    db_session.add_all([source, raw])
    db_session.flush()
    return source, raw


def submission(
    source: Source,
    raw: RawEvidence,
    artifact_type: ArtifactType,
    content: str,
) -> ArtifactSubmission:
    return ArtifactSubmission(
        source_id=source.id,
        raw_evidence_id=raw.id,
        artifact_type=artifact_type,
        origin=Origin.IMPORTED,
        content=content,
        metadata={"collection": "task-11", "handling": "local-only"},
    )


def test_valid_invalid_stix_are_stored_faithfully(db_session: Session) -> None:
    source, raw = seed_provenance(db_session)
    service = ArtifactService()
    valid = service.ingest(
        db_session, submission(source, raw, ArtifactType.STIX_2_1, VALID_STIX)
    ).artifact
    bundle = service.ingest(
        db_session, submission(source, raw, ArtifactType.STIX_2_1, VALID_STIX_BUNDLE)
    ).artifact
    invalid_content = '{"type":"indicator","spec_version":"2.1","pattern":"broken"}'
    invalid = service.ingest(
        db_session,
        submission(source, raw, ArtifactType.STIX_2_1, invalid_content),
    ).artifact

    assert valid.validation_status is ArtifactValidationStatus.VALID
    assert valid.canonical_id == "attack-pattern--00000000-0000-4000-8000-000000000011"
    assert valid.original_content == VALID_STIX
    assert valid.structured_content == json.loads(VALID_STIX)
    assert bundle.validation_status is ArtifactValidationStatus.VALID
    assert bundle.original_content == VALID_STIX_BUNDLE
    assert bundle.artifact_metadata["object_count"] == 1
    assert invalid.validation_status is ArtifactValidationStatus.INVALID
    assert invalid.validation_errors
    assert invalid.original_content == invalid_content
    assert invalid.raw_evidence_id == raw.id
    assert invalid.origin is Origin.IMPORTED


def test_valid_invalid_sigma_and_duplicate_handling(db_session: Session) -> None:
    source, raw = seed_provenance(db_session)
    service = ArtifactService()
    first = service.ingest(db_session, submission(source, raw, ArtifactType.SIGMA, VALID_SIGMA))
    duplicate = service.ingest(db_session, submission(source, raw, ArtifactType.SIGMA, VALID_SIGMA))
    invalid_content = """title: Broken rule
logsource:
  category: process_creation
detection:
  selection:
    Image: cmd.exe
"""
    invalid = service.ingest(
        db_session,
        submission(source, raw, ArtifactType.SIGMA, invalid_content),
    ).artifact

    assert first.artifact.validation_status is ArtifactValidationStatus.VALID
    assert first.artifact.original_content == VALID_SIGMA
    assert first.duplicate is False
    assert duplicate.duplicate is True
    assert duplicate.artifact.id == first.artifact.id
    assert invalid.validation_status is ArtifactValidationStatus.INVALID
    assert invalid.original_content == invalid_content


def test_attack_reference_retrieval_filters_and_provenance(db_session: Session) -> None:
    source, raw = seed_provenance(db_session)
    service = ArtifactService()
    artifact = service.ingest(
        db_session,
        submission(source, raw, ArtifactType.ATTACK_TECHNIQUE, VALID_ATTACK),
    ).artifact

    results = service.search(
        db_session,
        query="PowerShell",
        artifact_type=ArtifactType.ATTACK_TECHNIQUE,
        source_id=source.id,
        origin=Origin.IMPORTED,
        validation_status=ArtifactValidationStatus.VALID,
    )
    detail = service.get(db_session, artifact.id)

    assert [item.id for item in results] == [artifact.id]
    assert results[0].canonical_id == "T1059.001"
    assert results[0].source.id == source.id
    assert results[0].raw_evidence_id == raw.id
    assert results[0].metadata["handling"] == "local-only"
    assert detail.original_content == VALID_ATTACK
    assert detail.structured_content == json.loads(VALID_ATTACK)


def test_imported_artifact_requires_matching_raw_provenance(db_session: Session) -> None:
    source, _ = seed_provenance(db_session)
    with pytest.raises(ArtifactError, match="raw evidence"):
        ArtifactService().ingest(
            db_session,
            ArtifactSubmission(
                source_id=source.id,
                artifact_type=ArtifactType.STIX_2_1,
                origin=Origin.IMPORTED,
                content=VALID_STIX,
            ),
        )
    generated = (
        ArtifactService()
        .ingest(
            db_session,
            ArtifactSubmission(
                source_id=source.id,
                artifact_type=ArtifactType.STIX_2_1,
                origin=Origin.WATCHTOWER,
                content=VALID_STIX,
            ),
        )
        .artifact
    )
    assert generated.origin is Origin.WATCHTOWER
    assert generated.raw_evidence_id is None


def test_operator_artifact_api_and_search_index(db_session: Session) -> None:
    source, raw = seed_provenance(db_session)
    artifact = (
        ArtifactService()
        .ingest(db_session, submission(source, raw, ArtifactType.SIGMA, VALID_SIGMA))
        .artifact
    )
    settings = Settings(operator_token="task-11-test-operator-token-0001")  # pyright: ignore[reportCallIssue]
    token = settings.operator_token
    assert token is not None
    app = create_app(settings)

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    headers = {"X-WATCHTOWER-Operator-Token": token.get_secret_value()}
    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/operations/artifacts")
        listing = client.get(
            "/api/v1/operations/artifacts",
            params={"q": "PowerShell", "artifact_type": "sigma"},
            headers=headers,
        )
        detail = client.get(f"/api/v1/operations/artifacts/{artifact.id}", headers=headers)
        missing = client.get(f"/api/v1/operations/artifacts/{uuid4()}", headers=headers)

    assert unauthorized.status_code == 401
    assert listing.status_code == 200
    assert listing.json()["data"][0]["id"] == str(artifact.id)
    assert "original_content" not in listing.json()["data"][0]
    assert detail.status_code == 200
    assert detail.json()["data"]["original_content"] == VALID_SIGMA
    assert missing.status_code == 404
    indexes = set(
        db_session.scalars(
            text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() "
                "AND tablename = 'technical_artifacts'"
            )
        ).all()
    )
    assert "ix_technical_artifacts_search_document" in indexes
