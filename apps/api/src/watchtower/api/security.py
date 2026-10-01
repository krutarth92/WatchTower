"""Small application-level HTTP security boundaries."""

from typing import Any

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyTooLargeError(HTTPException):
    """The incoming HTTP body crossed the configured application boundary."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request body is too large.")


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        declared_length = self._content_length(scope)
        if declared_length is None or 0 <= declared_length <= self._max_bytes:
            received = 0

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > self._max_bytes:
                        raise RequestBodyTooLargeError
                return message

            try:
                await self._app(scope, limited_receive, send)
                return
            except RequestBodyTooLargeError:
                pass

        await self._reject(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    length = int(value)
                except ValueError:
                    return -1
                return length
        return None

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        state: dict[str, Any] = scope.get("state", {})
        request_id = str(state.get("request_id", "unavailable"))
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "request_too_large",
                    "message": f"Request body exceeds {self._max_bytes} bytes.",
                    "request_id": request_id,
                    "details": [],
                }
            },
        )
        await response(scope, receive, send)
