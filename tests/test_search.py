import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from watchtower.api.v1.search_schemas import SearchEntityType, SearchMatchKind
from watchtower.core.config import Settings
from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Campaign,
    IntelligenceType,
    Observation,
    Origin,
    PublicationState,
    Source,
    Technique,
)
from watchtower.db.session import get_session
from watchtower.main import create_app
from watchtower.services.search import SearchService

pytestmark = pytest.mark.integration
EVALUATION_PATH = Path(__file__).parent / "evaluations" / "search-baseline.json"


def seed_search_evaluation(db_session: Session) -> dict[str, Source]:
    alpha = Source(
        name="Task09 Alpha Intelligence",
        kind="dataset",
        policy_notes="Curated adversary research",
        source_metadata={"collection": "BlackEnergy archive"},
    )
    beta = Source(
        name="Task09 Beta Research",
        kind="reporting",
        policy_notes="Campaign tracking",
    )
    actor = Actor(
        canonical_name="Sandworm Team",
        normalized_name="sandworm team",
        description="Threat actor associated with disruptive operations.",
    )
    alias = Alias(
        source=alpha,
        actor=actor,
        name="Voodoo Bear",
        normalized_name="voodoo bear",
        source_native_id="alias--voodoo-bear",
    )
    campaign = Campaign(
        source=beta,
        source_native_id="campaign--northern-gale",
        name="Northern Gale Campaign",
        normalized_name="northern gale campaign",
        description="A northern campaign focused on public-sector targets.",
        first_seen=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen=datetime(2026, 3, 1, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    behavior = Behavior(
        name="PowerShell Scripting",
        normalized_name="powershell scripting",
        description="Uses PowerShell scripts for command execution.",
    )
    technique = Technique(
        source=alpha,
        external_id="T1059.001",
        name="PowerShell",
        description="A command and scripting interpreter available on Windows.",
    )
    observed = Observation(
        source=alpha,
        source_native_id="observation--credential-phishing",
        title="Credential phishing activity",
        summary=(
            "Operators conducted a credential harvesting operation through targeted phishing."
        ),
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    distractor = Observation(
        source=beta,
        source_native_id="observation--scattered-terms",
        title="Credential operation report",
        summary=(
            "The operation used unrelated tooling before harvesting browser data and later "
            "tested credential access."
        ),
        observed_at=datetime(2026, 1, 20, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    assessment = Observation(
        source=beta,
        source_native_id="observation--credential-assessment",
        title="Credential risk assessment",
        summary="WATCHTOWER assessment of credential exposure risk.",
        observed_at=datetime(2026, 2, 15, tzinfo=UTC),
        intelligence_type=IntelligenceType.ASSESSED,
        origin=Origin.WATCHTOWER,
    )
    actor.observations.append(observed)
    observed.behaviors.append(behavior)
    observed.techniques.append(technique)
    for record in (
        alpha,
        beta,
        actor,
        alias,
        campaign,
        behavior,
        technique,
        observed,
        distractor,
        assessment,
    ):
        record.publication_state = PublicationState.PUBLISHED
    db_session.add_all(
        [
            alpha,
            beta,
            actor,
            alias,
            campaign,
            behavior,
            technique,
            observed,
            distractor,
            assessment,
        ]
    )
    db_session.flush()
    return {"alpha": alpha, "beta": beta}


def load_evaluation_cases() -> list[dict[str, Any]]:
    return json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))


def test_curated_search_evaluation_and_stable_ranking(db_session: Session) -> None:
    sources = seed_search_evaluation(db_session)
    service = SearchService()

    for case in load_evaluation_cases():
        entity_types = (
            {SearchEntityType(value) for value in case["entity_types"]}
            if "entity_types" in case
            else None
        )
        source_id = sources[case["source_key"]].id if "source_key" in case else None
        intelligence_type = (
            IntelligenceType(case["intelligence_type"]) if "intelligence_type" in case else None
        )
        date_from = datetime.fromisoformat(case["date_from"]) if "date_from" in case else None
        _, results = service.search(
            db_session,
            case["query"],
            entity_types=entity_types,
            source_id=source_id,
            intelligence_type=intelligence_type,
            date_from=date_from,
            limit=25,
        )
        assert results, case["name"]
        assert results[0].entity_type.value == case["expected_type"], case["name"]
        assert results[0].title == case["expected_title"], case["name"]

        _, repeated = service.search(
            db_session,
            case["query"],
            entity_types=entity_types,
            source_id=source_id,
            intelligence_type=intelligence_type,
            date_from=date_from,
            limit=25,
        )
        assert [item.id for item in repeated] == [item.id for item in results]

    _, exact_results = service.search(db_session, "Sandworm Team")
    assert exact_results[0].match_kind is SearchMatchKind.EXACT
    assert exact_results[0].score >= 100


def test_search_api_filters_validation_and_response_contract(db_session: Session) -> None:
    sources = seed_search_evaluation(db_session)
    app = create_app(Settings())  # pyright: ignore[reportCallIssue]

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/search",
            params=[
                ("q", "credential phishing"),
                ("entity_type", "observation"),
                ("source_id", str(sources["alpha"].id)),
                ("limit", "10"),
            ],
            headers={"X-Request-ID": "task-09-search-test"},
        )
        invalid_dates = client.get(
            "/api/v1/search",
            params={
                "q": "credential",
                "date_from": "2026-03-01T00:00:00Z",
                "date_to": "2026-02-01T00:00:00Z",
            },
        )
        unsafe = client.get("/api/v1/search", params={"q": "bad\nquery"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "task-09-search-test"
    payload = response.json()
    assert payload["query"] == "credential phishing"
    assert payload["limit"] == 10
    assert payload["data"][0]["entity_type"] == "observation"
    assert payload["data"][0]["title"] == "Credential phishing activity"
    assert payload["data"][0]["source_id"] == str(sources["alpha"].id)
    assert invalid_dates.status_code == 422
    assert unsafe.status_code == 422


def test_search_excludes_internal_records(db_session: Session) -> None:
    source = Source(
        name="Published Fixture Source",
        kind="reporting",
        publication_state=PublicationState.PUBLISHED,
    )
    internal_source = Source(name="Internal Search Source", kind="reporting")
    actor = Actor(
        canonical_name="Internal Search Actor",
        normalized_name="internal search actor",
    )
    published_actor = Actor(
        canonical_name="Published Fixture Actor",
        normalized_name="published fixture actor",
        publication_state=PublicationState.PUBLISHED,
    )
    alias = Alias(
        source=source,
        actor=published_actor,
        name="Internal Search Alias",
        normalized_name="internal search alias",
    )
    campaign = Campaign(
        source=source,
        name="Internal Search Campaign",
        normalized_name="internal search campaign",
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    behavior = Behavior(
        name="Internal Search Behavior",
        normalized_name="internal search behavior",
    )
    technique = Technique(
        source=source,
        external_id="INTERNAL-SEARCH-TECHNIQUE",
        name="Internal Search Technique",
    )
    observation = Observation(
        source=source,
        source_native_id="internal-search-observation",
        title="Internal Search Finding",
        summary="A uniquely searchable record that remains private.",
        observed_at=datetime(2026, 4, 1, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    published_with_internal_source = Observation(
        source=internal_source,
        source_native_id="published-with-internal-source",
        title="Private Provenance Search Finding",
        summary="A published record backed by an internal source remains private.",
        observed_at=datetime(2026, 4, 2, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
        publication_state=PublicationState.PUBLISHED,
    )
    db_session.add_all(
        [
            source,
            internal_source,
            actor,
            published_actor,
            alias,
            campaign,
            behavior,
            technique,
            observation,
            published_with_internal_source,
        ]
    )
    db_session.flush()

    _, results = SearchService().search(db_session, "Internal Search")
    _, provenance_results = SearchService().search(db_session, "Private Provenance")

    assert internal_source.publication_state is PublicationState.INTERNAL
    assert actor.publication_state is PublicationState.INTERNAL
    assert alias.publication_state is PublicationState.INTERNAL
    assert campaign.publication_state is PublicationState.INTERNAL
    assert behavior.publication_state is PublicationState.INTERNAL
    assert technique.publication_state is PublicationState.INTERNAL
    assert observation.publication_state is PublicationState.INTERNAL
    assert results == []
    assert provenance_results == []


def test_search_indexes_exist_and_support_full_text_plan(db_session: Session) -> None:
    indexes = set(
        db_session.scalars(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = current_schema() AND indexname LIKE 'ix_%_search_document'"
            )
        ).all()
    )
    assert {
        "ix_actors_search_document",
        "ix_aliases_search_document",
        "ix_behaviors_search_document",
        "ix_campaigns_search_document",
        "ix_observations_search_document",
        "ix_sources_search_document",
        "ix_techniques_search_document",
    } <= indexes

    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(
        db_session.scalars(
            text(
                "EXPLAIN SELECT id FROM observations WHERE search_document @@ "
                "websearch_to_tsquery('english'::regconfig, 'credential')"
            )
        ).all()
    )
    assert "ix_observations_search_document" in plan
