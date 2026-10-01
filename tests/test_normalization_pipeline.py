import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import (
    NormalizationLedger,
    NormalizationStage,
    NormalizationStatus,
    Observation,
    ProcessingState,
    RawEvidence,
)
from watchtower.ingestion.mitre_attack import ConnectorRunStatus, MitreAttackConnector
from watchtower.ingestion.mitre_attack_normalization import (
    MitreAttackObservationNormalizer,
    MitreAttackRecordParser,
)
from watchtower.ingestion.normalization import (
    CanonicalObservation,
    DeduplicationAction,
    DeduplicationDecision,
    NormalizationPipeline,
    NormalizationRecord,
    ObservationRepository,
)
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.storage.local import LocalObjectStore

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mitre_attack" / "enterprise-attack-small.json"
FETCHED_AT = datetime(2026, 9, 28, 8, 0, tzinfo=UTC)


def make_pipeline(
    session: Session, repository: ObservationRepository | None = None
) -> NormalizationPipeline:
    return NormalizationPipeline(
        session,
        MitreAttackRecordParser(),
        MitreAttackObservationNormalizer(),
        repository,
    )


def make_connector(
    session: Session,
    tmp_path: Path,
    repository: ObservationRepository | None = None,
) -> MitreAttackConnector:
    store = LocalObjectStore(tmp_path / "objects", max_bytes=1024 * 1024)
    intake = RawEvidenceIntake(store, max_bytes=1024 * 1024)
    return MitreAttackConnector(intake, make_pipeline(session, repository))


def make_bundle(*objects: dict) -> bytes:
    return json.dumps(
        {
            "type": "bundle",
            "id": "bundle--aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "objects": list(objects),
        },
        separators=(",", ":"),
    ).encode()


def intrusion_set(**overrides: object) -> dict:
    record = {
        "type": "intrusion-set",
        "spec_version": "2.1",
        "id": "intrusion-set--bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "created": "2026-08-01T00:00:00Z",
        "modified": "2026-08-05T05:30:00+05:30",
        "name": "Fixture Group",
        "description": "A deterministic fixture observation.",
        "first_seen": "2026-01-02T05:30:00+05:30",
        "last_seen": "2026-02-02T05:30:00+05:30",
        "aliases": ["Fixture Alias"],
        "external_references": [{"source_name": "mitre-attack", "external_id": "G0000"}],
    }
    return record | overrides


def test_connector_creates_observation_with_continuous_provenance(
    db_session: Session, tmp_path: Path
) -> None:
    connector = make_connector(db_session, tmp_path)

    result = connector.run_fixture(db_session, FIXTURE_PATH.read_bytes(), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.SUCCEEDED
    assert result.raw_evidence_id is not None
    observation = db_session.scalar(select(Observation))
    assert observation is not None
    assert observation.source_id == result.source_id
    assert observation.raw_evidence_id == result.raw_evidence_id
    assert observation.source_native_id == "intrusion-set--22222222-2222-4222-8222-222222222222"
    assert observation.title == "WATCHTOWER fixture group"
    assert observation.observed_at == datetime(2026, 8, 5, tzinfo=UTC)
    assert observation.observation_metadata["source"]["stix_type"] == "intrusion-set"

    ledgers = db_session.scalars(
        select(NormalizationLedger).order_by(NormalizationLedger.object_index)
    ).all()
    assert len(ledgers) == 2
    assert ledgers[0].status is NormalizationStatus.SUCCEEDED
    assert ledgers[0].observation_id == observation.id
    assert ledgers[0].source_id == observation.source_id
    assert ledgers[0].raw_evidence_id == observation.raw_evidence_id
    assert ledgers[1].status is NormalizationStatus.REJECTED
    assert ledgers[1].reason == "unsupported object type: attack-pattern"
    assert ledgers[1].observation_id is None


def test_malformed_supported_record_is_rejected_without_losing_raw(
    db_session: Session, tmp_path: Path
) -> None:
    content = make_bundle(intrusion_set(name=None))
    connector = make_connector(db_session, tmp_path)

    result = connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.FAILED
    assert result.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.FAILED
    assert db_session.scalar(select(func.count()).select_from(Observation)) == 0
    ledger = db_session.scalar(select(NormalizationLedger))
    assert ledger is not None
    assert ledger.status is NormalizationStatus.REJECTED
    assert ledger.stage is NormalizationStage.PARSE
    assert ledger.reason == "invalid ATT&CK intrusion-set fields: name"


def test_duplicate_source_record_creates_one_observation(
    db_session: Session, tmp_path: Path
) -> None:
    item = intrusion_set()
    connector = make_connector(db_session, tmp_path)

    result = connector.run_fixture(db_session, make_bundle(item, item), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.SUCCEEDED
    assert db_session.scalar(select(func.count()).select_from(Observation)) == 1
    statuses = db_session.scalars(
        select(NormalizationLedger.status).order_by(NormalizationLedger.object_index)
    ).all()
    assert statuses == [NormalizationStatus.SUCCEEDED, NormalizationStatus.DEDUPLICATED]


def test_missing_optional_fields_uses_deterministic_defaults(
    db_session: Session, tmp_path: Path
) -> None:
    item = intrusion_set()
    for field in ("description", "first_seen", "last_seen", "aliases", "external_references"):
        item.pop(field)
    connector = make_connector(db_session, tmp_path)

    result = connector.run_fixture(db_session, make_bundle(item), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.SUCCEEDED
    observation = db_session.scalar(select(Observation))
    assert observation is not None
    assert observation.summary == "Fixture Group"
    assert observation.first_seen is None
    assert observation.last_seen is None
    assert observation.observed_at == datetime(2026, 8, 5, tzinfo=UTC)
    assert observation.observation_metadata["source"]["aliases"] == []


def test_replay_is_deduplicated_and_increments_attempt_count(
    db_session: Session, tmp_path: Path
) -> None:
    content = make_bundle(intrusion_set())
    connector = make_connector(db_session, tmp_path)
    result = connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)
    assert result.raw_evidence_id is not None
    item = intrusion_set()
    replay = NormalizationRecord(
        source_id=result.source_id,
        raw_evidence_id=result.raw_evidence_id,
        source_native_id=str(item["id"]),
        object_type="intrusion-set",
        object_index=0,
        payload=item,
    )

    make_pipeline(db_session).emit(replay)

    assert db_session.scalar(select(func.count()).select_from(Observation)) == 1
    ledger = db_session.scalar(select(NormalizationLedger))
    assert ledger is not None
    assert ledger.status is NormalizationStatus.DEDUPLICATED
    assert ledger.attempts == 2
    assert ledger.reason == "canonical observation already exists"


class FailingObservationRepository:
    def deduplicate(
        self, session: Session, canonical: CanonicalObservation, fingerprint: str
    ) -> DeduplicationDecision:
        return DeduplicationDecision(DeduplicationAction.CREATE, None)

    def persist(
        self,
        session: Session,
        canonical: CanonicalObservation,
        fingerprint: str,
        decision: DeduplicationDecision,
    ) -> Observation:
        raise RuntimeError("fixture persistence failure")


def test_failed_persist_stage_records_state_and_preserves_raw(
    db_session: Session, tmp_path: Path
) -> None:
    connector = make_connector(db_session, tmp_path, FailingObservationRepository())

    result = connector.run_fixture(db_session, make_bundle(intrusion_set()), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.FAILED
    assert result.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.FAILED
    ledger = db_session.scalar(select(NormalizationLedger))
    assert ledger is not None
    assert ledger.status is NormalizationStatus.FAILED
    assert ledger.stage is NormalizationStage.PERSIST
    assert ledger.reason == "persist stage raised RuntimeError"
    assert db_session.scalar(select(func.count()).select_from(Observation)) == 0


def test_older_source_version_does_not_overwrite_newer_observation(
    db_session: Session, tmp_path: Path
) -> None:
    connector = make_connector(db_session, tmp_path)
    newest = intrusion_set(name="New name", modified="2026-08-06T00:00:00Z")
    first = connector.run_fixture(db_session, make_bundle(newest), fetched_at=FETCHED_AT)
    assert first.raw_evidence_id is not None
    older = intrusion_set(name="Old name", modified="2026-08-05T00:00:00Z")

    second = connector.run_fixture(db_session, make_bundle(older), fetched_at=FETCHED_AT)

    assert second.status is ConnectorRunStatus.SUCCEEDED
    observation = db_session.scalar(select(Observation))
    assert observation is not None
    assert observation.title == "New name"
    assert observation.raw_evidence_id == first.raw_evidence_id
    ledger = db_session.scalar(
        select(NormalizationLedger).where(
            NormalizationLedger.raw_evidence_id == second.raw_evidence_id
        )
    )
    assert ledger is not None
    assert ledger.status is NormalizationStatus.DEDUPLICATED
    assert ledger.reason == "existing observation has a newer source timestamp"


def test_equal_timestamp_conflict_is_rejected_deterministically(
    db_session: Session, tmp_path: Path
) -> None:
    connector = make_connector(db_session, tmp_path)
    original = intrusion_set(name="Original name")
    first = connector.run_fixture(db_session, make_bundle(original), fetched_at=FETCHED_AT)
    conflicting = intrusion_set(name="Conflicting name")

    second = connector.run_fixture(db_session, make_bundle(conflicting), fetched_at=FETCHED_AT)

    assert first.status is ConnectorRunStatus.SUCCEEDED
    assert second.status is ConnectorRunStatus.FAILED
    observation = db_session.scalar(select(Observation))
    assert observation is not None
    assert observation.title == "Original name"
    ledger = db_session.scalar(
        select(NormalizationLedger).where(
            NormalizationLedger.raw_evidence_id == second.raw_evidence_id
        )
    )
    assert ledger is not None
    assert ledger.status is NormalizationStatus.REJECTED
    assert ledger.stage is NormalizationStage.DEDUPLICATE
    assert ledger.reason == "conflicting canonical content has the same source timestamp"
