"""Operator-only retrieval for validated technical artifacts."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from watchtower.api.errors import OPERATOR_ERROR_RESPONSES, ApiError
from watchtower.api.operator_auth import require_operator
from watchtower.artifacts.contracts import ArtifactCollectionResponse, ArtifactResponse
from watchtower.artifacts.service import ArtifactNotFoundError, ArtifactQueryError, ArtifactService
from watchtower.db.models import ArtifactType, ArtifactValidationStatus, Origin
from watchtower.db.session import get_session

router = APIRouter(
    prefix="/api/v1/operations/artifacts",
    tags=["operator artifacts"],
    dependencies=[Depends(require_operator)],
    responses=OPERATOR_ERROR_RESPONSES,
)
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("", response_model=ArtifactCollectionResponse, summary="Search technical artifacts")
def search_artifacts(
    session: DatabaseSession,
    q: Annotated[str | None, Query(min_length=2, max_length=200)] = None,
    artifact_type: ArtifactType | None = None,
    source_id: UUID | None = None,
    origin: Origin | None = None,
    validation_status: ArtifactValidationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ArtifactCollectionResponse:
    try:
        artifacts = ArtifactService().search(
            session,
            query=q,
            artifact_type=artifact_type,
            source_id=source_id,
            origin=origin,
            validation_status=validation_status,
            limit=limit,
        )
    except ArtifactQueryError as error:
        raise ApiError(422, "invalid_artifact_query", str(error)) from None
    return ArtifactCollectionResponse(data=artifacts, limit=limit)


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Retrieve a faithful technical artifact",
)
def get_artifact(artifact_id: UUID, session: DatabaseSession) -> ArtifactResponse:
    try:
        artifact = ArtifactService().get(session, artifact_id)
    except ArtifactNotFoundError:
        raise ApiError(404, "artifact_not_found", "Technical artifact was not found.") from None
    return ArtifactResponse(data=artifact)
