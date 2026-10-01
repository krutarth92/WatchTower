import gzip
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import ProcessingState, RawEvidence, Source
from watchtower.ingestion.mitre_attack import (
    ATTACK_URL,
    ConnectorRunStatus,
    MitreAttackConnector,
    MitreAttackFetcher,
    MitreAttackFetchError,
)
from watchtower.ingestion.normalization import NormalizationRecord
from watchtower.ingestion.raw_evidence import RawEvidenceIntake
from watchtower.storage.local import LocalObjectStore

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mitre_attack" / "enterprise-attack-small.json"
FETCHED_AT = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)


class RecordingEmitter:
    def __init__(self, fail_id: str | None = None) -> None:
        self.records: list[NormalizationRecord] = []
        self.fail_id = fail_id

    def emit(self, record: NormalizationRecord) -> None:
        if record.source_native_id == self.fail_id:
            raise RuntimeError("fixture emitter failure")
        self.records.append(record)


def build_connector(
    tmp_path: Path, emitter: RecordingEmitter
) -> tuple[MitreAttackConnector, RawEvidenceIntake, LocalObjectStore]:
    store = LocalObjectStore(tmp_path / "objects", max_bytes=1024 * 1024)
    intake = RawEvidenceIntake(store, max_bytes=1024 * 1024)
    return MitreAttackConnector(intake, emitter), intake, store


def test_successful_fixture_load_preserves_raw_provenance(
    db_session: Session, tmp_path: Path
) -> None:
    content = FIXTURE_PATH.read_bytes()
    emitter = RecordingEmitter()
    connector, _, store = build_connector(tmp_path, emitter)

    result = connector.run_fixture(
        db_session,
        content,
        fetched_at=FETCHED_AT,
        etag='"fixture-etag"',
        last_modified="Wed, 05 Aug 2026 00:00:00 GMT",
    )

    assert result.status is ConnectorRunStatus.SUCCEEDED
    assert result.metrics.objects_seen == 2
    assert result.metrics.objects_emitted == 2
    assert result.metrics.objects_failed == 0
    assert result.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.SUCCEEDED
    assert raw.source_native_id == "bundle--11111111-1111-4111-8111-111111111111"
    assert raw.source_locator == ATTACK_URL
    assert raw.evidence_metadata["attack_version"] == "19.2"
    assert raw.evidence_metadata["etag"] == '"fixture-etag"'
    assert raw.storage_key is not None
    assert store.get(raw.storage_key) == content
    assert {record.raw_evidence_id for record in emitter.records} == {raw.id}
    assert {record.source_id for record in emitter.records} == {result.source_id}

    source = db_session.get(Source, result.source_id)
    assert source is not None
    assert source.license_name == "MITRE ATT&CK License"
    assert "permission of The MITRE Corporation" in (source.policy_notes or "")


def test_malformed_payload_is_retained_and_marked_failed(
    db_session: Session, tmp_path: Path
) -> None:
    content = b'{"type":"bundle", invalid'
    connector, _, store = build_connector(tmp_path, RecordingEmitter())

    result = connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.FAILED
    assert result.metrics.objects_failed == 1
    assert result.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.FAILED
    assert raw.processing_error == "Payload is not valid UTF-8 JSON"
    assert raw.storage_key is not None
    assert store.get(raw.storage_key) == content


def test_duplicate_succeeded_bundle_is_skipped(db_session: Session, tmp_path: Path) -> None:
    content = FIXTURE_PATH.read_bytes()
    emitter = RecordingEmitter()
    connector, _, _ = build_connector(tmp_path, emitter)

    first = connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)
    second = connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)

    assert first.status is ConnectorRunStatus.SUCCEEDED
    assert second.status is ConnectorRunStatus.SKIPPED
    assert second.duplicate is True
    assert second.raw_evidence_id == first.raw_evidence_id
    assert len(emitter.records) == 2
    assert db_session.scalar(select(func.count()).select_from(RawEvidence)) == 1


def test_partial_emitter_failure_marks_run_failed_and_keeps_other_records(
    db_session: Session, tmp_path: Path
) -> None:
    failing_id = "attack-pattern--33333333-3333-4333-8333-333333333333"
    emitter = RecordingEmitter(fail_id=failing_id)
    connector, _, _ = build_connector(tmp_path, emitter)

    result = connector.run_fixture(db_session, FIXTURE_PATH.read_bytes(), fetched_at=FETCHED_AT)

    assert result.status is ConnectorRunStatus.FAILED
    assert result.metrics.objects_seen == 2
    assert result.metrics.objects_emitted == 1
    assert result.metrics.objects_failed == 1
    assert result.issues[0].source_native_id == failing_id
    assert result.issues[0].detail == "Normalization emitter raised RuntimeError"
    assert result.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, result.raw_evidence_id)
    assert raw is not None
    assert raw.processing_state is ProcessingState.FAILED


def test_interrupted_duplicate_is_recovered_and_replayed(
    db_session: Session, tmp_path: Path
) -> None:
    content = FIXTURE_PATH.read_bytes()
    first_emitter = RecordingEmitter(fail_id="attack-pattern--33333333-3333-4333-8333-333333333333")
    first_connector, intake, store = build_connector(tmp_path, first_emitter)
    first = first_connector.run_fixture(db_session, content, fetched_at=FETCHED_AT)
    assert first.raw_evidence_id is not None
    raw = db_session.get(RawEvidence, first.raw_evidence_id)
    assert raw is not None
    intake.request_reprocessing(raw)
    intake.mark_processing(raw)
    assert raw.processing_state is ProcessingState.PROCESSING

    replay_emitter = RecordingEmitter()
    replay = MitreAttackConnector(
        RawEvidenceIntake(store, max_bytes=1024 * 1024), replay_emitter
    ).run_fixture(db_session, content, fetched_at=FETCHED_AT)

    assert replay.status is ConnectorRunStatus.SUCCEEDED
    assert replay.duplicate is True
    assert replay.raw_evidence_id == first.raw_evidence_id
    assert len(replay_emitter.records) == 2
    assert raw.processing_state is ProcessingState.SUCCEEDED
    assert raw.processing_attempts == 3


def test_source_unavailable_returns_metrics_without_raw_evidence(
    db_session: Session, tmp_path: Path
) -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("fixture offline", request=request)

    connector, _, _ = build_connector(tmp_path, RecordingEmitter())
    fetcher = MitreAttackFetcher(1024, transport=httpx.MockTransport(unavailable))

    result = connector.run_live(db_session, fetcher)

    assert result.status is ConnectorRunStatus.SOURCE_UNAVAILABLE
    assert result.raw_evidence_id is None
    assert result.metrics.bytes_retrieved == 0
    assert result.issues[0].error_type == "MitreAttackFetchError"
    assert db_session.scalar(select(func.count()).select_from(RawEvidence)) == 0


def test_fetcher_rejects_redirect_media_type_and_oversized_response() -> None:
    responses = [
        httpx.Response(302, headers={"location": "https://example.test/other"}),
        httpx.Response(200, headers={"content-type": "text/html"}, content=b"no"),
        httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "9"},
            content=b"123456789",
        ),
        httpx.Response(
            200,
            headers={"content-type": "application/json", "content-encoding": "gzip"},
            content=gzip.compress(b"compressed-content-is-not-accepted"),
        ),
    ]
    for response in responses:
        fetcher = MitreAttackFetcher(
            8,
            transport=httpx.MockTransport(lambda _request, item=response: item),
        )
        try:
            fetcher.fetch()
        except MitreAttackFetchError:
            pass
        else:
            raise AssertionError("unsafe response should be rejected")


def test_fetcher_requests_identity_encoding_without_environment_proxy() -> None:
    captured_request: httpx.Request | None = None

    def response(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b'{"type":"bundle","id":"bundle--00000000-0000-4000-8000-000000000000","objects":[]}',
        )

    with patch("watchtower.ingestion.mitre_attack.httpx.Client", wraps=httpx.Client) as client:
        result = MitreAttackFetcher(1024, transport=httpx.MockTransport(response)).fetch()

    assert result.content.startswith(b'{"type":"bundle"')
    assert captured_request is not None
    assert captured_request.headers["accept-encoding"] == "identity"
    assert client.call_args.kwargs["trust_env"] is False
