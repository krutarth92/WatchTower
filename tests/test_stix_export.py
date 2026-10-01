from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from stix2 import parse as parse_stix

from watchtower.core.config import Settings
from watchtower.db.models import (
    Actor,
    Alias,
    Campaign,
    Evidence,
    IntelligenceType,
    Observation,
    Origin,
    Relationship,
    Source,
    Technique,
)
from watchtower.db.session import get_session
from watchtower.exports.stix import StixActorNotFoundError, StixExportService
from watchtower.main import create_app

pytestmark = pytest.mark.integration


def seed_export_graph(db_session: Session) -> Actor:
    token = uuid4().hex
    source = Source(
        name=f"Task 12 Source {token}",
        kind="dataset",
        base_url="https://example.test/intelligence",
    )
    actor = Actor(
        canonical_name="Example Intrusion Set",
        normalized_name=f"example-intrusion-set-{token}",
        description="An actor used to verify the bounded STIX mapping.",
    )
    actor.aliases.append(
        Alias(
            source=source,
            name="Example Vendor Alias",
            normalized_name=f"example-vendor-alias-{token}",
            source_native_id=f"intrusion-set--{token}",
            confidence=92,
        )
    )
    technique = Technique(
        source=source,
        external_id="T1059.001",
        name="PowerShell",
        description="PowerShell command execution.",
    )
    evidence = Evidence(
        source=source,
        citation="Vendor report section 4",
        excerpt="The group used PowerShell during the campaign.",
        locator="https://example.test/intelligence/report#section-4",
        captured_at=datetime(2026, 3, 5, tzinfo=UTC),
        confidence=85,
        origin=Origin.IMPORTED,
    )
    observed = Observation(
        source=source,
        source_native_id=f"observation--{token}",
        title="PowerShell activity",
        summary="The source reports PowerShell activity by the actor.",
        observed_at=datetime(2026, 3, 4, tzinfo=UTC),
        first_seen=datetime(2026, 3, 1, tzinfo=UTC),
        last_seen=datetime(2026, 3, 4, tzinfo=UTC),
        confidence=80,
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    observed.techniques.append(technique)
    observed.evidence.append(evidence)
    assessed = Observation(
        source=source,
        source_native_id=f"assessment--{token}",
        title="Analyst assessment",
        summary="WATCHTOWER assesses the activity as consistent with this actor.",
        observed_at=datetime(2026, 3, 6, tzinfo=UTC),
        confidence=65,
        intelligence_type=IntelligenceType.ASSESSED,
        origin=Origin.WATCHTOWER,
    )
    assessed.evidence.append(evidence)
    actor.observations.extend([observed, assessed])

    campaign = Campaign(
        source=source,
        source_native_id=f"campaign--{token}",
        name="Example Campaign",
        normalized_name=f"example-campaign-{token}",
        description="A campaign with explicit actor attribution.",
        first_seen=datetime(2026, 2, 1, tzinfo=UTC),
        last_seen=datetime(2026, 3, 4, tzinfo=UTC),
        confidence=75,
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    attribution = Relationship(
        actor=actor,
        campaign=campaign,
        source=source,
        evidence=evidence,
        relationship_type="attributed-to",
        first_seen=datetime(2026, 2, 2, tzinfo=UTC),
        last_seen=datetime(2026, 3, 4, tzinfo=UTC),
        confidence=70,
        intelligence_type=IntelligenceType.ASSESSED,
        origin=Origin.WATCHTOWER,
    )
    excluded_campaign = Campaign(
        source=source,
        source_native_id=f"excluded-campaign--{token}",
        name="Unsupported Relationship Campaign",
        normalized_name=f"unsupported-campaign-{token}",
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    unsupported = Relationship(
        actor=actor,
        campaign=excluded_campaign,
        source=source,
        relationship_type="related-to",
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    db_session.add_all([actor, campaign, attribution, excluded_campaign, unsupported])
    db_session.flush()
    return actor


def test_actor_export_is_valid_deterministic_and_semantically_bounded(
    db_session: Session,
) -> None:
    actor = seed_export_graph(db_session)
    service = StixExportService()

    first = service.export_actor(db_session, actor.id)
    second = service.export_actor(db_session, actor.id)
    parsed: Any = parse_stix(first, allow_custom=False, version="2.1")

    assert parsed.type == "bundle"
    assert first == second
    assert first["id"] == second["id"]
    objects = first["objects"]
    by_type: dict[str, list[dict[str, object]]] = {}
    for item in objects:
        by_type.setdefault(str(item["type"]), []).append(item)

    assert {item["type"] for item in objects} == {
        "attack-pattern",
        "campaign",
        "intrusion-set",
        "note",
        "relationship",
    }
    assert "indicator" not in by_type
    assert "observed-data" not in by_type
    assert len(by_type["intrusion-set"]) == 1
    assert by_type["intrusion-set"][0]["aliases"] == ["Example Vendor Alias"]
    assert len(by_type["attack-pattern"]) == 1
    assert by_type["attack-pattern"][0]["external_references"][0]["external_id"] == "T1059.001"  # type: ignore[index]
    assert len(by_type["campaign"]) == 1
    assert by_type["campaign"][0]["name"] == "Example Campaign"
    assert by_type["campaign"][0]["confidence"] == 75

    notes = by_type["note"]
    assert len(notes) == 2
    assert {tuple(item["labels"]) for item in notes} == {  # type: ignore[arg-type]
        ("watchtower:observed",),
        ("watchtower:assessed",),
    }
    assert any("WATCHTOWER intelligence time: 2026-03-04" in str(item["content"]) for item in notes)
    assert any(
        "Vendor report section 4" in str(reference.get("description"))
        for item in notes
        for reference in item["external_references"]  # type: ignore[union-attr]
    )

    relationships = by_type["relationship"]
    assert {item["relationship_type"] for item in relationships} == {"uses", "attributed-to"}
    actor_ref = str(by_type["intrusion-set"][0]["id"])
    campaign_ref = str(by_type["campaign"][0]["id"])
    attribution_object = next(
        item for item in relationships if item["relationship_type"] == "attributed-to"
    )
    assert attribution_object["source_ref"] == campaign_ref
    assert attribution_object["target_ref"] == actor_ref
    assert attribution_object["start_time"] == "2026-02-02T00:00:00.000Z"
    assert attribution_object["stop_time"] == "2026-03-04T00:00:00.000Z"
    assert all("Unsupported Relationship Campaign" not in str(item) for item in objects)

    with pytest.raises(StixActorNotFoundError):
        service.export_actor(db_session, uuid4())


def test_operator_stix_export_api(db_session: Session) -> None:
    actor = seed_export_graph(db_session)
    settings = Settings(operator_token="task-12-test-operator-token-0001")  # pyright: ignore[reportCallIssue]
    token = settings.operator_token
    assert token is not None
    app = create_app(settings)

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    headers = {"X-WATCHTOWER-Operator-Token": token.get_secret_value()}
    with TestClient(app) as client:
        unauthorized = client.get(f"/api/v1/operations/exports/stix/actors/{actor.id}")
        response = client.get(f"/api/v1/operations/exports/stix/actors/{actor.id}", headers=headers)
        missing = client.get(f"/api/v1/operations/exports/stix/actors/{uuid4()}", headers=headers)
        openapi = client.get("/openapi.json")

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/stix+json")
    parsed: Any = parse_stix(response.json(), allow_custom=False, version="2.1")
    assert parsed.type == "bundle"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "actor_not_found"
    path = openapi.json()["paths"]["/api/v1/operations/exports/stix/actors/{actor_id}"]
    assert "application/stix+json" in path["get"]["responses"]["200"]["content"]
