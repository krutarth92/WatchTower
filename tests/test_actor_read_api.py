from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from watchtower.core.config import Settings
from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Evidence,
    IntelligenceType,
    Observation,
    Origin,
    PublicationState,
    Source,
    Technique,
)
from watchtower.db.session import get_session
from watchtower.main import create_app
from watchtower.services.actor_resolution import normalize_actor_name

pytestmark = pytest.mark.integration


@dataclass(frozen=True, slots=True)
class ActorApiFixture:
    client: TestClient
    session: Session
    actor_id: UUID
    empty_actor_id: UUID
    observation_ids: tuple[UUID, ...]
    alias_name: str
    evidence_id: UUID
    source_id: UUID
    behavior_id: UUID
    technique_id: UUID


@pytest.fixture
def actor_api(db_session: Session) -> Iterator[ActorApiFixture]:
    token = uuid4().hex
    source = Source(
        name=f"Actor API source {token}",
        kind="dataset",
        base_url="https://example.test/intelligence",
    )
    technique_source = Source(
        name=f"Technique source {token}",
        kind="framework",
        base_url="https://example.test/techniques",
    )
    actor = Actor(
        canonical_name=f"Northwind Group {token[:6]}",
        normalized_name=normalize_actor_name(f"Northwind Group {token[:6]}"),
        description="Fixture actor used to validate public reads.",
    )
    empty_actor = Actor(
        canonical_name=f"Empty Actor {token[:6]}",
        normalized_name=normalize_actor_name(f"Empty Actor {token[:6]}"),
    )
    alias_name = f"Vendor Shadow {token[:6]}"
    alias = Alias(
        actor=actor,
        source=source,
        name=alias_name,
        normalized_name=normalize_actor_name(alias_name),
        source_native_id=f"alias--{token}",
        confidence=91,
    )
    behavior = Behavior(
        name=f"Changes tooling {token[:6]}",
        normalized_name=normalize_actor_name(f"Changes tooling {token[:6]}"),
        description="Observed changes in tooling.",
    )
    technique = Technique(
        source=technique_source,
        external_id=f"T-{token[:8]}",
        name="Command and Scripting Interpreter",
        description="Fixture technique.",
    )
    evidence = Evidence(
        source=source,
        citation="Vendor report section 4",
        excerpt="The actor changed its scripting behavior.",
        locator="section-4",
        captured_at=datetime(2026, 4, 3, tzinfo=UTC),
        confidence=88,
        origin=Origin.IMPORTED,
    )
    observations = [
        Observation(
            source=source,
            source_native_id=f"observation--{token}--{index}",
            title=f"Timeline event {index}",
            summary=f"Fixture timeline summary {index}.",
            observed_at=observed_at,
            first_seen=observed_at,
            last_seen=observed_at,
            confidence=80 + index,
            intelligence_type=intelligence_type,
            origin=origin,
        )
        for index, observed_at, intelligence_type, origin in (
            (1, datetime(2026, 1, 10, tzinfo=UTC), IntelligenceType.OBSERVED, Origin.IMPORTED),
            (2, datetime(2026, 2, 10, tzinfo=UTC), IntelligenceType.OBSERVED, Origin.IMPORTED),
            (3, datetime(2026, 3, 10, tzinfo=UTC), IntelligenceType.ASSESSED, Origin.WATCHTOWER),
            (4, datetime(2026, 4, 10, tzinfo=UTC), IntelligenceType.OBSERVED, Origin.IMPORTED),
        )
    ]
    for record in (
        source,
        technique_source,
        actor,
        empty_actor,
        alias,
        behavior,
        technique,
        evidence,
        *observations,
    ):
        record.publication_state = PublicationState.PUBLISHED
    actor.observations.extend(observations)
    observations[-1].evidence.append(evidence)
    observations[-1].behaviors.append(behavior)
    observations[-1].techniques.append(technique)
    db_session.add_all([source, technique_source, actor, empty_actor, alias])
    db_session.flush()

    app = create_app(Settings())  # pyright: ignore[reportCallIssue]

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield ActorApiFixture(
            client=client,
            session=db_session,
            actor_id=actor.id,
            empty_actor_id=empty_actor.id,
            observation_ids=tuple(item.id for item in observations),
            alias_name=alias_name,
            evidence_id=evidence.id,
            source_id=source.id,
            behavior_id=behavior.id,
            technique_id=technique.id,
        )


def test_actor_lookup_request_id_and_openapi(actor_api: ActorApiFixture) -> None:
    response = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}",
        headers={"X-Request-ID": "actor-read-test-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "actor-read-test-1"
    assert response.json()["data"]["id"] == str(actor_api.actor_id)
    assert response.json()["data"]["canonical_name"].startswith("Northwind Group")
    openapi = actor_api.client.get("/openapi.json").json()
    assert "/api/v1/actors/{actor_id}/timeline" in openapi["paths"]
    assert "TimelinePageResponse" in openapi["components"]["schemas"]
    assert "ErrorResponse" in openapi["components"]["schemas"]


def test_large_reads_are_compressed_without_compressing_small_actor_reads(
    actor_api: ActorApiFixture,
) -> None:
    headers = {"Accept-Encoding": "gzip"}
    actor = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}", headers=headers)
    timeline = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/timeline",
        params={"limit": 100},
        headers=headers,
    )

    assert actor.status_code == timeline.status_code == 200
    assert "content-encoding" not in actor.headers
    assert timeline.headers["content-encoding"] == "gzip"
    assert len(timeline.json()["data"]) == 4


def test_actor_not_found_uses_stable_error(actor_api: ActorApiFixture) -> None:
    response = actor_api.client.get(
        f"/api/v1/actors/{uuid4()}",
        headers={"X-Request-ID": "missing-actor"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "actor_not_found",
            "message": "Actor was not found.",
            "request_id": "missing-actor",
            "details": [],
        }
    }
    assert response.headers["X-Request-ID"] == "missing-actor"


def test_internal_actor_is_indistinguishable_from_missing(
    actor_api: ActorApiFixture,
) -> None:
    internal_actor = Actor(
        canonical_name=f"Internal Actor {uuid4().hex[:8]}",
        normalized_name=f"internal actor {uuid4().hex}",
    )
    actor_api.session.add(internal_actor)
    actor_api.session.flush()

    detail = actor_api.client.get(f"/api/v1/actors/{internal_actor.id}")
    search = actor_api.client.get(
        "/api/v1/actors/search", params={"q": internal_actor.canonical_name}
    )

    assert internal_actor.publication_state is PublicationState.INTERNAL
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "actor_not_found"
    assert search.status_code == 200
    assert search.json()["data"] == []


def test_internal_nested_records_are_omitted(actor_api: ActorApiFixture) -> None:
    internal_observation = Observation(
        source_id=actor_api.source_id,
        source_native_id=f"internal--{uuid4().hex}",
        title="Internal only observation",
        summary="This record must not appear in a public actor response.",
        observed_at=datetime(2026, 5, 10, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    actor = actor_api.session.get(Actor, actor_api.actor_id)
    assert actor is not None
    actor.observations.append(internal_observation)
    internal_source = Source(name=f"Internal source {uuid4().hex}", kind="reporting")
    actor.observations.append(
        Observation(
            source=internal_source,
            source_native_id=f"published-with-private-source--{uuid4().hex}",
            title="Published record with internal source",
            summary="A public-state record must still preserve private provenance.",
            observed_at=datetime(2026, 5, 11, tzinfo=UTC),
            intelligence_type=IntelligenceType.OBSERVED,
            origin=Origin.IMPORTED,
            publication_state=PublicationState.PUBLISHED,
        )
    )
    actor.aliases.append(
        Alias(
            source_id=actor_api.source_id,
            name="Internal only alias",
            normalized_name=f"internal only alias {uuid4().hex}",
        )
    )
    published_observation = actor_api.session.get(Observation, actor_api.observation_ids[-1])
    assert published_observation is not None
    published_observation.evidence.append(
        Evidence(
            source_id=actor_api.source_id,
            citation="Internal only evidence",
            origin=Origin.IMPORTED,
        )
    )
    published_observation.behaviors.append(
        Behavior(
            name="Internal only behavior",
            normalized_name=f"internal only behavior {uuid4().hex}",
        )
    )
    published_observation.techniques.append(
        Technique(
            source_id=actor_api.source_id,
            external_id=f"INTERNAL-{uuid4().hex}",
            name="Internal only technique",
        )
    )
    actor_api.session.flush()

    timeline = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/timeline")
    aliases = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/aliases")
    associations = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/associations")
    references = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/references")

    assert {
        timeline.status_code,
        aliases.status_code,
        associations.status_code,
        references.status_code,
    } == {200}
    assert "Internal only" not in str(timeline.json())
    assert "Published record with internal source" not in {
        item["title"] for item in timeline.json()["data"]
    }
    assert "Internal only evidence" not in {
        item["citation"] for item in references.json()["data"]["evidence"]
    }
    assert "Internal only alias" not in {item["name"] for item in aliases.json()["data"]["items"]}
    assert "Internal only behavior" not in {
        item["name"] for item in associations.json()["data"]["behaviors"]
    }
    assert "Internal only technique" not in {
        item["name"] for item in associations.json()["data"]["techniques"]
    }


def test_alias_search_and_source_preservation(actor_api: ActorApiFixture) -> None:
    search = actor_api.client.get("/api/v1/actors/search", params={"q": actor_api.alias_name})
    aliases = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/aliases")

    assert search.status_code == 200
    assert [item["id"] for item in search.json()["data"]] == [str(actor_api.actor_id)]
    assert actor_api.alias_name in search.json()["data"][0]["matched_names"]
    assert aliases.status_code == 200
    assert aliases.json()["data"]["items"][0]["name"] == actor_api.alias_name
    assert aliases.json()["data"]["items"][0]["source_native_id"].startswith("alias--")
    assert aliases.json()["data"]["items"][0]["source"]["id"] == str(actor_api.source_id)


def test_observation_cursor_pagination_is_complete_and_stable(
    actor_api: ActorApiFixture,
) -> None:
    first = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/observations",
        params={"limit": 2},
    )
    first_body = first.json()
    second = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/observations",
        params={"limit": 2, "cursor": first_body["page"]["next_cursor"]},
    )
    second_body = second.json()

    assert first.status_code == second.status_code == 200
    first_ids = [item["id"] for item in first_body["data"]]
    second_ids = [item["id"] for item in second_body["data"]]
    assert len(first_ids) == len(second_ids) == 2
    assert not set(first_ids) & set(second_ids)
    assert set(first_ids + second_ids) == {str(item) for item in actor_api.observation_ids}
    assert second_body["page"]["next_cursor"] is None

    altered_cursor = f"{first_body['page']['next_cursor']}x"
    invalid = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/observations",
        params={"cursor": altered_cursor},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_timeline_date_and_intelligence_type_filters(actor_api: ActorApiFixture) -> None:
    response = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/timeline",
        params={
            "date_from": "2026-02-01T00:00:00Z",
            "date_to": "2026-03-31T23:59:59Z",
            "intelligence_type": "assessed",
        },
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()["data"]] == ["Timeline event 3"]
    assert response.json()["data"][0]["event_type"] == "observation"
    assert response.json()["data"][0]["intelligence_type"] == "assessed"


def test_empty_actor_timeline(actor_api: ActorApiFixture) -> None:
    response = actor_api.client.get(f"/api/v1/actors/{actor_api.empty_actor_id}/timeline")

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["page"] == {"limit": 25, "next_cursor": None}


def test_timeline_associations_and_evidence_references(actor_api: ActorApiFixture) -> None:
    timeline = actor_api.client.get(
        f"/api/v1/actors/{actor_api.actor_id}/timeline",
        params={"date_from": "2026-04-01T00:00:00Z"},
    )
    associations = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/associations")
    references = actor_api.client.get(f"/api/v1/actors/{actor_api.actor_id}/references")

    assert timeline.status_code == associations.status_code == references.status_code == 200
    event_body = timeline.json()["data"][0]
    assert event_body["evidence"][0]["id"] == str(actor_api.evidence_id)
    assert event_body["evidence"][0]["source"]["id"] == str(actor_api.source_id)
    assert event_body["behaviors"][0]["id"] == str(actor_api.behavior_id)
    assert event_body["techniques"][0]["id"] == str(actor_api.technique_id)
    assert associations.json()["data"]["behaviors"][0]["id"] == str(actor_api.behavior_id)
    assert associations.json()["data"]["techniques"][0]["id"] == str(actor_api.technique_id)
    assert references.json()["data"]["evidence"][0]["id"] == str(actor_api.evidence_id)
    assert str(actor_api.source_id) in {item["id"] for item in references.json()["data"]["sources"]}


def test_timeline_query_count_is_bounded_by_relationship_types(
    actor_api: ActorApiFixture,
) -> None:
    bind = actor_api.session.get_bind()
    counts: list[int] = []

    def count_query(
        _connection: Connection,
        _cursor: object,
        _statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        counts[-1] += 1

    event.listen(bind, "before_cursor_execute", count_query)
    try:
        for limit in (1, 4):
            actor_api.session.expire_all()
            counts.append(0)
            response = actor_api.client.get(
                f"/api/v1/actors/{actor_api.actor_id}/timeline",
                params={"limit": limit},
            )
            assert response.status_code == 200
    finally:
        event.remove(bind, "before_cursor_execute", count_query)

    assert counts[0] == counts[1]
    assert counts[0] <= 6
    assert counts[0] > 0
