"""Minimal operator authentication boundary for administrative routes."""

from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from watchtower.api.errors import ApiError

OPERATOR_HEADER = "X-WATCHTOWER-Operator-Token"
operator_header = APIKeyHeader(name=OPERATOR_HEADER, auto_error=False)


def require_operator(
    request: Request,
    provided: Annotated[str | None, Depends(operator_header)],
) -> None:
    configured = request.app.state.settings.operator_token
    if configured is None:
        raise ApiError(
            503,
            "operator_auth_unavailable",
            "Operator endpoints are not configured.",
        )
    expected = configured.get_secret_value()
    supplied = provided or ""
    if not compare_digest(supplied, expected):
        raise ApiError(401, "operator_auth_failed", "Operator authentication failed.")
