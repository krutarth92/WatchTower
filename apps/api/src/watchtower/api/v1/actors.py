"""Read-only actor endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from watchtower.api.errors import ERROR_RESPONSES, ApiError
from watchtower.api.v1.schemas import (
    ActorResponse,
    ActorSearchResponse,
    AliasCollection,
    AliasResponse,
    AssociationCollection,
    AssociationResponse,
    CursorPage,
    ObservationPageResponse,
    ReferenceCollection,
    ReferenceResponse,
    TimelineEvent,
    TimelinePageResponse,
)
from watchtower.db.models import IntelligenceType
from watchtower.db.session import get_session
from watchtower.services.actor_read import SEARCH_LIMIT, ActorReadService, actor_read

router = APIRouter(prefix="/api/v1/actors", tags=["actors"], responses=ERROR_RESPONSES)
service = ActorReadService()
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get(
    "/search",
    response_model=ActorSearchResponse,
    summary="Search actors by canonical name or linked source alias",
)
def search_actors(
    session: DatabaseSession,
    q: Annotated[str, Query(min_length=2, max_length=100)],
) -> ActorSearchResponse:
    return ActorSearchResponse(data=service.search(session, q), limit=SEARCH_LIMIT)


@router.get(
    "/{actor_id}",
    response_model=ActorResponse,
    summary="Get an actor by stable ID",
)
def get_actor(actor_id: UUID, session: DatabaseSession) -> ActorResponse:
    return ActorResponse(data=actor_read(service.require_actor(session, actor_id)))


@router.get(
    "/{actor_id}/aliases",
    response_model=AliasResponse,
    summary="List source-preserved aliases for an actor",
)
def get_actor_aliases(actor_id: UUID, session: DatabaseSession) -> AliasResponse:
    aliases, truncated = service.aliases(session, actor_id)
    return AliasResponse(data=AliasCollection(items=aliases, truncated=truncated))


@router.get(
    "/{actor_id}/observations",
    response_model=ObservationPageResponse,
    summary="List evidence-backed actor observations",
)
def get_actor_observations(
    actor_id: UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    intelligence_type: IntelligenceType | None = None,
) -> ObservationPageResponse:
    _validate_dates(date_from, date_to)
    page = service.observations(
        session,
        actor_id,
        limit=limit,
        cursor=cursor,
        date_from=date_from,
        date_to=date_to,
        intelligence_type=intelligence_type,
    )
    return ObservationPageResponse(
        data=page.items,
        page=CursorPage(limit=limit, next_cursor=page.next_cursor),
    )


@router.get(
    "/{actor_id}/timeline",
    response_model=TimelinePageResponse,
    summary="Read an actor timeline with evidence and associations",
)
def get_actor_timeline(
    actor_id: UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    intelligence_type: IntelligenceType | None = None,
) -> TimelinePageResponse:
    _validate_dates(date_from, date_to)
    page = service.observations(
        session,
        actor_id,
        limit=limit,
        cursor=cursor,
        date_from=date_from,
        date_to=date_to,
        intelligence_type=intelligence_type,
    )
    return TimelinePageResponse(
        data=[TimelineEvent(**item.model_dump()) for item in page.items],
        page=CursorPage(limit=limit, next_cursor=page.next_cursor),
    )


@router.get(
    "/{actor_id}/associations",
    response_model=AssociationResponse,
    summary="List an actor's observed behaviors and techniques",
)
def get_actor_associations(actor_id: UUID, session: DatabaseSession) -> AssociationResponse:
    behaviors, behaviors_truncated, techniques, techniques_truncated = service.associations(
        session, actor_id
    )
    return AssociationResponse(
        data=AssociationCollection(
            behaviors=behaviors,
            techniques=techniques,
            behaviors_truncated=behaviors_truncated,
            techniques_truncated=techniques_truncated,
        )
    )


@router.get(
    "/{actor_id}/references",
    response_model=ReferenceResponse,
    summary="List source and evidence references for an actor",
)
def get_actor_references(actor_id: UUID, session: DatabaseSession) -> ReferenceResponse:
    sources, sources_truncated, evidence, evidence_truncated = service.references(session, actor_id)
    return ReferenceResponse(
        data=ReferenceCollection(
            sources=sources,
            evidence=evidence,
            sources_truncated=sources_truncated,
            evidence_truncated=evidence_truncated,
        )
    )


def _validate_dates(date_from: datetime | None, date_to: datetime | None) -> None:
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is not None and value.tzinfo is None:
            raise ApiError(
                422,
                "validation_error",
                f"{name} must include a UTC offset.",
            )
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApiError(
            422,
            "validation_error",
            "date_from must be earlier than or equal to date_to.",
        )
