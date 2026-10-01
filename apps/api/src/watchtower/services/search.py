"""Deterministic PostgreSQL full-text search across approved V1 entities."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    String,
    Text,
    Uuid,
    and_,
    case,
    cast,
    exists,
    func,
    literal,
    literal_column,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from watchtower.api.v1.search_schemas import (
    SearchEntityType,
    SearchMatchKind,
    SearchResultRead,
)
from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Campaign,
    IntelligenceType,
    Observation,
    Source,
    Technique,
    actor_observations,
    observation_behaviors,
)
from watchtower.services.actor_resolution import normalize_actor_name

CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
ENGLISH = literal_column("'english'::regconfig")
ENTITY_ORDER = {
    SearchEntityType.ACTOR: 0,
    SearchEntityType.ALIAS: 1,
    SearchEntityType.CAMPAIGN: 2,
    SearchEntityType.BEHAVIOR: 3,
    SearchEntityType.TECHNIQUE: 4,
    SearchEntityType.OBSERVATION: 5,
    SearchEntityType.SOURCE: 6,
}

SEARCH_DOCUMENTS = {
    SearchEntityType.SOURCE: (
        "setweight(to_tsvector('english'::regconfig, coalesce(sources.name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(sources.kind, '') || ' ' || "
        "coalesce(sources.policy_notes, '') || ' ' || coalesce(sources.license_name, '')), "
        "'B') || setweight(to_tsvector('english'::regconfig, "
        "coalesce(sources.metadata::text, '')), 'D')"
    ),
    SearchEntityType.ACTOR: (
        "setweight(to_tsvector('english'::regconfig, coalesce(actors.canonical_name, '')), 'A') "
        "|| setweight(to_tsvector('english'::regconfig, coalesce(actors.description, '')), 'B') "
        "|| setweight(to_tsvector('english'::regconfig, coalesce(actors.metadata::text, '')), 'D')"
    ),
    SearchEntityType.ALIAS: (
        "setweight(to_tsvector('english'::regconfig, coalesce(aliases.name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(aliases.source_native_id, '')), "
        "'C') || setweight(to_tsvector('english'::regconfig, "
        "coalesce(aliases.metadata::text, '')), 'D')"
    ),
    SearchEntityType.CAMPAIGN: (
        "setweight(to_tsvector('english'::regconfig, coalesce(campaigns.name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(campaigns.description, '')), 'B') "
        "|| setweight(to_tsvector('english'::regconfig, "
        "coalesce(campaigns.metadata::text, '')), 'D')"
    ),
    SearchEntityType.BEHAVIOR: (
        "setweight(to_tsvector('english'::regconfig, coalesce(behaviors.name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(behaviors.description, '')), 'B') "
        "|| setweight(to_tsvector('english'::regconfig, "
        "coalesce(behaviors.metadata::text, '')), 'D')"
    ),
    SearchEntityType.TECHNIQUE: (
        "setweight(to_tsvector('english'::regconfig, coalesce(techniques.external_id, '') || "
        "' ' || coalesce(techniques.name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(techniques.description, '')), "
        "'B') || setweight(to_tsvector('english'::regconfig, "
        "coalesce(techniques.metadata::text, '')), 'D')"
    ),
    SearchEntityType.OBSERVATION: ("observations.search_document"),
}


class SearchQueryError(ValueError):
    """The supplied search query cannot be safely evaluated."""


class SearchService:
    def search(
        self,
        session: Session,
        query_text: str,
        *,
        entity_types: set[SearchEntityType] | None = None,
        source_id: UUID | None = None,
        intelligence_type: IntelligenceType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 25,
    ) -> tuple[str, list[SearchResultRead]]:
        clean_query = self._clean_query(query_text)
        normalized_query = normalize_actor_name(clean_query)
        selected = entity_types or set(SearchEntityType)
        tsquery = func.websearch_to_tsquery(ENGLISH, clean_query)
        restrict_to_intelligence = any(
            value is not None for value in (intelligence_type, date_from, date_to)
        )
        branches: list[Select[Any]] = []

        if SearchEntityType.ACTOR in selected and not restrict_to_intelligence:
            source_condition = None
            if source_id is not None:
                source_condition = or_(
                    exists(
                        select(literal(1)).where(
                            Alias.actor_id == Actor.id,
                            Alias.source_id == source_id,
                        )
                    ),
                    exists(
                        select(literal(1))
                        .select_from(
                            actor_observations.join(
                                Observation,
                                Observation.id == actor_observations.c.observation_id,
                            )
                        )
                        .where(
                            actor_observations.c.actor_id == Actor.id,
                            Observation.source_id == source_id,
                        )
                    ),
                )
            branches.append(
                self._branch(
                    SearchEntityType.ACTOR,
                    Actor.id,
                    Actor.canonical_name,
                    Actor.description,
                    exact=Actor.normalized_name == normalized_query,
                    tsquery=tsquery,
                    source_condition=source_condition,
                )
            )

        if SearchEntityType.ALIAS in selected and not restrict_to_intelligence:
            branches.append(
                self._branch(
                    SearchEntityType.ALIAS,
                    Alias.id,
                    Alias.name,
                    literal("Source-preserved actor alias"),
                    exact=Alias.normalized_name == normalized_query,
                    tsquery=tsquery,
                    source_id=Alias.source_id,
                    actor_id=Alias.actor_id,
                    source_condition=(
                        Alias.source_id == source_id if source_id is not None else None
                    ),
                )
            )

        if SearchEntityType.CAMPAIGN in selected:
            campaign_filters = []
            if source_id is not None:
                campaign_filters.append(Campaign.source_id == source_id)
            if intelligence_type is not None:
                campaign_filters.append(Campaign.intelligence_type == intelligence_type)
            if date_from is not None:
                campaign_filters.append(
                    or_(Campaign.last_seen.is_(None), Campaign.last_seen >= date_from)
                )
            if date_to is not None:
                campaign_filters.append(
                    or_(Campaign.first_seen.is_(None), Campaign.first_seen <= date_to)
                )
            branches.append(
                self._branch(
                    SearchEntityType.CAMPAIGN,
                    Campaign.id,
                    Campaign.name,
                    Campaign.description,
                    exact=Campaign.normalized_name == normalized_query,
                    tsquery=tsquery,
                    source_id=Campaign.source_id,
                    observed_at=Campaign.first_seen,
                    intelligence_type=Campaign.intelligence_type,
                    origin=Campaign.origin,
                    source_condition=and_(*campaign_filters) if campaign_filters else None,
                )
            )

        if SearchEntityType.BEHAVIOR in selected and not restrict_to_intelligence:
            behavior_source = None
            if source_id is not None:
                behavior_source = exists(
                    select(literal(1))
                    .select_from(
                        observation_behaviors.join(
                            Observation,
                            Observation.id == observation_behaviors.c.observation_id,
                        )
                    )
                    .where(
                        observation_behaviors.c.behavior_id == Behavior.id,
                        Observation.source_id == source_id,
                    )
                )
            branches.append(
                self._branch(
                    SearchEntityType.BEHAVIOR,
                    Behavior.id,
                    Behavior.name,
                    Behavior.description,
                    exact=Behavior.normalized_name == normalized_query,
                    tsquery=tsquery,
                    source_condition=behavior_source,
                )
            )

        if SearchEntityType.TECHNIQUE in selected and not restrict_to_intelligence:
            technique_exact = or_(
                func.lower(Technique.external_id) == clean_query.casefold(),
                func.lower(Technique.name) == clean_query.casefold(),
            )
            branches.append(
                self._branch(
                    SearchEntityType.TECHNIQUE,
                    Technique.id,
                    Technique.name,
                    Technique.description,
                    exact=technique_exact,
                    tsquery=tsquery,
                    source_id=Technique.source_id,
                    external_id=Technique.external_id,
                    source_condition=(
                        Technique.source_id == source_id if source_id is not None else None
                    ),
                )
            )

        if SearchEntityType.OBSERVATION in selected:
            observation_filters = []
            if source_id is not None:
                observation_filters.append(Observation.source_id == source_id)
            if intelligence_type is not None:
                observation_filters.append(Observation.intelligence_type == intelligence_type)
            if date_from is not None:
                observation_filters.append(Observation.observed_at >= date_from)
            if date_to is not None:
                observation_filters.append(Observation.observed_at <= date_to)
            branches.append(
                self._branch(
                    SearchEntityType.OBSERVATION,
                    Observation.id,
                    Observation.title,
                    Observation.summary,
                    exact=func.lower(Observation.title) == clean_query.casefold(),
                    tsquery=tsquery,
                    source_id=Observation.source_id,
                    observed_at=Observation.observed_at,
                    intelligence_type=Observation.intelligence_type,
                    origin=Observation.origin,
                    source_condition=(and_(*observation_filters) if observation_filters else None),
                )
            )

        if SearchEntityType.SOURCE in selected and not restrict_to_intelligence:
            branches.append(
                self._branch(
                    SearchEntityType.SOURCE,
                    Source.id,
                    Source.name,
                    Source.policy_notes,
                    exact=func.lower(Source.name) == clean_query.casefold(),
                    tsquery=tsquery,
                    source_id=Source.id,
                    source_condition=Source.id == source_id if source_id is not None else None,
                )
            )

        if not branches:
            return clean_query, []
        combined = union_all(*branches).subquery("search_results")
        entity_order = case(
            *[
                (combined.c.entity_type == entity.value, order)
                for entity, order in ENTITY_ORDER.items()
            ],
            else_=len(ENTITY_ORDER),
        )
        statement = (
            select(combined)
            .order_by(
                combined.c.score.desc(),
                entity_order,
                func.lower(combined.c.title),
                combined.c.id,
            )
            .limit(limit)
        )
        rows = session.execute(statement).mappings().all()
        return clean_query, [SearchResultRead.model_validate(dict(row)) for row in rows]

    @staticmethod
    def _branch(
        entity_type: SearchEntityType,
        entity_id: Any,
        title: Any,
        summary: Any,
        *,
        exact: Any,
        tsquery: Any,
        source_id: Any | None = None,
        actor_id: Any | None = None,
        external_id: Any | None = None,
        observed_at: Any | None = None,
        intelligence_type: Any | None = None,
        origin: Any | None = None,
        source_condition: Any | None = None,
    ) -> Select[Any]:
        document = literal_column(f"({SEARCH_DOCUMENTS[entity_type]})")
        full_text_match = document.op("@@")(tsquery)
        score = cast(
            case((exact, literal(100.0)), else_=literal(0.0))
            + func.ts_rank_cd(document, tsquery, 32),
            Float,
        )
        statement = select(
            cast(literal(entity_type.value), String).label("entity_type"),
            cast(entity_id, Uuid).label("id"),
            cast(title, String).label("title"),
            cast(func.left(cast(summary, Text), 500), Text).label("summary"),
            cast(source_id if source_id is not None else null(), Uuid).label("source_id"),
            cast(actor_id if actor_id is not None else null(), Uuid).label("actor_id"),
            cast(external_id if external_id is not None else null(), String).label("external_id"),
            cast(
                observed_at if observed_at is not None else null(),
                DateTime(timezone=True),
            ).label("observed_at"),
            cast(
                intelligence_type if intelligence_type is not None else null(),
                String,
            ).label("intelligence_type"),
            cast(origin if origin is not None else null(), String).label("origin"),
            cast(
                case(
                    (exact, literal(SearchMatchKind.EXACT.value)),
                    else_=literal(SearchMatchKind.FULL_TEXT.value),
                ),
                String,
            ).label("match_kind"),
            score.label("score"),
        ).where(or_(exact, full_text_match))
        if source_condition is not None:
            statement = statement.where(source_condition)
        return statement

    @staticmethod
    def _clean_query(value: str) -> str:
        cleaned = " ".join(value.split())
        if not 2 <= len(cleaned) <= 200 or CONTROL_CHARACTER.search(value):
            raise SearchQueryError("Search query must contain 2–200 safe characters")
        return cleaned
