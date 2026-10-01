from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from watchtower.db.models import (
    Actor,
    ActorResolutionDecision,
    Alias,
    Evidence,
    Origin,
    ResolutionDecision,
    ResolutionMethod,
    Source,
)
from watchtower.services.actor_resolution import (
    ActorResolutionService,
    AliasAssertion,
    AliasConflictError,
    KnownAliasRuleInput,
    ManualResolutionInput,
    normalize_actor_name,
)

pytestmark = pytest.mark.integration


def make_source(session: Session, label: str) -> Source:
    source = Source(name=f"Resolution source {label} {uuid4().hex}", kind="dataset")
    session.add(source)
    session.flush()
    return source


def make_actor(session: Session, canonical_name: str) -> Actor:
    actor = Actor(
        canonical_name=canonical_name,
        normalized_name=normalize_actor_name(canonical_name),
    )
    session.add(actor)
    session.flush()
    return actor


def make_evidence(session: Session, source: Source, citation: str) -> Evidence:
    evidence = Evidence(source=source, citation=citation, origin=Origin.IMPORTED)
    session.add(evidence)
    session.flush()
    return evidence


def count_rows(
    session: Session, model: type[Actor] | type[Alias] | type[ActorResolutionDecision]
) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_exact_canonical_and_known_alias_rules_auto_link_with_audit(
    db_session: Session,
) -> None:
    service = ActorResolutionService()
    rule_source = make_source(db_session, "rule")
    canonical_source = make_source(db_session, "canonical")
    alias_source = make_source(db_session, "alias")
    actor = make_actor(db_session, "Meridian Group")
    evidence = make_evidence(db_session, rule_source, "Reviewed vendor naming record")

    registration = service.register_known_alias(
        db_session,
        KnownAliasRuleInput(
            alias_name="Night Lantern",
            actor_id=actor.id,
            reason="Reviewed source explicitly maps this vendor label.",
            confidence=96,
            evidence_id=evidence.id,
            created_by="analyst@example.test",
        ),
    )
    duplicate = service.register_known_alias(
        db_session,
        KnownAliasRuleInput(
            alias_name="Night Lantern",
            actor_id=actor.id,
            reason="Reviewed source explicitly maps this vendor label.",
            confidence=96,
            evidence_id=evidence.id,
            created_by="analyst@example.test",
        ),
    )
    canonical = service.resolve(
        db_session,
        AliasAssertion(source_id=canonical_source.id, name="Meridian  Group"),
    )
    known = service.resolve(
        db_session,
        AliasAssertion(
            source_id=alias_source.id,
            name="Night Lantern",
            source_native_id="vendor-actor-17",
            evidence_id=evidence.id,
        ),
    )

    assert registration.duplicate is False
    assert duplicate.duplicate is True
    assert duplicate.rule.id == registration.rule.id
    assert canonical.alias.actor_id == actor.id
    assert canonical.alias.name == "Meridian  Group"
    assert canonical.decision.method is ResolutionMethod.EXACT_ACTOR_NAME
    assert canonical.decision.confidence == 100
    assert known.alias.actor_id == actor.id
    assert known.alias.name == "Night Lantern"
    assert known.alias.source_native_id == "vendor-actor-17"
    assert known.decision.decision is ResolutionDecision.AUTO_LINK
    assert known.decision.method is ResolutionMethod.KNOWN_ALIAS
    assert (
        known.decision.reason
        == "Curated known-alias rule: Reviewed source explicitly maps this vendor label."
    )
    assert known.decision.confidence == 96
    assert known.decision.evidence_id == evidence.id


def test_similar_names_are_candidates_and_never_auto_merge(db_session: Session) -> None:
    service = ActorResolutionService()
    source = make_source(db_session, "similar")
    first = make_actor(db_session, "Silver Wolf East")
    second = make_actor(db_session, "Silver Wolf West")
    actor_count = count_rows(db_session, Actor)

    result = service.resolve(
        db_session,
        AliasAssertion(source_id=source.id, name="Silver Wolf Nest"),
    )

    assert result.alias.actor_id is None
    assert result.decision.decision is ResolutionDecision.UNRESOLVED
    assert result.decision.method is ResolutionMethod.SIMILARITY_CANDIDATES
    assert {candidate.actor_id for candidate in result.candidates} == {first.id, second.id}
    assert all(candidate.similarity is not None for candidate in result.candidates)
    assert count_rows(db_session, Actor) == actor_count


def test_conflicting_source_assertions_stay_ambiguous(db_session: Session) -> None:
    service = ActorResolutionService()
    first_source = make_source(db_session, "conflict-a")
    second_source = make_source(db_session, "conflict-b")
    third_source = make_source(db_session, "conflict-c")
    first_actor = make_actor(db_session, "Northstar Unit")
    second_actor = make_actor(db_session, "Southern Cross Unit")

    first_alias = service.resolve(
        db_session,
        AliasAssertion(source_id=first_source.id, name="Shared Vendor Label"),
    ).alias
    service.correct_manually(
        db_session,
        ManualResolutionInput(
            alias_id=first_alias.id,
            actor_id=first_actor.id,
            reason="First source assertion was reviewed.",
            confidence=85,
            decided_by="analyst-a",
        ),
    )
    second_alias = service.resolve(
        db_session,
        AliasAssertion(source_id=second_source.id, name="Shared Vendor Label"),
    ).alias
    service.correct_manually(
        db_session,
        ManualResolutionInput(
            alias_id=second_alias.id,
            actor_id=second_actor.id,
            reason="Second source assertion was independently reviewed.",
            confidence=80,
            decided_by="analyst-b",
        ),
    )

    conflicted = service.resolve(
        db_session,
        AliasAssertion(source_id=third_source.id, name="Shared Vendor Label"),
    )

    assert conflicted.alias.actor_id is None
    assert conflicted.decision.method is ResolutionMethod.AMBIGUOUS_EXACT
    assert {candidate.actor_id for candidate in conflicted.candidates} == {
        first_actor.id,
        second_actor.id,
    }
    assert all(
        "existing source alias assertion" in candidate.bases for candidate in conflicted.candidates
    )


def test_manual_link_relink_and_unlink_preserve_source_label_and_audit(
    db_session: Session,
) -> None:
    service = ActorResolutionService()
    source = make_source(db_session, "manual")
    first_actor = make_actor(db_session, "First Reviewed Actor")
    second_actor = make_actor(db_session, "Corrected Reviewed Actor")
    evidence = make_evidence(db_session, source, "Analyst review worksheet")
    initial = service.resolve(
        db_session,
        AliasAssertion(source_id=source.id, name="Vendor Label X"),
    )

    link_request = ManualResolutionInput(
        alias_id=initial.alias.id,
        actor_id=first_actor.id,
        reason="Initial analyst adjudication.",
        confidence=75,
        evidence_id=evidence.id,
        decided_by="analyst-one",
    )
    linked = service.correct_manually(db_session, link_request)
    repeated_link = service.correct_manually(db_session, link_request)
    relinked = service.correct_manually(
        db_session,
        ManualResolutionInput(
            alias_id=initial.alias.id,
            actor_id=second_actor.id,
            reason="New evidence corrects the earlier adjudication.",
            confidence=92,
            evidence_id=evidence.id,
            decided_by="analyst-two",
        ),
    )
    unlinked = service.correct_manually(
        db_session,
        ManualResolutionInput(
            alias_id=initial.alias.id,
            reason="Identity is unresolved pending additional evidence.",
            evidence_id=evidence.id,
            decided_by="analyst-two",
        ),
    )

    assert initial.alias.name == "Vendor Label X"
    assert linked.decision.previous_actor_id is None
    assert linked.decision.actor_id == first_actor.id
    assert repeated_link.repeated is True
    assert repeated_link.decision.id == linked.decision.id
    assert relinked.decision.previous_actor_id == first_actor.id
    assert relinked.decision.actor_id == second_actor.id
    assert unlinked.decision.decision is ResolutionDecision.MANUAL_UNLINK
    assert unlinked.decision.previous_actor_id == second_actor.id
    assert unlinked.alias.actor_id is None
    assert unlinked.alias.confidence is None
    assert count_rows(db_session, ActorResolutionDecision) == 4


def test_repeated_resolution_reuses_alias_and_decision(db_session: Session) -> None:
    service = ActorResolutionService()
    source = make_source(db_session, "repeat")
    actor = make_actor(db_session, "Repeatable Actor")
    request = AliasAssertion(
        source_id=source.id,
        name="Repeatable Actor",
        source_native_id="actor--repeatable",
        metadata={"collection": "test"},
    )

    first = service.resolve(db_session, request)
    second = service.resolve(db_session, request)

    assert first.repeated is False
    assert second.repeated is True
    assert second.alias.id == first.alias.id
    assert second.alias.actor_id == actor.id
    assert second.decision.id == first.decision.id
    assert count_rows(db_session, Alias) == 1
    assert count_rows(db_session, ActorResolutionDecision) == 1


def test_source_aliases_remain_distinct_and_conflicting_replay_is_rejected(
    db_session: Session,
) -> None:
    service = ActorResolutionService()
    first_source = make_source(db_session, "preserve-a")
    second_source = make_source(db_session, "preserve-b")
    actor = make_actor(db_session, "Canonical Falcon")
    service.register_known_alias(
        db_session,
        KnownAliasRuleInput(
            alias_name="Falcon Team",
            actor_id=actor.id,
            reason="Reviewed deterministic mapping.",
            created_by="curator",
        ),
    )
    actor_count = count_rows(db_session, Actor)
    first = service.resolve(
        db_session,
        AliasAssertion(
            source_id=first_source.id,
            name="Falcon Team",
            source_native_id="first-1",
            metadata={"vendor": "one"},
        ),
    )
    second = service.resolve(
        db_session,
        AliasAssertion(
            source_id=second_source.id,
            name="Falcon Team",
            source_native_id="second-7",
            metadata={"vendor": "two"},
        ),
    )

    assert first.alias.id != second.alias.id
    assert first.alias.source_id != second.alias.source_id
    assert first.alias.actor_id == second.alias.actor_id == actor.id
    assert first.alias.name == second.alias.name == "Falcon Team"
    assert count_rows(db_session, Actor) == actor_count
    assert count_rows(db_session, Alias) == 2
    with pytest.raises(AliasConflictError, match="different immutable source data"):
        service.resolve(
            db_session,
            AliasAssertion(
                source_id=first_source.id,
                name="falcon team",
                source_native_id="changed-id",
                metadata={"vendor": "changed"},
            ),
        )
    assert first.alias.name == "Falcon Team"
    assert first.alias.source_native_id == "first-1"
    assert first.alias.alias_metadata == {"vendor": "one"}
