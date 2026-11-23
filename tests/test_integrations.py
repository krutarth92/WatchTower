from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from watchtower.api.v1.ingestion import get_job_queue
from watchtower.core.config import Settings
from watchtower.db.session import get_session
from watchtower.main import create_app


@dataclass(slots=True)
class RecordingQueue:
    messages: list[tuple[UUID, int]] = field(default_factory=list)

    def enqueue(self, job_id: UUID, *, delay_ms: int = 0) -> None:
        self.messages.append((job_id, delay_ms))


def test_operator_catalog_is_truthful_and_does_not_disclose_secrets(
    db_session: Session,
) -> None:
    token = "task-35-operator-token-with-32-characters"
    app = create_app(
        Settings(operator_token=SecretStr(token))  # pyright: ignore[reportCallIssue]
    )

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/operations/integrations")
        response = client.get(
            "/api/v1/operations/integrations",
            headers={"X-WATCHTOWER-Operator-Token": token},
        )

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "operator_auth_failed"
    assert response.status_code == 200
    body = response.json()
    sources = {item["key"]: item for item in body["data"]}
    enrichments = {item["key"]: item for item in body["enrichment_roadmap"]}

    assert sources["mitre-attack"]["status"] == "available"
    assert sources["mitre-attack"]["configured"] is True
    assert sources["mitre-attack"]["can_sync"] is True
    for key in (
        "mitre-attack",
        "misp-galaxy",
        "cisa",
        "microsoft-threat-intelligence",
        "unit-42",
        "the-hacker-news",
    ):
        assert sources[key]["status"] == "available"
        assert sources[key]["configured"] is True
        assert sources[key]["can_sync"] is True
        assert sources[key]["job_kind"]
    assert sources["malpedia"]["required_settings"] == ["WATCHTOWER_MALPEDIA_API_KEY"]
    assert {
        "misp-galaxy",
        "cisa",
        "microsoft-threat-intelligence",
        "google-tag",
        "unit-42",
        "the-hacker-news",
    } <= set(sources)
    assert {"malpedia", "securelist", "eset-research", "selected-news"} <= set(sources)
    assert "twitter" not in sources
    assert "alienvault-otx" not in sources
    assert enrichments["attack-mapping"]["implemented"] is True
    assert enrichments["geoip-asn"]["implemented"] is False
    assert enrichments["external-reputation"]["wave"] == "later"
    assert token not in response.text
    assert "replace-with" not in response.text


def test_operator_can_submit_only_supported_replay_safe_sync(
    db_session: Session,
) -> None:
    token = "task-35-operator-token-with-32-characters"
    app = create_app(
        Settings(operator_token=SecretStr(token))  # pyright: ignore[reportCallIssue]
    )
    queue = RecordingQueue()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_job_queue] = lambda: queue
    key = f"task-35-{uuid4().hex}"
    payload = {
        "integration_key": "mitre-attack",
        "job_kind": "mitre_attack_refresh",
        "idempotency_key": key,
    }
    headers = {"X-WATCHTOWER-Operator-Token": token}

    with TestClient(app) as client:
        accepted = client.post(
            "/api/v1/operations/integrations/mitre-attack/sync",
            json=payload,
            headers=headers,
        )
        duplicate = client.post(
            "/api/v1/operations/integrations/mitre-attack/sync",
            json=payload,
            headers=headers,
        )
        additional = []
        for integration_key, job_kind in (
            ("misp-galaxy", "misp_galaxy_refresh"),
            ("cisa", "cisa_kev_refresh"),
            (
                "microsoft-threat-intelligence",
                "microsoft_threat_intelligence_refresh",
            ),
            ("unit-42", "unit_42_refresh"),
            ("the-hacker-news", "the_hacker_news_refresh"),
        ):
            additional.append(
                client.post(
                    f"/api/v1/operations/integrations/{integration_key}/sync",
                    json={
                        "integration_key": integration_key,
                        "job_kind": job_kind,
                        "idempotency_key": f"{key}-{integration_key}",
                    },
                    headers=headers,
                )
            )
        planned = client.post(
            "/api/v1/operations/integrations/google-tag/sync",
            json={**payload, "integration_key": "google-tag"},
            headers=headers,
        )
        catalog = client.get(
            "/api/v1/operations/integrations",
            headers=headers,
        )

    assert accepted.status_code == 202
    assert accepted.json()["data"]["duplicate"] is False
    assert duplicate.status_code == 202
    assert duplicate.json()["data"]["duplicate"] is True
    assert duplicate.json()["data"]["job"]["id"] == accepted.json()["data"]["job"]["id"]
    assert all(response.status_code == 202 for response in additional)
    assert planned.status_code == 404
    assert planned.json()["error"]["code"] == "integration_not_available"
    mitre = next(item for item in catalog.json()["data"] if item["key"] == "mitre-attack")
    assert mitre["latest_job"]["id"] == accepted.json()["data"]["job"]["id"]
    expected = [
        (UUID(accepted.json()["data"]["job"]["id"]), 0),
        (UUID(accepted.json()["data"]["job"]["id"]), 0),
    ]
    expected.extend((UUID(response.json()["data"]["job"]["id"]), 0) for response in additional)
    assert queue.messages == expected
