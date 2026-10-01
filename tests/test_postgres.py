import os

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from watchtower.core.config import Settings
from watchtower.main import create_app


@pytest.mark.integration
def test_real_postgres_readiness() -> None:
    url = os.environ.get("WATCHTOWER_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set WATCHTOWER_TEST_DATABASE_URL to run the real PostgreSQL check")
    with TestClient(create_app(Settings(database_url=SecretStr(url)))) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}


def test_real_connection_failure_returns_unavailable() -> None:
    # Port zero cannot host PostgreSQL; this exercises the actual driver failure path.
    settings = Settings(
        database_url=SecretStr("postgresql+psycopg://test:test@127.0.0.1:0/unavailable"),
        db_connect_timeout=1,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
