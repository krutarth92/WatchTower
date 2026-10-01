"""Dramatiq worker module: ``dramatiq watchtower.workers.tasks``."""

from uuid import UUID

import dramatiq
from dramatiq import Middleware
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy.orm import sessionmaker

from watchtower.core.config import Settings
from watchtower.db.session import build_engine
from watchtower.ingestion.job_runner import IngestionJobRunner
from watchtower.ingestion.jobs import IngestionJobService
from watchtower.workers.processor import ApprovedIngestionProcessor
from watchtower.workers.queue import (
    INGESTION_ACTOR,
    INGESTION_QUEUE,
    DramatiqJobQueue,
    recover_and_dispatch,
)

settings = Settings()  # pyright: ignore[reportCallIssue]
engine = build_engine(settings)
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
broker = RedisBroker(url=settings.redis_url.get_secret_value())
queue = DramatiqJobQueue(broker)
job_service = IngestionJobService(
    lease_seconds=settings.ingestion_job_lease_seconds,
    retry_base_seconds=settings.ingestion_job_retry_base_seconds,
    max_active_jobs=settings.ingestion_max_active_jobs,
    recovery_batch_size=settings.ingestion_recovery_batch_size,
)
runner = IngestionJobRunner(
    session_factory,
    job_service,
    ApprovedIngestionProcessor(settings),
    queue,
)
worker_time_limit_ms = settings.ingestion_job_timeout_seconds * 1000


class IngestionRecoveryMiddleware(Middleware):
    def after_process_boot(self, broker: dramatiq.Broker) -> None:
        recover_and_dispatch(session_factory, job_service, queue)


broker.add_middleware(IngestionRecoveryMiddleware())
dramatiq.set_broker(broker)


@dramatiq.actor(
    actor_name=INGESTION_ACTOR,
    queue_name=INGESTION_QUEUE,
    max_retries=0,
    time_limit=worker_time_limit_ms,
)
def process_ingestion_job(job_id: str) -> None:
    runner.run(UUID(job_id))
