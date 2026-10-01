import logging
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["operations"])
logger = logging.getLogger("watchtower.readiness")


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse, responses={503: {"model": ReadyResponse}})
def ready(request: Request, response: Response) -> ReadyResponse:
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("database_not_ready", exc_info=True)
        response.status_code = 503
        return ReadyResponse(status="not_ready")
    return ReadyResponse(status="ready")
