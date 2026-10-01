"""Set-oriented actor read queries and cursor handling."""

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select, union
from sqlalchemy.orm import Session, joinedload, selectinload

from watchtower.api.errors import ApiError
from watchtower.api.v1.schemas import (
    ActorRead,
    ActorSearchRead,
    AliasRead,
    BehaviorRead,
    EvidenceRead,
    ObservationRead,
    SourceRead,
    TechniqueRead,
)
from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Evidence,
    IntelligenceType,
    Observation,
    Source,
    Technique,
    actor_observations,
    observation_behaviors,
    observation_evidence,
    observation_techniques,
)
from watchtower.services.actor_resolution import ActorResolutionError, normalize_actor_name

MAX_ALIASES = 100
MAX_ASSOCIATIONS = 200
MAX_EVIDENCE_REFERENCES = 200
MAX_SOURCE_REFERENCES = 100
SEARCH_LIMIT = 20
MAX_MATCHED_NAMES = 5
MAX_CURSOR_LENGTH = 1024
MAX_NESTED_ASSOCIATIONS = 50


@dataclass(frozen=True, slots=True)
class ObservationPage:
    items: list[ObservationRead]
    next_cursor: str | None


def source_read(source: Source) -> SourceRead:
    return SourceRead(id=source.id, name=source.name, kind=source.kind, base_url=source.base_url)


def actor_read(actor: Actor) -> ActorRead:
    return ActorRead(
        id=actor.id,
        canonical_name=actor.canonical_name,
        description=actor.description,
    )


def alias_read(alias: Alias) -> AliasRead:
    return AliasRead(
        id=alias.id,
        name=alias.name,
        source_native_id=alias.source_native_id,
        confidence=alias.confidence,
        source=source_read(alias.source),
    )


def behavior_read(behavior: Behavior) -> BehaviorRead:
    return BehaviorRead(
        id=behavior.id,
        name=behavior.name,
        description=behavior.description,
    )


def technique_read(technique: Technique) -> TechniqueRead:
    return TechniqueRead(
        id=technique.id,
        external_id=technique.external_id,
        name=technique.name,
        description=technique.description,
        source=source_read(technique.source),
    )


def evidence_read(evidence: Evidence) -> EvidenceRead:
    return EvidenceRead(
        id=evidence.id,
        citation=evidence.citation,
        excerpt=evidence.excerpt,
        locator=evidence.locator,
        captured_at=evidence.captured_at,
        confidence=evidence.confidence,
        origin=evidence.origin,
        raw_evidence_id=evidence.raw_evidence_id,
        source=source_read(evidence.source),
    )


def observation_read(observation: Observation) -> ObservationRead:
    evidence = sorted(observation.evidence, key=lambda item: (item.citation, str(item.id)))
    behaviors = sorted(observation.behaviors, key=lambda item: (item.name, str(item.id)))
    techniques = sorted(
        observation.techniques,
        key=lambda item: (item.external_id, str(item.id)),
    )
    return ObservationRead(
        id=observation.id,
        source_native_id=observation.source_native_id,
        title=observation.title,
        summary=observation.summary,
        observed_at=observation.observed_at,
        first_seen=observation.first_seen,
        last_seen=observation.last_seen,
        confidence=observation.confidence,
        intelligence_type=observation.intelligence_type,
        origin=observation.origin,
        raw_evidence_id=observation.raw_evidence_id,
        source=source_read(observation.source),
        evidence=[evidence_read(item) for item in evidence[:MAX_NESTED_ASSOCIATIONS]],
        behaviors=[behavior_read(item) for item in behaviors[:MAX_NESTED_ASSOCIATIONS]],
        techniques=[technique_read(item) for item in techniques[:MAX_NESTED_ASSOCIATIONS]],
        evidence_truncated=len(evidence) > MAX_NESTED_ASSOCIATIONS,
        behaviors_truncated=len(behaviors) > MAX_NESTED_ASSOCIATIONS,
        techniques_truncated=len(techniques) > MAX_NESTED_ASSOCIATIONS,
    )


class ActorReadService:
    def require_actor(self, session: Session, actor_id: UUID) -> Actor:
        actor = session.get(Actor, actor_id)
        if actor is None:
            raise ApiError(404, "actor_not_found", "Actor was not found.")
        return actor

    def search(self, session: Session, query: str) -> list[ActorSearchRead]:
        try:
            normalized = normalize_actor_name(query)
        except ActorResolutionError:
            raise ApiError(
                422,
                "validation_error",
                "The actor search query must contain safe visible text.",
            ) from None
        canonical_contains = Actor.normalized_name.contains(normalized, autoescape=True)
        alias_contains = Alias.normalized_name.contains(normalized, autoescape=True)
        match_rank = case(
            (Actor.normalized_name == normalized, 0),
            (Alias.normalized_name == normalized, 1),
            (canonical_contains, 2),
            else_=3,
        )
        ranked = session.execute(
            select(Actor.id, func.min(match_rank).label("match_rank"))
            .outerjoin(Alias, Alias.actor_id == Actor.id)
            .where(or_(canonical_contains, alias_contains))
            .group_by(Actor.id)
            .order_by("match_rank", Actor.normalized_name, Actor.id)
            .limit(SEARCH_LIMIT)
        ).all()
        actor_ids = [row.id for row in ranked]
        if not actor_ids:
            return []
        actors = {
            actor.id: actor
            for actor in session.scalars(select(Actor).where(Actor.id.in_(actor_ids))).all()
        }
        alias_rank = func.row_number().over(
            partition_by=Alias.actor_id,
            order_by=(Alias.normalized_name, Alias.id),
        )
        matching_aliases = (
            select(
                Alias.actor_id.label("actor_id"),
                Alias.name.label("name"),
                alias_rank.label("alias_rank"),
            )
            .where(Alias.actor_id.in_(actor_ids), alias_contains)
            .subquery()
        )
        alias_rows = session.execute(
            select(matching_aliases.c.actor_id, matching_aliases.c.name)
            .where(matching_aliases.c.alias_rank <= MAX_MATCHED_NAMES)
            .order_by(matching_aliases.c.actor_id, matching_aliases.c.alias_rank)
        ).all()
        matched_aliases: dict[UUID, list[str]] = {}
        for actor_id, name in alias_rows:
            if actor_id is None:
                continue
            names = matched_aliases.setdefault(actor_id, [])
            if name not in names and len(names) < MAX_MATCHED_NAMES:
                names.append(name)
        results: list[ActorSearchRead] = []
        for actor_id in actor_ids:
            actor = actors[actor_id]
            names = matched_aliases.get(actor_id, []).copy()
            if normalized in actor.normalized_name and actor.canonical_name not in names:
                names.insert(0, actor.canonical_name)
            results.append(
                ActorSearchRead(
                    id=actor.id,
                    canonical_name=actor.canonical_name,
                    description=actor.description,
                    matched_names=names[:MAX_MATCHED_NAMES],
                )
            )
        return results

    def aliases(self, session: Session, actor_id: UUID) -> tuple[list[AliasRead], bool]:
        self.require_actor(session, actor_id)
        aliases = session.scalars(
            select(Alias)
            .where(Alias.actor_id == actor_id)
            .options(joinedload(Alias.source))
            .order_by(Alias.normalized_name, Alias.id)
            .limit(MAX_ALIASES + 1)
        ).all()
        return [alias_read(item) for item in aliases[:MAX_ALIASES]], len(aliases) > MAX_ALIASES

    def observations(
        self,
        session: Session,
        actor_id: UUID,
        *,
        limit: int,
        cursor: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        intelligence_type: IntelligenceType | None,
    ) -> ObservationPage:
        self.require_actor(session, actor_id)
        scope = self._cursor_scope(actor_id, date_from, date_to, intelligence_type)
        cursor_values = self._decode_cursor(cursor, scope) if cursor else None
        statement: Select[tuple[Observation]] = (
            select(Observation)
            .join(actor_observations, actor_observations.c.observation_id == Observation.id)
            .where(actor_observations.c.actor_id == actor_id)
            .options(
                joinedload(Observation.source),
                selectinload(Observation.evidence).joinedload(Evidence.source),
                selectinload(Observation.behaviors),
                selectinload(Observation.techniques).joinedload(Technique.source),
            )
        )
        if date_from is not None:
            statement = statement.where(Observation.observed_at >= date_from)
        if date_to is not None:
            statement = statement.where(Observation.observed_at <= date_to)
        if intelligence_type is not None:
            statement = statement.where(Observation.intelligence_type == intelligence_type)
        if cursor_values is not None:
            observed_at, observation_id = cursor_values
            statement = statement.where(
                or_(
                    Observation.observed_at < observed_at,
                    and_(
                        Observation.observed_at == observed_at,
                        Observation.id < observation_id,
                    ),
                )
            )
        rows = session.scalars(
            statement.order_by(Observation.observed_at.desc(), Observation.id.desc()).limit(
                limit + 1
            )
        ).all()
        page_rows = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page_rows:
            last = page_rows[-1]
            next_cursor = self._encode_cursor(last.observed_at, last.id, scope)
        return ObservationPage(
            items=[observation_read(item) for item in page_rows],
            next_cursor=next_cursor,
        )

    def associations(
        self, session: Session, actor_id: UUID
    ) -> tuple[list[BehaviorRead], bool, list[TechniqueRead], bool]:
        self.require_actor(session, actor_id)
        behaviors = session.scalars(
            select(Behavior)
            .join(
                observation_behaviors,
                observation_behaviors.c.behavior_id == Behavior.id,
            )
            .join(
                actor_observations,
                actor_observations.c.observation_id == observation_behaviors.c.observation_id,
            )
            .where(actor_observations.c.actor_id == actor_id)
            .distinct()
            .order_by(Behavior.normalized_name, Behavior.id)
            .limit(MAX_ASSOCIATIONS + 1)
        ).all()
        techniques = session.scalars(
            select(Technique)
            .join(
                observation_techniques,
                observation_techniques.c.technique_id == Technique.id,
            )
            .join(
                actor_observations,
                actor_observations.c.observation_id == observation_techniques.c.observation_id,
            )
            .where(actor_observations.c.actor_id == actor_id)
            .options(joinedload(Technique.source))
            .distinct()
            .order_by(Technique.external_id, Technique.id)
            .limit(MAX_ASSOCIATIONS + 1)
        ).all()
        return (
            [behavior_read(item) for item in behaviors[:MAX_ASSOCIATIONS]],
            len(behaviors) > MAX_ASSOCIATIONS,
            [technique_read(item) for item in techniques[:MAX_ASSOCIATIONS]],
            len(techniques) > MAX_ASSOCIATIONS,
        )

    def references(
        self, session: Session, actor_id: UUID
    ) -> tuple[list[SourceRead], bool, list[EvidenceRead], bool]:
        self.require_actor(session, actor_id)
        observation_source_ids = (
            select(Observation.source_id)
            .join(actor_observations, actor_observations.c.observation_id == Observation.id)
            .where(actor_observations.c.actor_id == actor_id)
        )
        evidence_source_ids = (
            select(Evidence.source_id)
            .join(
                observation_evidence,
                observation_evidence.c.evidence_id == Evidence.id,
            )
            .join(
                actor_observations,
                actor_observations.c.observation_id == observation_evidence.c.observation_id,
            )
            .where(actor_observations.c.actor_id == actor_id)
        )
        all_source_ids = union(observation_source_ids, evidence_source_ids)
        sources = session.scalars(
            select(Source)
            .where(Source.id.in_(all_source_ids))
            .order_by(Source.name, Source.id)
            .limit(MAX_SOURCE_REFERENCES + 1)
        ).all()
        evidence = session.scalars(
            select(Evidence)
            .join(
                observation_evidence,
                observation_evidence.c.evidence_id == Evidence.id,
            )
            .join(
                actor_observations,
                actor_observations.c.observation_id == observation_evidence.c.observation_id,
            )
            .where(actor_observations.c.actor_id == actor_id)
            .options(joinedload(Evidence.source))
            .distinct()
            .order_by(Evidence.citation, Evidence.id)
            .limit(MAX_EVIDENCE_REFERENCES + 1)
        ).all()
        return (
            [source_read(item) for item in sources[:MAX_SOURCE_REFERENCES]],
            len(sources) > MAX_SOURCE_REFERENCES,
            [evidence_read(item) for item in evidence[:MAX_EVIDENCE_REFERENCES]],
            len(evidence) > MAX_EVIDENCE_REFERENCES,
        )

    @staticmethod
    def _cursor_scope(
        actor_id: UUID,
        date_from: datetime | None,
        date_to: datetime | None,
        intelligence_type: IntelligenceType | None,
    ) -> str:
        scope = {
            "actor_id": str(actor_id),
            "date_from": _datetime_text(date_from),
            "date_to": _datetime_text(date_to),
            "intelligence_type": intelligence_type.value if intelligence_type else None,
        }
        encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _encode_cursor(observed_at: datetime, observation_id: UUID, scope: str) -> str:
        payload = json.dumps(
            {
                "v": 1,
                "observed_at": _datetime_text(observed_at),
                "observation_id": str(observation_id),
                "scope": scope,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        checksum = hashlib.sha256(payload).hexdigest()
        token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        return f"{token}.{checksum}"

    @staticmethod
    def _decode_cursor(cursor: str, expected_scope: str) -> tuple[datetime, UUID]:
        try:
            if len(cursor) > MAX_CURSOR_LENGTH:
                raise ValueError
            token, checksum = cursor.split(".", maxsplit=1)
            padding = "=" * (-len(token) % 4)
            payload = base64.urlsafe_b64decode(f"{token}{padding}")
            if hashlib.sha256(payload).hexdigest() != checksum:
                raise ValueError
            values = json.loads(payload)
            if set(values) != {"v", "observed_at", "observation_id", "scope"}:
                raise ValueError
            if values["v"] != 1 or values["scope"] != expected_scope:
                raise ValueError
            observed_at = datetime.fromisoformat(values["observed_at"])
            observation_id = UUID(values["observation_id"])
            if observed_at.tzinfo is None:
                raise ValueError
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            raise ApiError(
                422,
                "validation_error",
                "The pagination cursor is invalid for this request.",
            ) from None
        return observed_at, observation_id


def _datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()
