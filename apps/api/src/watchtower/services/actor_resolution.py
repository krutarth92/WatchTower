"""Conservative, auditable actor and source-alias resolution."""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import (
    Actor,
    ActorAliasRule,
    ActorResolutionDecision,
    Alias,
    Evidence,
    ResolutionDecision,
    ResolutionMethod,
    Source,
)

CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class ActorResolutionError(ValueError):
    """Base error for controlled resolution failures."""


class AliasConflictError(ActorResolutionError):
    """A source-specific alias key was reused with different source data."""


class KnownAliasConflictError(ActorResolutionError):
    """A curated alias already names a different rule."""


class ResolutionReferenceError(ActorResolutionError):
    """A referenced source, actor, alias or evidence record does not exist."""


def normalize_actor_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    collapsed = " ".join(normalized.split()).casefold()
    if not collapsed or CONTROL_CHARACTER.search(collapsed):
        raise ActorResolutionError("Actor or alias name must contain safe visible text")
    if len(collapsed) > 255:
        raise ActorResolutionError("Normalized actor or alias name exceeds 255 characters")
    return collapsed


class AliasAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: UUID
    name: str = Field(min_length=1, max_length=255)
    source_native_id: str | None = Field(default=None, max_length=512)
    evidence_id: UUID | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Value must contain safe visible text")
        return cleaned

    @field_validator("source_native_id")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Value must contain safe visible text")
        return cleaned


class KnownAliasRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alias_name: str = Field(min_length=1, max_length=255)
    actor_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    confidence: int = Field(default=100, ge=0, le=100)
    evidence_id: UUID | None = None
    created_by: str = Field(min_length=1, max_length=255)

    @field_validator("alias_name", "reason", "created_by")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Value must contain safe visible text")
        return cleaned


class ManualResolutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alias_id: UUID
    actor_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=2000)
    confidence: int | None = Field(default=None, ge=0, le=100)
    evidence_id: UUID | None = None
    decided_by: str = Field(min_length=1, max_length=255)

    @field_validator("reason", "decided_by")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or CONTROL_CHARACTER.search(cleaned):
            raise ValueError("Value must contain safe visible text")
        return cleaned


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    actor_id: UUID
    canonical_name: str
    bases: tuple[str, ...]
    similarity: float | None = None

    def as_json(self) -> dict[str, JsonValue]:
        return {
            "actor_id": str(self.actor_id),
            "canonical_name": self.canonical_name,
            "bases": list(self.bases),
            "similarity": round(self.similarity, 6) if self.similarity is not None else None,
        }


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    alias: Alias
    decision: ActorResolutionDecision
    candidates: tuple[ResolutionCandidate, ...]
    repeated: bool


@dataclass(frozen=True, slots=True)
class RuleRegistrationResult:
    rule: ActorAliasRule
    duplicate: bool


@dataclass(slots=True)
class _CandidateAccumulator:
    actor: Actor
    bases: set[str] = field(default_factory=set)
    similarity: float | None = None


class ActorResolutionService:
    def __init__(self, similarity_threshold: float = 0.84) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        self._similarity_threshold = similarity_threshold

    def register_known_alias(
        self, session: Session, request: KnownAliasRuleInput
    ) -> RuleRegistrationResult:
        actor = self._require_actor(session, request.actor_id)
        self._require_evidence(session, request.evidence_id)
        normalized = normalize_actor_name(request.alias_name)
        existing = session.scalar(
            select(ActorAliasRule).where(ActorAliasRule.normalized_alias == normalized)
        )
        if existing is not None:
            if (
                existing.alias_name != request.alias_name
                or existing.actor_id != actor.id
                or existing.reason != request.reason
                or existing.confidence != request.confidence
                or existing.evidence_id != request.evidence_id
                or existing.created_by != request.created_by
                or not existing.active
            ):
                raise KnownAliasConflictError(
                    "Known alias already exists with different immutable details"
                )
            return RuleRegistrationResult(existing, True)
        rule = ActorAliasRule(
            alias_name=request.alias_name,
            normalized_alias=normalized,
            actor_id=actor.id,
            reason=request.reason,
            confidence=request.confidence,
            evidence_id=request.evidence_id,
            created_by=request.created_by,
        )
        session.add(rule)
        session.flush()
        return RuleRegistrationResult(rule, False)

    def resolve(self, session: Session, assertion: AliasAssertion) -> ResolutionResult:
        self._require_source(session, assertion.source_id)
        self._require_evidence(session, assertion.evidence_id)
        normalized = normalize_actor_name(assertion.name)
        alias, repeated_alias = self._get_or_create_alias(session, assertion, normalized)
        if alias.actor_id is not None:
            latest = self._latest_decision(session, alias.id)
            if latest is not None:
                return ResolutionResult(alias, latest, (), True)
            decision, repeated = self._record_decision(
                session,
                alias=alias,
                actor_id=alias.actor_id,
                previous_actor_id=alias.actor_id,
                evidence_id=assertion.evidence_id,
                decision=ResolutionDecision.AUTO_LINK,
                method=ResolutionMethod.EXISTING_LINK,
                reason="Existing source-specific actor link retained.",
                confidence=alias.confidence,
                decided_by="system",
                candidates=(),
            )
            return ResolutionResult(alias, decision, (), repeated or repeated_alias)

        exact, safe_methods, rule_confidence, rule_reasons = self._exact_candidates(session, alias)
        exact_candidates = self._freeze_candidates(exact)
        if len(exact) > 1:
            return self._unresolved(
                session,
                alias,
                assertion.evidence_id,
                ResolutionMethod.AMBIGUOUS_EXACT,
                "Exact evidence identifies multiple actors; manual review is required.",
                exact_candidates,
                repeated_alias,
            )
        if len(exact) == 1:
            actor_id = next(iter(exact))
            if actor_id in safe_methods:
                methods = safe_methods[actor_id]
                if ResolutionMethod.EXACT_ACTOR_NAME in methods:
                    method = ResolutionMethod.EXACT_ACTOR_NAME
                    confidence = 100
                    reason = "Alias exactly matches the canonical actor name."
                else:
                    method = ResolutionMethod.KNOWN_ALIAS
                    confidence = rule_confidence[actor_id]
                    reason = f"Curated known-alias rule: {rule_reasons[actor_id]}"
                alias.actor_id = actor_id
                alias.confidence = confidence
                decision, repeated = self._record_decision(
                    session,
                    alias=alias,
                    actor_id=actor_id,
                    previous_actor_id=None,
                    evidence_id=assertion.evidence_id,
                    decision=ResolutionDecision.AUTO_LINK,
                    method=method,
                    reason=reason,
                    confidence=confidence,
                    decided_by="system",
                    candidates=exact_candidates,
                )
                session.flush()
                return ResolutionResult(alias, decision, exact_candidates, repeated)
            return self._unresolved(
                session,
                alias,
                assertion.evidence_id,
                ResolutionMethod.EXACT_CANDIDATES,
                "Matching source aliases are candidates but cannot establish identity.",
                exact_candidates,
                repeated_alias,
            )

        similar = self._similar_candidates(session, normalized)
        if similar:
            return self._unresolved(
                session,
                alias,
                assertion.evidence_id,
                ResolutionMethod.SIMILARITY_CANDIDATES,
                "Similar actor names found; similarity cannot auto-link actors.",
                similar,
                repeated_alias,
            )
        return self._unresolved(
            session,
            alias,
            assertion.evidence_id,
            ResolutionMethod.NO_MATCH,
            "No deterministic actor match was found.",
            (),
            repeated_alias,
        )

    def correct_manually(
        self, session: Session, request: ManualResolutionInput
    ) -> ResolutionResult:
        alias = session.get(Alias, request.alias_id)
        if alias is None:
            raise ResolutionReferenceError("Alias does not exist")
        actor = self._require_actor(session, request.actor_id) if request.actor_id else None
        self._require_evidence(session, request.evidence_id)
        previous_actor_id = alias.actor_id
        decision_type = (
            ResolutionDecision.MANUAL_LINK if actor else ResolutionDecision.MANUAL_UNLINK
        )
        if previous_actor_id == request.actor_id:
            latest = self._latest_decision(session, alias.id)
            if (
                latest is not None
                and latest.decision is decision_type
                and latest.method is ResolutionMethod.MANUAL
                and latest.reason == request.reason
                and latest.confidence == (request.confidence if actor else None)
                and latest.evidence_id == request.evidence_id
                and latest.decided_by == request.decided_by
            ):
                return ResolutionResult(alias, latest, (), True)
        alias.actor_id = actor.id if actor else None
        alias.confidence = request.confidence if actor else None
        decision, repeated = self._record_decision(
            session,
            alias=alias,
            actor_id=actor.id if actor else None,
            previous_actor_id=previous_actor_id,
            evidence_id=request.evidence_id,
            decision=decision_type,
            method=ResolutionMethod.MANUAL,
            reason=request.reason,
            confidence=request.confidence if actor else None,
            decided_by=request.decided_by,
            candidates=(),
        )
        session.flush()
        return ResolutionResult(alias, decision, (), repeated)

    def _get_or_create_alias(
        self, session: Session, assertion: AliasAssertion, normalized: str
    ) -> tuple[Alias, bool]:
        existing = session.scalar(
            select(Alias).where(
                Alias.source_id == assertion.source_id,
                Alias.normalized_name == normalized,
            )
        )
        if existing is not None:
            if (
                existing.name != assertion.name
                or existing.source_native_id != assertion.source_native_id
                or existing.alias_metadata != assertion.metadata
            ):
                raise AliasConflictError(
                    "Source-specific alias exists with different immutable source data"
                )
            return existing, True
        alias = Alias(
            source_id=assertion.source_id,
            name=assertion.name,
            normalized_name=normalized,
            source_native_id=assertion.source_native_id,
            alias_metadata=assertion.metadata,
        )
        session.add(alias)
        session.flush()
        return alias, False

    def _exact_candidates(
        self, session: Session, alias: Alias
    ) -> tuple[
        dict[UUID, _CandidateAccumulator],
        dict[UUID, set[ResolutionMethod]],
        dict[UUID, int],
        dict[UUID, str],
    ]:
        candidates: dict[UUID, _CandidateAccumulator] = {}
        safe_methods: dict[UUID, set[ResolutionMethod]] = {}
        rule_confidence: dict[UUID, int] = {}
        rule_reasons: dict[UUID, str] = {}
        actors = session.scalars(
            select(Actor).where(Actor.normalized_name == alias.normalized_name)
        ).all()
        for actor in actors:
            self._add_candidate(candidates, actor, "exact canonical name")
            safe_methods.setdefault(actor.id, set()).add(ResolutionMethod.EXACT_ACTOR_NAME)
        rules = session.scalars(
            select(ActorAliasRule).where(
                ActorAliasRule.normalized_alias == alias.normalized_name,
                ActorAliasRule.active.is_(True),
            )
        ).all()
        for rule in rules:
            self._add_candidate(candidates, rule.actor, "curated known alias")
            safe_methods.setdefault(rule.actor_id, set()).add(ResolutionMethod.KNOWN_ALIAS)
            rule_confidence[rule.actor_id] = rule.confidence
            rule_reasons[rule.actor_id] = rule.reason
        linked_aliases = session.scalars(
            select(Alias).where(
                Alias.normalized_name == alias.normalized_name,
                Alias.actor_id.is_not(None),
                Alias.id != alias.id,
            )
        ).all()
        for linked in linked_aliases:
            assert linked.actor is not None
            self._add_candidate(candidates, linked.actor, "existing source alias assertion")
        return candidates, safe_methods, rule_confidence, rule_reasons

    def _similar_candidates(
        self, session: Session, normalized_alias: str
    ) -> tuple[ResolutionCandidate, ...]:
        candidates: dict[UUID, _CandidateAccumulator] = {}
        for actor in session.scalars(select(Actor).order_by(Actor.id)).all():
            score = SequenceMatcher(None, normalized_alias, actor.normalized_name).ratio()
            if score >= self._similarity_threshold:
                self._add_candidate(candidates, actor, "similar canonical name", score)
        for rule in session.scalars(
            select(ActorAliasRule).where(ActorAliasRule.active.is_(True))
        ).all():
            score = SequenceMatcher(None, normalized_alias, rule.normalized_alias).ratio()
            if score >= self._similarity_threshold:
                self._add_candidate(candidates, rule.actor, "similar curated alias", score)
        frozen = self._freeze_candidates(candidates)
        return tuple(
            sorted(
                frozen,
                key=lambda item: (-(item.similarity or 0.0), str(item.actor_id)),
            )[:10]
        )

    def _unresolved(
        self,
        session: Session,
        alias: Alias,
        evidence_id: UUID | None,
        method: ResolutionMethod,
        reason: str,
        candidates: tuple[ResolutionCandidate, ...],
        repeated_alias: bool,
    ) -> ResolutionResult:
        decision, repeated = self._record_decision(
            session,
            alias=alias,
            actor_id=None,
            previous_actor_id=None,
            evidence_id=evidence_id,
            decision=ResolutionDecision.UNRESOLVED,
            method=method,
            reason=reason,
            confidence=None,
            decided_by="system",
            candidates=candidates,
        )
        return ResolutionResult(alias, decision, candidates, repeated)

    def _record_decision(
        self,
        session: Session,
        *,
        alias: Alias,
        actor_id: UUID | None,
        previous_actor_id: UUID | None,
        evidence_id: UUID | None,
        decision: ResolutionDecision,
        method: ResolutionMethod,
        reason: str,
        confidence: int | None,
        decided_by: str,
        candidates: tuple[ResolutionCandidate, ...],
    ) -> tuple[ActorResolutionDecision, bool]:
        candidate_json = [candidate.as_json() for candidate in candidates]
        fingerprint_payload = {
            "actor_id": str(actor_id) if actor_id else None,
            "previous_actor_id": str(previous_actor_id) if previous_actor_id else None,
            "evidence_id": str(evidence_id) if evidence_id else None,
            "decision": decision.value,
            "method": method.value,
            "reason": reason,
            "confidence": confidence,
            "decided_by": decided_by,
            "candidates": candidate_json,
        }
        decision_hash = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        existing = session.scalar(
            select(ActorResolutionDecision).where(
                ActorResolutionDecision.alias_id == alias.id,
                ActorResolutionDecision.decision_hash == decision_hash,
            )
        )
        if existing is not None:
            return existing, True
        audit = ActorResolutionDecision(
            alias_id=alias.id,
            actor_id=actor_id,
            previous_actor_id=previous_actor_id,
            evidence_id=evidence_id,
            decision=decision,
            method=method,
            reason=reason,
            confidence=confidence,
            decided_by=decided_by,
            candidates=candidate_json,
            decision_hash=decision_hash,
        )
        session.add(audit)
        session.flush()
        return audit, False

    @staticmethod
    def _add_candidate(
        candidates: dict[UUID, _CandidateAccumulator],
        actor: Actor,
        basis: str,
        similarity: float | None = None,
    ) -> None:
        candidate = candidates.setdefault(actor.id, _CandidateAccumulator(actor))
        candidate.bases.add(basis)
        if similarity is not None:
            candidate.similarity = max(candidate.similarity or 0.0, similarity)

    @staticmethod
    def _freeze_candidates(
        candidates: dict[UUID, _CandidateAccumulator],
    ) -> tuple[ResolutionCandidate, ...]:
        return tuple(
            ResolutionCandidate(
                actor_id=item.actor.id,
                canonical_name=item.actor.canonical_name,
                bases=tuple(sorted(item.bases)),
                similarity=item.similarity,
            )
            for _, item in sorted(candidates.items(), key=lambda pair: str(pair[0]))
        )

    @staticmethod
    def _latest_decision(session: Session, alias_id: UUID) -> ActorResolutionDecision | None:
        return session.scalar(
            select(ActorResolutionDecision)
            .where(ActorResolutionDecision.alias_id == alias_id)
            .order_by(ActorResolutionDecision.sequence.desc())
            .limit(1)
        )

    @staticmethod
    def _require_source(session: Session, source_id: UUID) -> Source:
        source = session.get(Source, source_id)
        if source is None:
            raise ResolutionReferenceError("Source does not exist")
        return source

    @staticmethod
    def _require_actor(session: Session, actor_id: UUID) -> Actor:
        actor = session.get(Actor, actor_id)
        if actor is None:
            raise ResolutionReferenceError("Actor does not exist")
        return actor

    @staticmethod
    def _require_evidence(session: Session, evidence_id: UUID | None) -> Evidence | None:
        if evidence_id is None:
            return None
        evidence = session.get(Evidence, evidence_id)
        if evidence is None:
            raise ResolutionReferenceError("Evidence does not exist")
        return evidence
