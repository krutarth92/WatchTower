from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from dramatiq import Message
from dramatiq.brokers.stub import StubBroker
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from watchtower.api.v1.ingestion import get_job_queue
from watchtower.core.config import Settings
from watchtower.db.models import (
    IngestionJob,
    IngestionJobKind,
    IngestionJobState,
    Source,
)
from watchtower.db.session import get_session
from watchtower.ingestion.job_runner import (
    IngestionJobRunner,
    PermanentIngestionError,
    RetryableIngestionError,
    RunDisposition,
)
from watchtower.ingestion.jobs import (
    FailureDisposition,
    IngestionBackpressureError,
    IngestionJobService,
    JobClaim,
)
from watchtower.main import create_app
from watchtower.workers.queue import DramatiqJobQueue, recover_and_dispatch
from watchtower.workers.run import worker_arguments

pytestmark = pytest.mark.integration


@dataclass(slots=True)
class MutableClock:
    value: datetime = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, *, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


@dataclass(slots=True)
class RecordingQueue:
    messages: list[tuple[UUID, int]] = field(default_factory=list)
    fail: bool = False

    def enqueue(self, job_id: UUID, *, delay_ms: int = 0) -> None:
        if self.fail:
            raise ConnectionError("redis password=secret")
        self.messages.append((job_id, delay_ms))


@dataclass(slots=True)
class PlannedProcessor:
    outcomes: list[UUID | None | Exception]
    claims: list[JobClaim] = field(default_factory=list)

    def process(self, session: Session, claim: JobClaim) -> UUID | None:
        del session
        self.claims.append(claim)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass(slots=True)
class WritingProcessor:
    source_name: str

    def process(self, session: Session, claim: JobClaim) -> UUID | None:
        del claim
        session.add(Source(name=self.source_name, kind="dataset"))
        session.flush()
        return None


class LeaseLosingService(IngestionJobService):
    def mark_succeeded(
        self,
        session: Session,
        claim: JobClaim,
        raw_evidence_id: UUID | None,
    ) -> bool:
        del session, claim, raw_evidence_id
        return False


def make_factory(db_session: Session) -> sessionmaker[Session]:
    return sessionmaker(
        bind=db_session.connection(),
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


def make_source(db_session: Session) -> Source:
    source = Source(name=f"Job source {uuid4().hex}", kind="dataset")
    db_session.add(source)
    db_session.flush()
    return source


def make_service(
    clock: MutableClock,
    *,
    lease_seconds: int = 30,
    max_active_jobs: int = 1000,
) -> IngestionJobService:
    return IngestionJobService(
        lease_seconds=lease_seconds,
        retry_base_seconds=5,
        max_active_jobs=max_active_jobs,
        clock=clock,
    )


def submit_job(
    factory: sessionmaker[Session],
    service: IngestionJobService,
    source_id: UUID,
    *,
    key: str,
    max_attempts: int = 3,
) -> UUID:
    with factory.begin() as session:
        source = session.get(Source, source_id)
        assert source is not None
        result = service.submit(
            session,
            job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
            source=source,
            correlation_id=f"correlation-{key}",
            idempotency_key=key,
            max_attempts=max_attempts,
        )
        return result.job.id


def load_job(factory: sessionmaker[Session], job_id: UUID) -> IngestionJob:
    with factory() as session:
        job = session.get(IngestionJob, job_id)
        assert job is not None
        session.expunge(job)
        return job


def test_successful_job_and_duplicate_delivery_are_idempotent(db_session: Session) -> None:
    clock = MutableClock()
    service = make_service(clock)
    factory = make_factory(db_session)
    source = make_source(db_session)
    queue = RecordingQueue()
    processor = PlannedProcessor([None])
    job_id = submit_job(factory, service, source.id, key="success")
    runner = IngestionJobRunner(factory, service, processor, queue)

    assert runner.run(job_id) is RunDisposition.SUCCEEDED
    assert runner.run(job_id) is RunDisposition.SKIPPED
    job = load_job(factory, job_id)
    assert job.state is IngestionJobState.SUCCEEDED
    assert job.attempts == 1
    assert job.failure_reason is None
    assert job.finished_at == clock.value
    assert len(processor.claims) == 1


def test_retryable_failure_is_delayed_then_succeeds(db_session: Session) -> None:
    clock = MutableClock()
    service = make_service(clock)
    factory = make_factory(db_session)
    source = make_source(db_session)
    queue = RecordingQueue()
    processor = PlannedProcessor(
        [RetryableIngestionError("Approved source temporarily unavailable."), None]
    )
    job_id = submit_job(factory, service, source.id, key="retry", max_attempts=2)
    runner = IngestionJobRunner(factory, service, processor, queue)

    assert runner.run(job_id) is RunDisposition.RETRY_QUEUED
    retrying = load_job(factory, job_id)
    assert retrying.state is IngestionJobState.QUEUED
    assert retrying.attempts == 1
    assert retrying.failure_reason == "Approved source temporarily unavailable."
    assert queue.messages == [(job_id, 5000)]
    assert runner.run(job_id) is RunDisposition.SKIPPED

    clock.advance(seconds=5)
    assert runner.run(job_id) is RunDisposition.SUCCEEDED
    completed = load_job(factory, job_id)
    assert completed.state is IngestionJobState.SUCCEEDED
    assert completed.attempts == 2
    assert completed.failure_reason is None


def test_permanent_and_exhausted_failures_are_terminal(db_session: Session) -> None:
    clock = MutableClock()
    service = make_service(clock)
    factory = make_factory(db_session)
    source = make_source(db_session)
    queue = RecordingQueue()
    permanent_id = submit_job(factory, service, source.id, key="permanent")
    permanent = IngestionJobRunner(
        factory,
        service,
        PlannedProcessor([PermanentIngestionError("Invalid deterministic payload.")]),
        queue,
    )
    exhausted_id = submit_job(factory, service, source.id, key="exhausted", max_attempts=1)
    exhausted = IngestionJobRunner(
        factory,
        service,
        PlannedProcessor([RetryableIngestionError("Temporary failure.")]),
        queue,
    )

    assert permanent.run(permanent_id) is RunDisposition.FAILED
    assert exhausted.run(exhausted_id) is RunDisposition.FAILED
    assert load_job(factory, permanent_id).failure_reason == "Invalid deterministic payload."
    assert load_job(factory, exhausted_id).failure_reason == "Temporary failure."
    assert load_job(factory, permanent_id).state is IngestionJobState.FAILED
    assert load_job(factory, exhausted_id).state is IngestionJobState.FAILED
    assert queue.messages == []


def test_duplicate_submission_reuses_durable_job(db_session: Session) -> None:
    clock = MutableClock()
    service = make_service(clock)
    source = make_source(db_session)

    first = service.submit(
        db_session,
        job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
        source=source,
        correlation_id="first-correlation",
        idempotency_key="same-request",
        max_attempts=3,
    )
    second = service.submit(
        db_session,
        job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
        source=source,
        correlation_id="second-correlation",
        idempotency_key="same-request",
        max_attempts=3,
    )

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.job.id == first.job.id
    assert second.job.correlation_id == "first-correlation"


def test_queue_metrics_and_backpressure_bound_active_jobs(db_session: Session) -> None:
    clock = MutableClock()
    service = make_service(clock, max_active_jobs=1)
    source = make_source(db_session)

    first = service.submit(
        db_session,
        job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
        source=source,
        correlation_id="capacity-first",
        idempotency_key="capacity-first",
        max_attempts=3,
    )
    duplicate = service.submit(
        db_session,
        job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
        source=source,
        correlation_id="capacity-duplicate",
        idempotency_key="capacity-first",
        max_attempts=3,
    )
    metrics = service.queue_metrics(db_session)

    assert duplicate.duplicate is True
    assert duplicate.job.id == first.job.id
    assert metrics.queued == 1
    assert metrics.due == 1
    assert metrics.processing == 0
    assert metrics.active == 1
    assert metrics.capacity == 1
    assert metrics.available == 0
    assert metrics.oldest_queued_at is not None

    with pytest.raises(IngestionBackpressureError, match="1-job capacity"):
        service.submit(
            db_session,
            job_kind=IngestionJobKind.MITRE_ATTACK_REFRESH,
            source=source,
            correlation_id="capacity-second",
            idempotency_key="capacity-second",
            max_attempts=3,
        )


def test_worker_restart_recovers_expired_lease_and_rejects_stale_worker(
    db_session: Session,
) -> None:
    clock = MutableClock()
    service = make_service(clock, lease_seconds=30)
    factory = make_factory(db_session)
    source = make_source(db_session)
    queue = RecordingQueue()
    job_id = submit_job(factory, service, source.id, key="restart")
    with factory.begin() as session:
        stale_claim = service.claim(session, job_id)
    assert stale_claim is not None

    clock.advance(seconds=31)
    recovered, dispatched = recover_and_dispatch(factory, service, queue)
    assert (recovered, dispatched) == (1, 1)
    assert queue.messages == [(job_id, 0)]
    queued = load_job(factory, job_id)
    assert queued.state is IngestionJobState.QUEUED
    assert queued.failure_reason == "Worker lease expired; job queued for replay."

    with factory.begin() as session:
        stale_result = service.mark_succeeded(session, stale_claim, None)
    assert stale_result is False
    assert load_job(factory, job_id).state is IngestionJobState.QUEUED


def test_stale_completion_rolls_back_processor_changes(db_session: Session) -> None:
    clock = MutableClock()
    service = LeaseLosingService(
        lease_seconds=30,
        retry_base_seconds=5,
        clock=clock,
    )
    factory = make_factory(db_session)
    source = make_source(db_session)
    side_effect_name = f"Must roll back {uuid4().hex}"
    job_id = submit_job(factory, service, source.id, key="stale-rollback")
    runner = IngestionJobRunner(
        factory,
        service,
        WritingProcessor(side_effect_name),
        RecordingQueue(),
    )

    assert runner.run(job_id) is RunDisposition.STALE
    with factory() as session:
        assert session.query(Source).filter_by(name=side_effect_name).one_or_none() is None
    assert load_job(factory, job_id).state is IngestionJobState.PROCESSING


def test_unexpected_failure_does_not_store_or_log_secret_message(
    db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    clock = MutableClock()
    service = make_service(clock)
    factory = make_factory(db_session)
    source = make_source(db_session)
    queue = RecordingQueue(fail=True)
    processor = PlannedProcessor([RuntimeError("password=secret-token")])
    job_id = submit_job(factory, service, source.id, key="safe-failure")
    runner = IngestionJobRunner(factory, service, processor, queue)

    with caplog.at_level("INFO"):
        assert runner.run(job_id) is RunDisposition.RETRY_QUEUED

    job = load_job(factory, job_id)
    assert job.failure_reason == "Job processor raised RuntimeError."
    assert "secret-token" not in caplog.text
    assert "password=" not in caplog.text


def test_dramatiq_payload_contains_only_job_identifier() -> None:
    broker = StubBroker()
    queue = DramatiqJobQueue(broker)
    job_id = uuid4()

    queue.enqueue(job_id)

    encoded = broker.queues["ingestion"].get_nowait()
    message = Message.decode(encoded)
    assert message.actor_name == "process_ingestion_job"
    assert message.args == (str(job_id),)
    assert message.kwargs == {}
    assert len(encoded) < 1024


def test_operator_api_accepts_duplicate_reports_metrics_and_applies_backpressure(
    db_session: Session,
) -> None:
    token = "task-08-operator-token-with-32-characters"
    settings = Settings(  # pyright: ignore[reportCallIssue]
        operator_token=SecretStr(token),
        ingestion_max_active_jobs=1,
    )
    app = create_app(settings)
    queue = RecordingQueue()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_job_queue] = lambda: queue
    payload = {
        "job_kind": "mitre_attack_refresh",
        "idempotency_key": f"api-{uuid4().hex}",
    }
    with TestClient(app) as client:
        unauthorized = client.post("/api/v1/operations/ingestion/jobs", json=payload)
        accepted = client.post(
            "/api/v1/operations/ingestion/jobs",
            json=payload,
            headers={
                "X-WATCHTOWER-Operator-Token": token,
                "X-Request-ID": "task-08-api-test",
            },
        )
        duplicate = client.post(
            "/api/v1/operations/ingestion/jobs",
            json=payload,
            headers={"X-WATCHTOWER-Operator-Token": token},
        )
        rejected = client.post(
            "/api/v1/operations/ingestion/jobs",
            json={
                "job_kind": "mitre_attack_refresh",
                "idempotency_key": f"api-capacity-{uuid4().hex}",
            },
            headers={"X-WATCHTOWER-Operator-Token": token},
        )
        metrics_response = client.get(
            "/api/v1/operations/ingestion/jobs/metrics",
            headers={"X-WATCHTOWER-Operator-Token": token},
        )
        job_id = accepted.json()["data"]["job"]["id"]
        status_response = client.get(
            f"/api/v1/operations/ingestion/jobs/{job_id}",
            headers={"X-WATCHTOWER-Operator-Token": token},
        )
        missing = client.get(
            f"/api/v1/operations/ingestion/jobs/{uuid4()}",
            headers={"X-WATCHTOWER-Operator-Token": token},
        )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "operator_auth_failed"
    assert accepted.status_code == 202
    assert accepted.json()["data"]["duplicate"] is False
    assert accepted.json()["data"]["job"]["state"] == "queued"
    assert accepted.json()["data"]["job"]["correlation_id"] == "task-08-api-test"
    assert duplicate.status_code == 202
    assert duplicate.json()["data"]["duplicate"] is True
    assert duplicate.json()["data"]["job"]["id"] == job_id
    assert rejected.status_code == 429
    assert rejected.json()["error"]["code"] == "ingestion_backpressure"
    assert metrics_response.status_code == 200
    assert metrics_response.json()["data"] == {
        "queued": 1,
        "due": 1,
        "processing": 0,
        "active": 1,
        "capacity": 1,
        "available": 0,
        "oldest_queued_at": metrics_response.json()["data"]["oldest_queued_at"],
    }
    assert metrics_response.json()["data"]["oldest_queued_at"] is not None
    assert status_response.status_code == 200
    assert status_response.json()["data"]["id"] == job_id
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ingestion_job_not_found"
    assert queue.messages == [(UUID(job_id), 0), (UUID(job_id), 0)]


def test_worker_arguments_use_bounded_settings() -> None:
    settings = Settings(  # pyright: ignore[reportCallIssue]
        ingestion_worker_processes=3,
        ingestion_worker_threads=4,
    )

    assert worker_arguments(settings) == [
        "watchtower.workers.tasks",
        "--processes",
        "3",
        "--threads",
        "4",
    ]


def test_failure_disposition_values_are_stable() -> None:
    assert [item.value for item in FailureDisposition] == ["retry", "failed", "stale"]
