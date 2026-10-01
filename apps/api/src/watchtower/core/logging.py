import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

REDACTED = "[REDACTED]"
SENSITIVE_FIELD_NAMES = {
    "authorization",
    "cookie",
    "databaseurl",
    "password",
    "proxyauthorization",
    "redisurl",
    "secret",
    "setcookie",
    "token",
}


def _normalized_field_name(name: object) -> str:
    return "".join(character for character in str(name).lower() if character.isalnum())


def _redact_fields(value: Any, *, field_name: object | None = None) -> Any:
    if field_name is not None and any(
        sensitive in _normalized_field_name(field_name) for sensitive in SENSITIVE_FIELD_NAMES
    ):
        return REDACTED
    if isinstance(value, dict):
        return {key: _redact_fields(item, field_name=key) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_fields(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload["fields"] = _redact_fields(fields)
        # Exception messages may contain connection details; log only their class.
        if record.exc_info and record.exc_info[0]:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    logger = logging.getLogger("watchtower")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
