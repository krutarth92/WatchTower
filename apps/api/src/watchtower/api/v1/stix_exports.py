"""Operator-only STIX 2.1 intelligence exports."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from watchtower.api.errors import OPERATOR_ERROR_RESPONSES, ApiError
from watchtower.api.operator_auth import require_operator
from watchtower.db.session import get_session
from watchtower.exports.stix import StixActorNotFoundError, StixExportService


class StixJSONResponse(JSONResponse):
    media_type = "application/stix+json"


router = APIRouter(
    prefix="/api/v1/operations/exports/stix",
    tags=["operator exports"],
    dependencies=[Depends(require_operator)],
    responses=OPERATOR_ERROR_RESPONSES,
)
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get(
    "/actors/{actor_id}",
    response_class=StixJSONResponse,
    response_model=None,
    summary="Export actor intelligence as STIX 2.1",
)
def export_actor(actor_id: UUID, session: DatabaseSession) -> dict[str, Any]:
    try:
        return StixExportService().export_actor(session, actor_id)
    except StixActorNotFoundError:
        raise ApiError(404, "actor_not_found", "Actor was not found.") from None
