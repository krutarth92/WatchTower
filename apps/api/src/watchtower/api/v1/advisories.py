"""Public reads and operator writes for living intelligence advisories."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from watchtower.advisories.contracts import (
    AdvisoryCollectionResponse,
    AdvisoryCreate,
    AdvisoryResponse,
    AdvisoryUpdateCreate,
    PublishRequest,
    RevisionInput,
    UpdateCollectionResponse,
    UpdateRead,
)
from watchtower.advisories.service import (
    AdvisoryConflictError,
    AdvisoryNotFoundError,
    AdvisoryReferenceError,
    AdvisoryService,
)
from watchtower.api.errors import ERROR_RESPONSES, OPERATOR_ERROR_RESPONSES, ApiError
from watchtower.api.operator_auth import require_operator
from watchtower.db.session import get_session

public_router = APIRouter(
    prefix="/api/v1/advisories",
    tags=["advisories"],
    responses=ERROR_RESPONSES,
)
operator_router = APIRouter(
    prefix="/api/v1/operations/advisories",
    tags=["operator advisories"],
    dependencies=[Depends(require_operator)],
    responses=OPERATOR_ERROR_RESPONSES,
)
DatabaseSession = Annotated[Session, Depends(get_session)]


def _not_found() -> ApiError:
    return ApiError(404, "advisory_not_found", "Advisory or revision was not found.")


def _write_error(error: Exception) -> ApiError:
    if isinstance(error, AdvisoryNotFoundError):
        return _not_found()
    if isinstance(error, AdvisoryConflictError):
        return ApiError(409, "advisory_conflict", str(error))
    return ApiError(422, "invalid_advisory_reference", str(error))


@public_router.get("", response_model=AdvisoryCollectionResponse, summary="List advisories")
def list_advisories(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdvisoryCollectionResponse:
    return AdvisoryCollectionResponse(
        data=AdvisoryService().public_list(session, limit), limit=limit
    )


@public_router.get("/{slug}", response_model=AdvisoryResponse, summary="Read a published advisory")
def get_advisory(slug: str, session: DatabaseSession) -> AdvisoryResponse:
    try:
        data = AdvisoryService().public_get(session, slug)
    except AdvisoryNotFoundError:
        raise _not_found() from None
    return AdvisoryResponse(data=data)


@public_router.get(
    "/{slug}/revisions/{version}",
    response_model=AdvisoryResponse,
    summary="Read a published advisory revision",
)
def get_advisory_revision(slug: str, version: int, session: DatabaseSession) -> AdvisoryResponse:
    try:
        data = AdvisoryService().public_revision(session, slug, version)
    except AdvisoryNotFoundError:
        raise _not_found() from None
    return AdvisoryResponse(data=data)


@public_router.get(
    "/{slug}/updates",
    response_model=UpdateCollectionResponse,
    summary="Read machine-readable advisory updates",
)
def get_advisory_updates(
    slug: str,
    session: DatabaseSession,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UpdateCollectionResponse:
    try:
        data = AdvisoryService().public_updates(session, slug, after_sequence, limit)
    except AdvisoryNotFoundError:
        raise _not_found() from None
    return UpdateCollectionResponse(data=data, after_sequence=after_sequence, limit=limit)


@operator_router.post(
    "",
    response_model=AdvisoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft advisory",
)
def create_advisory(payload: AdvisoryCreate, session: DatabaseSession) -> AdvisoryResponse:
    try:
        data = AdvisoryService().create(session, payload)
        session.commit()
    except (AdvisoryConflictError, AdvisoryReferenceError, AdvisoryNotFoundError) as error:
        session.rollback()
        raise _write_error(error) from None
    return AdvisoryResponse(data=data)


@operator_router.post(
    "/{advisory_id}/revisions",
    response_model=AdvisoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append an immutable advisory revision",
)
def add_advisory_revision(
    advisory_id: UUID, payload: RevisionInput, session: DatabaseSession
) -> AdvisoryResponse:
    try:
        data = AdvisoryService().add_revision(session, advisory_id, payload)
        session.commit()
    except (AdvisoryConflictError, AdvisoryReferenceError, AdvisoryNotFoundError) as error:
        session.rollback()
        raise _write_error(error) from None
    return AdvisoryResponse(data=data)


@operator_router.post(
    "/{advisory_id}/revisions/{version}/publish",
    response_model=AdvisoryResponse,
    summary="Publish an advisory revision",
)
def publish_advisory_revision(
    advisory_id: UUID,
    version: int,
    payload: PublishRequest,
    session: DatabaseSession,
) -> AdvisoryResponse:
    try:
        data = AdvisoryService().publish(session, advisory_id, version, payload.published_by)
        session.commit()
    except (AdvisoryConflictError, AdvisoryReferenceError, AdvisoryNotFoundError) as error:
        session.rollback()
        raise _write_error(error) from None
    return AdvisoryResponse(data=data)


@operator_router.post(
    "/{advisory_id}/updates",
    response_model=UpdateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Append a timestamped advisory update",
)
def add_advisory_update(
    advisory_id: UUID,
    payload: AdvisoryUpdateCreate,
    session: DatabaseSession,
) -> UpdateRead:
    try:
        data = AdvisoryService().add_update(session, advisory_id, payload)
        session.commit()
    except (AdvisoryConflictError, AdvisoryReferenceError, AdvisoryNotFoundError) as error:
        session.rollback()
        raise _write_error(error) from None
    return data
