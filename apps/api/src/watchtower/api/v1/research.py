"""Operator-only evidence-grounded research endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from watchtower.api.errors import OPERATOR_ERROR_RESPONSES, ApiError
from watchtower.api.operator_auth import require_operator
from watchtower.db.session import get_session
from watchtower.research.contracts import ResearchAnswerResponse, ResearchQuestion
from watchtower.research.service import ResearchService

router = APIRouter(
    prefix="/api/v1/operations/research",
    tags=["operator research"],
    dependencies=[Depends(require_operator)],
    responses=OPERATOR_ERROR_RESPONSES,
)
DatabaseSession = Annotated[Session, Depends(get_session)]


def get_research_service(request: Request) -> ResearchService:
    service = request.app.state.research_service
    if not request.app.state.settings.rag_enabled or service is None:
        raise ApiError(
            503,
            "research_unavailable",
            "Evidence-grounded research is disabled until a provider is configured.",
        )
    return service


ResearchServiceDependency = Annotated[ResearchService, Depends(get_research_service)]


@router.post(
    "/answers",
    response_model=ResearchAnswerResponse,
    summary="Generate an evidence-grounded actor research answer",
)
def answer_research_question(
    question: ResearchQuestion,
    session: DatabaseSession,
    service: ResearchServiceDependency,
) -> ResearchAnswerResponse:
    return ResearchAnswerResponse(data=service.answer(session, question))
