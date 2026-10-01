"""Correlation ID middleware for public API requests."""

import logging
import re
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
logger = logging.getLogger("watchtower.api.request")


async def add_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    supplied = request.headers.get(REQUEST_ID_HEADER)
    request_id = supplied if supplied and SAFE_REQUEST_ID.fullmatch(supplied) else str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/v1/operations/"):
        response.headers.setdefault("Cache-Control", "no-store")
    duration_ms = round((perf_counter() - started_at) * 1000, 3)
    slow_request = duration_ms >= request.app.state.settings.api_slow_request_ms
    logger.log(
        logging.WARNING if slow_request else logging.INFO,
        "slow_request" if slow_request else "request_completed",
        extra={
            "fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        },
    )
    return response
