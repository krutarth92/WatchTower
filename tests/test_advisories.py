from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import (
    Actor,
    Campaign,
    Evidence,
    IntelligenceType,
    Origin,
    Source,
    Technique,
)
from watchtower.db.session import get_session
from watchtower.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def advisory_api(db_session: Session) -> Iterator[tuple[TestClient, dict[str, object]]]:
    token = uuid4().hex
    source = Source(name=f"Advisory source {token}", kind="report")
    actor = Actor(
        canonical_name=f"Advisory Actor {token[:6]}",
        normalized_name=f"advisory-actor-{token}",
    )
    campaign = Campaign(
        source=source,
        name=f"Advisory Campaign {token[:6]}",
        normalized_name=f"advisory-campaign-{token}",
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    technique = Technique(
        source=source,
        external_id=f"T-{token[:8]}",
        name="Fixture technique",
    )
    evidence = Evidence(
        source=source,
        citation=f"Report {token} section 2",
        excerpt="The report documents the observed behavior.",
        origin=Origin.IMPORTED,
    )
    db_session.add_all([source, actor, campaign, technique, evidence])
    db_session.flush()

    operator_token = f"task-17-operator-{token}"
    app = create_app(Settings(operator_token=operator_token))  # pyright: ignore[reportCallIssue]

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield (
            client,
            {
                "slug": f"living-advisory-{token}",
                "headers": {"X-WATCHTOWER-Operator-Token": operator_token},
                "actor_id": actor.id,
                "campaign_id": campaign.id,
                "technique_id": technique.id,
                "evidence_id": evidence.id,
            },
        )


def _revision_payload(fixture: dict[str, object], title: str) -> dict[str, object]:
    return {
        "title": title,
        "summary": f"{title} summary",
        "created_by": "analyst@example.test",
        "sections": [
            {
                "section_type": "what_happened",
                "intelligence_type": "observed",
                "content": f"{title} observed facts",
            },
            {
                "section_type": "watchtower_assessment",
                "intelligence_type": "assessed",
                "content": f"{title} analyst assessment",
            },
        ],
        "evidence_ids": [str(fixture["evidence_id"])],
        "actor_ids": [str(fixture["actor_id"])],
        "campaign_ids": [str(fixture["campaign_id"])],
        "technique_ids": [str(fixture["technique_id"])],
    }


def test_living_advisory_history_links_updates_and_public_reads(
    advisory_api: tuple[TestClient, dict[str, object]],
) -> None:
    client, fixture = advisory_api
    create_payload = {
        "slug": fixture["slug"],
        **_revision_payload(fixture, "Initial advisory"),
    }
    created = client.post(
        "/api/v1/operations/advisories",
        headers=fixture["headers"],
        json=create_payload,
    )

    assert created.status_code == 201
    advisory_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "draft"
    assert created.json()["data"]["revision"]["version"] == 1
    assert created.json()["data"]["revision"]["evidence"][0]["id"] == str(fixture["evidence_id"])
    assert created.json()["data"]["revision"]["actors"][0]["id"] == str(fixture["actor_id"])
    assert created.json()["data"]["revision"]["campaigns"][0]["id"] == str(fixture["campaign_id"])
    assert created.json()["data"]["revision"]["techniques"][0]["id"] == str(fixture["technique_id"])
    assert client.get(f"/api/v1/advisories/{fixture['slug']}").status_code == 404

    published_v1 = client.post(
        f"/api/v1/operations/advisories/{advisory_id}/revisions/1/publish",
        headers=fixture["headers"],
        json={"published_by": "publisher@example.test"},
    )
    assert published_v1.status_code == 200
    assert published_v1.json()["data"]["revision"]["published_by"] == "publisher@example.test"

    revision_two = client.post(
        f"/api/v1/operations/advisories/{advisory_id}/revisions",
        headers=fixture["headers"],
        json=_revision_payload(fixture, "Revised advisory"),
    )
    assert revision_two.status_code == 201
    assert revision_two.json()["data"]["revision"]["version"] == 2
    assert revision_two.json()["data"]["revision"]["published_at"] is None

    before_publish = client.get(f"/api/v1/advisories/{fixture['slug']}")
    assert before_publish.json()["data"]["revision"]["title"] == "Initial advisory"

    published_v2 = client.post(
        f"/api/v1/operations/advisories/{advisory_id}/revisions/2/publish",
        headers=fixture["headers"],
        json={"published_by": "publisher@example.test"},
    )
    assert published_v2.status_code == 200
    update = client.post(
        f"/api/v1/operations/advisories/{advisory_id}/updates",
        headers=fixture["headers"],
        json={
            "occurred_at": "2026-09-30T12:30:00Z",
            "title": "Detection guidance updated",
            "summary": "A new observed detection pattern was linked.",
            "intelligence_type": "observed",
            "created_by": "analyst@example.test",
            "evidence_ids": [str(fixture["evidence_id"])],
        },
    )

    assert update.status_code == 201
    assert update.json()["sequence"] == 1
    assert update.json()["revision_version"] == 2
    assert update.json()["evidence"][0]["id"] == str(fixture["evidence_id"])

    current = client.get(f"/api/v1/advisories/{fixture['slug']}")
    previous = client.get(f"/api/v1/advisories/{fixture['slug']}/revisions/1")
    timeline = client.get(
        f"/api/v1/advisories/{fixture['slug']}/updates",
        params={"after_sequence": 0, "limit": 10},
    )
    listing = client.get("/api/v1/advisories", params={"limit": 10})

    assert current.status_code == previous.status_code == timeline.status_code == 200
    assert current.json()["data"]["revision"]["title"] == "Revised advisory"
    sections = current.json()["data"]["revision"]["sections"]
    assert [item["intelligence_type"] for item in sections] == ["observed", "assessed"]
    assert previous.json()["data"]["revision"]["title"] == "Initial advisory"
    assert previous.json()["data"]["revision"]["version"] == 1
    assert timeline.json()["data"][0]["sequence"] == 1
    assert listing.json()["data"][0]["slug"] == fixture["slug"]


def test_operator_auth_and_advisory_validation(
    advisory_api: tuple[TestClient, dict[str, object]],
) -> None:
    client, fixture = advisory_api
    payload = {"slug": fixture["slug"], **_revision_payload(fixture, "Auth check")}

    assert client.post("/api/v1/operations/advisories", json=payload).status_code == 401
    payload["sections"] = [payload["sections"][0], payload["sections"][0]]  # type: ignore[index]
    invalid = client.post("/api/v1/operations/advisories", headers=fixture["headers"], json=payload)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
