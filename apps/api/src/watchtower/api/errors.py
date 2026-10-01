"""Stable public API error responses."""

import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("watchtower.api")


class ErrorDetail(BaseModel):
    location: str
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=get_request_id(request),
            details=details or [],
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return error_response(request, exc.status_code, exc.code, exc.message, exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            location=".".join(str(part) for part in error["loc"]),
            message=str(error["msg"]),
            type=str(error["type"]),
        )
        for error in exc.errors()
    ]
    return error_response(
        request,
        422,
        "validation_error",
        "The request parameters are invalid.",
        details,
    )


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = str(exc.detail) if isinstance(exc.detail, str) else "The request could not be served."
    if exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 413:
        code = "request_too_large"
    else:
        code = "http_error"
    return error_response(request, exc.status_code, code, message)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_api_error",
        extra={
            "fields": {
                "request_id": get_request_id(request),
                "error_type": type(exc).__name__,
            }
        },
        exc_info=True,
    )
    return error_response(
        request,
        500,
        "internal_error",
        "The request could not be completed.",
    )


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    413: {"model": ErrorResponse, "description": "Request body is too large"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    422: {"model": ErrorResponse, "description": "Invalid request parameters"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}

OPERATOR_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    **ERROR_RESPONSES,
    401: {"model": ErrorResponse, "description": "Operator authentication failed"},
    503: {"model": ErrorResponse, "description": "Required service is unavailable"},
}
