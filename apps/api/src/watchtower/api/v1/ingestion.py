"""Token-protected asynchronous ingestion job API."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from watchtower.api.errors import (
    OPERATOR_ERROR_RESPONSES,
    ApiError,
    ErrorResponse,
    get_request_id,
)
from watchtower.api.operator_auth import require_operator
from watchtower.api.v1.job_schemas import (
    IngestionJobStatusResponse,
    IngestionJobSubmission,
    IngestionJobSubmissionData,
    IngestionJobSubmissionResponse,
    IngestionQueueMetricsRead,
    IngestionQueueMetricsResponse,
    ingestion_job_read,
)
from watchtower.db.models import IngestionJobState
from watchtower.db.session import get_session
from watchtower.ingestion.job_runner import JobQueue
from watchtower.ingestion.jobs import (
    IngestionBackpressureError,
    IngestionJobNotFoundError,
    IngestionJobService,
)
from watchtower.ingestion.mitre_attack import register_mitre_attack_source

logger = logging.getLogger("watchtower.api.ingestion")
router = APIRouter(
    prefix="/api/v1/operations/ingestion/jobs",
    tags=["operator ingestion"],
    dependencies=[Depends(require_operator)],
    responses={
        **OPERATOR_ERROR_RESPONSES,
        429: {"model": ErrorResponse, "description": "Ingestion backlog is at capacity"},
    },
)
DatabaseSession = Annotated[Session, Depends(get_session)]


def get_job_service(request: Request) -> IngestionJobService:
    return request.app.state.ingestion_job_service


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.ingestion_job_queue


JobService = Annotated[IngestionJobService, Depends(get_job_service)]
Queue = Annotated[JobQueue, Depends(get_job_queue)]


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobSubmissionResponse,
    summary="Submit an approved ingestion job",
)
def submit_ingestion_job(
    submission: IngestionJobSubmission,
    request: Request,
    session: DatabaseSession,
    service: JobService,
    queue: Queue,
) -> IngestionJobSubmissionResponse:
    source = register_mitre_attack_source(session)
    try:
        result = service.submit(
            session,
            job_kind=submission.job_kind,
            source=source,
            correlation_id=get_request_id(request),
            idempotency_key=submission.idempotency_key,
            max_attempts=request.app.state.settings.ingestion_job_max_attempts,
        )
    except IngestionBackpressureError as error:
        raise ApiError(429, "ingestion_backpressure", str(error)) from None
    session.commit()
    if result.job.state is IngestionJobState.QUEUED:
        try:
            queue.enqueue(result.job.id)
        except Exception as error:
            logger.warning(
                "ingestion_job_initial_enqueue_failed",
                extra={
                    "fields": {
                        "job_id": str(result.job.id),
                        "source_id": str(result.job.source_id),
                        "correlation_id": result.job.correlation_id,
                        "error_type": type(error).__name__,
                    }
                },
            )
    return IngestionJobSubmissionResponse(
        data=IngestionJobSubmissionData(
            job=ingestion_job_read(result.job),
            duplicate=result.duplicate,
        )
    )


@router.get(
    "/metrics",
    response_model=IngestionQueueMetricsResponse,
    summary="Read durable ingestion queue depth and capacity",
)
def get_ingestion_queue_metrics(
    session: DatabaseSession,
    service: JobService,
) -> IngestionQueueMetricsResponse:
    metrics = service.queue_metrics(session)
    return IngestionQueueMetricsResponse(
        data=IngestionQueueMetricsRead(
            queued=metrics.queued,
            due=metrics.due,
            processing=metrics.processing,
            active=metrics.active,
            capacity=metrics.capacity,
            available=metrics.available,
            oldest_queued_at=metrics.oldest_queued_at,
        )
    )


@router.get(
    "/{job_id}",
    response_model=IngestionJobStatusResponse,
    summary="Read ingestion job status",
)
def get_ingestion_job(
    job_id: UUID,
    session: DatabaseSession,
    service: JobService,
) -> IngestionJobStatusResponse:
    try:
        job = service.get(session, job_id)
    except IngestionJobNotFoundError:
        raise ApiError(404, "ingestion_job_not_found", "Ingestion job was not found.") from None
    return IngestionJobStatusResponse(data=ingestion_job_read(job))
