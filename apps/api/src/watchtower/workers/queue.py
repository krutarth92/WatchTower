"""Dramatiq queue adapter with identifier-only messages."""

import logging
from uuid import UUID

from dramatiq import Broker, Message
from sqlalchemy.orm import Session, sessionmaker

from watchtower.ingestion.job_runner import JobQueue
from watchtower.ingestion.jobs import IngestionJobService

INGESTION_QUEUE = "ingestion"
INGESTION_ACTOR = "process_ingestion_job"
logger = logging.getLogger("watchtower.ingestion.dispatch")


class DramatiqJobQueue(JobQueue):
    def __init__(self, broker: Broker) -> None:
        self._broker = broker
        self._broker.declare_queue(INGESTION_QUEUE)

    def enqueue(self, job_id: UUID, *, delay_ms: int = 0) -> None:
        message = Message(
            queue_name=INGESTION_QUEUE,
            actor_name=INGESTION_ACTOR,
            args=(str(job_id),),
            kwargs={},
            options={},
        )
        self._broker.enqueue(message, delay=delay_ms or None)


def recover_and_dispatch(
    session_factory: sessionmaker[Session],
    service: IngestionJobService,
    queue: JobQueue,
) -> tuple[int, int]:
    with session_factory.begin() as session:
        recovered = service.recover_expired(session)
        due = service.due_job_ids(session)
    dispatched = 0
    for job_id in due:
        try:
            queue.enqueue(job_id)
            dispatched += 1
        except Exception as error:
            logger.warning(
                "ingestion_job_dispatch_failed",
                extra={
                    "fields": {
                        "job_id": str(job_id),
                        "error_type": type(error).__name__,
                    }
                },
            )
    logger.info(
        "ingestion_job_recovery_completed",
        extra={"fields": {"recovered": len(recovered), "dispatched": dispatched}},
    )
    return len(recovered), dispatched
