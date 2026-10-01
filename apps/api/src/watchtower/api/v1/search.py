"""Read-only deterministic search endpoint."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from watchtower.api.errors import ERROR_RESPONSES, ApiError
from watchtower.api.v1.search_schemas import SearchEntityType, SearchResponse
from watchtower.db.models import IntelligenceType
from watchtower.db.session import get_session
from watchtower.services.search import SearchQueryError, SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"], responses=ERROR_RESPONSES)
service = SearchService()
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search approved intelligence entities with PostgreSQL full text",
)
def search(
    session: DatabaseSession,
    q: Annotated[str, Query(min_length=2, max_length=200)],
    entity_type: Annotated[list[SearchEntityType] | None, Query()] = None,
    source_id: UUID | None = None,
    intelligence_type: IntelligenceType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> SearchResponse:
    _validate_dates(date_from, date_to)
    try:
        clean_query, results = service.search(
            session,
            q,
            entity_types=set(entity_type) if entity_type else None,
            source_id=source_id,
            intelligence_type=intelligence_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    except SearchQueryError as error:
        raise ApiError(422, "validation_error", str(error)) from None
    return SearchResponse(query=clean_query, data=results, limit=limit)


def _validate_dates(date_from: datetime | None, date_to: datetime | None) -> None:
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ApiError(422, "validation_error", f"{name} must include a UTC offset.")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApiError(
            422,
            "validation_error",
            "date_from must be earlier than or equal to date_to.",
        )
