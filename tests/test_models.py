from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Campaign,
    Evidence,
    IntelligenceType,
    Observation,
    Origin,
    RawEvidence,
    Relationship,
    Source,
    Technique,
    actor_observations,
)

pytestmark = pytest.mark.integration

InvalidModelFactory = Callable[[Source], Actor | RawEvidence | Observation | Campaign]


def make_source(session: Session, token: str) -> Source:
    source = Source(name=f"Test Source {token}", kind="dataset")
    session.add(source)
    session.flush()
    return source


def test_full_intelligence_lifecycle_and_timeline(db_session: Session) -> None:
    token = uuid4().hex
    source = make_source(db_session, token)
    raw = RawEvidence(
        source=source,
        storage_uri=f"s3://evidence/{token}.json",
        content_sha256="a" * 64,
        retrieved_at=datetime(2026, 1, 3, tzinfo=UTC),
        published_at=datetime(2026, 1, 2, tzinfo=UTC),
        mime_type="application/json",
        source_native_id=f"bundle--{token}",
    )
    actor = Actor(canonical_name="Example Group", normalized_name=f"example-group-{token}")
    actor.aliases.extend(
        [
            Alias(
                source=source,
                name="Example Vendor Name",
                normalized_name=f"example-vendor-name-{token}",
                confidence=90,
            )
        ]
    )
    unresolved_alias = Alias(
        source=source,
        name="Possibly Related Group",
        normalized_name=f"possibly-related-{token}",
    )
    evidence = Evidence(
        source=source,
        raw_evidence=raw,
        citation="STIX object intrusion-set--example",
        locator="objects[0]",
        excerpt="Fixture-only evidence excerpt",
        origin=Origin.IMPORTED,
    )
    behavior = Behavior(name="Uses scripting", normalized_name=f"uses-scripting-{token}")
    technique = Technique(
        source=source,
        external_id=f"T-{token[:8]}",
        name="Command and Scripting Interpreter",
    )
    earlier = Observation(
        source=source,
        raw_evidence=raw,
        source_native_id=f"observation-early-{token}",
        title="Earlier behavior",
        summary="The source reports scripting activity.",
        observed_at=datetime(2026, 1, 4, tzinfo=UTC),
        confidence=80,
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    later = Observation(
        source=source,
        raw_evidence=raw,
        source_native_id=f"observation-late-{token}",
        title="Later behavior",
        summary="The source reports a subsequent behavior change.",
        observed_at=datetime(2026, 2, 4, tzinfo=UTC),
        first_seen=datetime(2026, 2, 1, tzinfo=UTC),
        last_seen=datetime(2026, 2, 4, tzinfo=UTC),
        confidence=75,
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    actor.observations.extend([later, earlier])
    earlier.evidence.append(evidence)
    earlier.behaviors.append(behavior)
    earlier.techniques.append(technique)
    campaign = Campaign(
        source=source,
        name="Example Campaign",
        normalized_name=f"example-campaign-{token}",
        first_seen=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen=datetime(2026, 2, 28, tzinfo=UTC),
        confidence=70,
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    actor_campaign = Relationship(
        actor=actor,
        campaign=campaign,
        source=source,
        evidence=evidence,
        relationship_type="attributed-to",
        first_seen=datetime(2026, 1, 1, tzinfo=UTC),
        last_seen=datetime(2026, 2, 28, tzinfo=UTC),
        confidence=65,
        intelligence_type=IntelligenceType.ASSESSED,
        origin=Origin.WATCHTOWER,
    )
    db_session.add_all([raw, actor, unresolved_alias, campaign, actor_campaign])
    db_session.flush()

    assert unresolved_alias.actor_id is None
    timeline = db_session.scalars(
        select(Observation)
        .join(actor_observations)
        .where(actor_observations.c.actor_id == actor.id)
        .order_by(Observation.observed_at)
    ).all()
    assert [item.title for item in timeline] == ["Earlier behavior", "Later behavior"]

    loaded = db_session.scalar(
        select(Observation)
        .where(Observation.id == earlier.id)
        .options(
            selectinload(Observation.actors),
            selectinload(Observation.evidence),
            selectinload(Observation.behaviors),
            selectinload(Observation.techniques),
        )
    )
    assert loaded is not None
    assert loaded.source_id == source.id
    assert loaded.raw_evidence_id == raw.id
    assert loaded.actors == [actor]
    assert loaded.evidence == [evidence]
    assert loaded.behaviors == [behavior]
    assert loaded.techniques == [technique]
    assert actor_campaign.evidence_id == evidence.id
    assert actor_campaign.campaign_id == campaign.id


def test_assessment_is_separate_from_imported_observation(db_session: Session) -> None:
    token = uuid4().hex
    external = make_source(db_session, f"external-{token}")
    internal = Source(name=f"WATCHTOWER {token}", kind="internal")
    raw = RawEvidence(
        source=external,
        storage_uri=f"file:///fixtures/{token}.json",
        content_sha256="b" * 64,
        retrieved_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    evidence = Evidence(
        source=external,
        raw_evidence=raw,
        citation="Fixture source record",
        origin=Origin.IMPORTED,
    )
    imported = Observation(
        source=external,
        raw_evidence=raw,
        title="Imported fact",
        summary="A fixture source fact.",
        observed_at=datetime(2026, 3, 1, tzinfo=UTC),
        intelligence_type=IntelligenceType.OBSERVED,
        origin=Origin.IMPORTED,
    )
    assessment = Observation(
        source=internal,
        title="WATCHTOWER assessment",
        summary="A fixture analytical assessment.",
        observed_at=datetime(2026, 3, 2, tzinfo=UTC),
        intelligence_type=IntelligenceType.ASSESSED,
        origin=Origin.WATCHTOWER,
    )
    imported.evidence.append(evidence)
    assessment.evidence.append(evidence)
    db_session.add_all([internal, raw, imported, assessment])
    db_session.flush()

    assert imported.id != assessment.id
    assert imported.origin is Origin.IMPORTED
    assert assessment.origin is Origin.WATCHTOWER
    assert assessment.raw_evidence_id is None
    assert assessment.evidence == [evidence]


@pytest.mark.parametrize(
    ("model_name", "make_invalid"),
    [
        ("actor name", lambda source: Actor(canonical_name=" ", normalized_name="invalid")),
        (
            "raw hash",
            lambda source: RawEvidence(
                source=source,
                storage_uri="file:///fixture.json",
                content_sha256="not-a-sha256",
                retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ),
        (
            "observation confidence",
            lambda source: Observation(
                source=source,
                title="Invalid confidence",
                summary="Fixture",
                observed_at=datetime(2026, 1, 1, tzinfo=UTC),
                confidence=101,
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
            ),
        ),
        (
            "campaign time range",
            lambda source: Campaign(
                source=source,
                name="Invalid range",
                normalized_name=f"invalid-range-{uuid4().hex}",
                first_seen=datetime(2026, 2, 1, tzinfo=UTC),
                last_seen=datetime(2026, 1, 1, tzinfo=UTC),
                intelligence_type=IntelligenceType.OBSERVED,
                origin=Origin.IMPORTED,
            ),
        ),
    ],
)
def test_database_rejects_obvious_invalid_states(
    db_session: Session, model_name: str, make_invalid: InvalidModelFactory
) -> None:
    token = uuid4().hex
    source = make_source(db_session, token)
    assert model_name
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(make_invalid(source))
            db_session.flush()
