"""Operator-only intelligence-source integration catalog and actions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.api.errors import OPERATOR_ERROR_RESPONSES, ApiError, ErrorResponse
from watchtower.api.operator_auth import require_operator
from watchtower.api.v1.ingestion import JobService, Queue, submit_approved_ingestion_job
from watchtower.api.v1.integration_schemas import (
    IntegrationCatalogResponse,
    IntegrationSyncRequest,
    enrichment_read,
    integration_read,
)
from watchtower.api.v1.job_schemas import (
    IngestionJobSubmission,
    IngestionJobSubmissionResponse,
    ingestion_job_read,
)
from watchtower.db.models import IngestionJob
from watchtower.db.session import get_session
from watchtower.integrations.catalog import (
    ENRICHMENT_ROADMAP,
    INTEGRATION_CATALOG,
    get_integration,
)

router = APIRouter(
    prefix="/api/v1/operations/integrations",
    tags=["operator integrations"],
    dependencies=[Depends(require_operator)],
    responses={**OPERATOR_ERROR_RESPONSES},
)
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get(
    "",
    response_model=IntegrationCatalogResponse,
    summary="Read the approved integration catalog and operational state",
)
def get_integrations(session: DatabaseSession) -> IntegrationCatalogResponse:
    data = []
    for definition in INTEGRATION_CATALOG:
        latest = None
        if definition.job_kind is not None:
            job = session.scalar(
                select(IngestionJob)
                .where(IngestionJob.job_kind == definition.job_kind)
                .order_by(IngestionJob.created_at.desc(), IngestionJob.id.desc())
                .limit(1)
            )
            latest = ingestion_job_read(job) if job is not None else None
        data.append(integration_read(definition, latest))
    return IntegrationCatalogResponse(
        data=data,
        enrichment_roadmap=[enrichment_read(item) for item in ENRICHMENT_ROADMAP],
    )


@router.post(
    "/{integration_key}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobSubmissionResponse,
    responses={
        **OPERATOR_ERROR_RESPONSES,
        404: {"model": ErrorResponse, "description": "Integration is unavailable"},
        429: {"model": ErrorResponse, "description": "Ingestion backlog is at capacity"},
    },
    summary="Submit a supported integration refresh",
)
def sync_integration(
    integration_key: str,
    payload: IntegrationSyncRequest,
    request: Request,
    session: DatabaseSession,
    service: JobService,
    queue: Queue,
) -> IngestionJobSubmissionResponse:
    definition = get_integration(integration_key)
    if (
        definition is None
        or not definition.can_sync
        or definition.job_kind is None
        or payload.integration_key != integration_key
        or payload.job_kind != definition.job_kind
    ):
        raise ApiError(404, "integration_not_available", "Integration is not available.")
    return submit_approved_ingestion_job(
        IngestionJobSubmission(
            job_kind=definition.job_kind,
            idempotency_key=payload.idempotency_key,
        ),
        request,
        session,
        service,
        queue,
    )
