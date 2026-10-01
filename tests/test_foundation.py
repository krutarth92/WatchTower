import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError, TimeoutError

from watchtower.core.config import Settings
from watchtower.core.logging import JsonFormatter
from watchtower.db.session import build_engine
from watchtower.main import create_app


def test_settings_use_environment_and_hide_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "WATCHTOWER_DATABASE_URL", "postgresql+psycopg://user:secret@localhost/watchtower"
    )
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert "secret" not in repr(settings)
    assert settings.database_url.get_secret_value().endswith("/watchtower")


def test_settings_accept_staging_environment() -> None:
    settings = Settings(environment="staging")  # pyright: ignore[reportCallIssue]

    assert settings.environment == "staging"


@pytest.mark.parametrize("url", ["sqlite:///local.db", "broken", "postgresql://host/db"])
def test_settings_reject_unsupported_database(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=SecretStr(url))


def test_health_and_readiness_recover_without_restarting() -> None:
    settings = Settings(database_url=SecretStr("postgresql+psycopg://user:secret@localhost/db"))
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    with patch("watchtower.main.build_engine", return_value=engine):
        with TestClient(create_app(settings)) as client:
            assert client.get("/health").json() == {"status": "ok"}
            engine.connect.assert_not_called()
            assert client.get("/ready").status_code == 200
            assert str(connection.execute.call_args.args[0]) == "SELECT 1"
            engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("secret"))
            response = client.get("/ready")
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
            assert client.get("/health").status_code == 200
            engine.connect.side_effect = TimeoutError("pool exhausted")
            assert client.get("/ready").status_code == 503
            engine.connect.side_effect = None
            assert client.get("/ready").json() == {"status": "ready"}
        engine.dispose.assert_called_once()


def test_json_logs_omit_exception_details() -> None:
    record = logging.LogRecord(
        "watchtower",
        logging.WARNING,
        __file__,
        1,
        "database_not_ready",
        (),
        (RuntimeError, RuntimeError("password=secret"), None),
    )
    output = JsonFormatter().format(record)
    assert json.loads(output)["error_type"] == "RuntimeError"
    assert "secret" not in output


def test_json_logs_redact_nested_sensitive_fields() -> None:
    record = logging.LogRecord(
        "watchtower",
        logging.INFO,
        __file__,
        1,
        "security_event",
        (),
        None,
    )
    record.fields = {
        "operator_token": "must-not-appear",
        "nested": {
            "database_url": "postgresql://user:password@host/db",
            "safe": "retained",
        },
        "authorization": ["Bearer must-not-appear"],
    }

    parsed = json.loads(JsonFormatter().format(record))

    assert parsed["fields"] == {
        "operator_token": "[REDACTED]",
        "nested": {"database_url": "[REDACTED]", "safe": "retained"},
        "authorization": "[REDACTED]",
    }
    assert "must-not-appear" not in json.dumps(parsed)


def test_engine_pool_capacity_is_bounded_and_configurable() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://user:secret@localhost/watchtower"),
        db_pool_size=12,
        db_max_overflow=8,
        db_pool_recycle_seconds=900,
    )
    with patch("watchtower.db.session.create_engine") as create_engine:
        build_engine(settings)

    options = create_engine.call_args.kwargs
    assert options["pool_size"] == 12
    assert options["max_overflow"] == 8
    assert options["pool_recycle"] == 900
    assert options["pool_use_lifo"] is True


def test_settings_reject_unsafe_ingestion_timeout_relationships() -> None:
    with pytest.raises(ValidationError, match="must leave five seconds"):
        Settings(  # pyright: ignore[reportCallIssue]
            ingestion_job_lease_seconds=30,
            ingestion_job_timeout_seconds=26,
        )
    with pytest.raises(ValidationError, match="cannot exceed"):
        Settings(  # pyright: ignore[reportCallIssue]
            ingestion_fetch_timeout_seconds=5,
            ingestion_fetch_connect_timeout_seconds=6,
        )


def test_http_security_headers_and_request_body_limit() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://user:secret@localhost/watchtower"),
        max_request_body_bytes=1024,
    )
    engine = MagicMock()
    with patch("watchtower.main.build_engine", return_value=engine):
        with TestClient(create_app(settings)) as client:
            health = client.get("/health")
            oversized = client.post(
                "/api/v1/operations/ingestion/jobs",
                content=b"x" * 1025,
                headers={"X-Request-ID": "oversized-request"},
            )
            chunked = client.post(
                "/api/v1/operations/ingestion/jobs",
                content=(chunk for chunk in (b"x" * 600, b"y" * 600)),
                headers={"X-Request-ID": "oversized-chunked"},
            )

    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["Referrer-Policy"] == "no-referrer"
    assert oversized.status_code == 413
    assert oversized.headers["X-Request-ID"] == "oversized-request"
    assert oversized.headers["Cache-Control"] == "no-store"
    assert oversized.json() == {
        "error": {
            "code": "request_too_large",
            "message": "Request body exceeds 1024 bytes.",
            "request_id": "oversized-request",
            "details": [],
        }
    }
    assert chunked.status_code == 413
    assert chunked.json()["error"]["request_id"] == "oversized-chunked"
