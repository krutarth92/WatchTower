"""Deterministic PostgreSQL full-text search across approved V1 entities."""

import base64
import hashlib
import hmac
import json
import math
import re
from collections.abc import Sequence
from datetime import UTC, datetime
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
    ActorDiscoveryRead,
    ActorDiscoveryResponse,
    RelatedActorRead,
    SearchEntityType,
    SearchMatchKind,
    SearchResultRead,
)
from watchtower.db.models import (
    Actor,
    Alias,
    Behavior,
    Campaign,
    Indicator,
    IntelligenceType,
    Observation,
    PublicationState,
    Source,
    Technique,
    Vulnerability,
    actor_indicators,
    actor_observations,
    actor_vulnerabilities,
    observation_behaviors,
)
from watchtower.services.actor_resolution import normalize_actor_name

CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
ENGLISH = literal_column("'english'::regconfig")
ENTITY_ORDER = {
    SearchEntityType.INDICATOR: 0,
    SearchEntityType.VULNERABILITY: 1,
    SearchEntityType.ACTOR: 2,
    SearchEntityType.ALIAS: 3,
    SearchEntityType.CAMPAIGN: 4,
    SearchEntityType.BEHAVIOR: 5,
    SearchEntityType.TECHNIQUE: 6,
    SearchEntityType.OBSERVATION: 7,
    SearchEntityType.SOURCE: 8,
}
MAX_CURSOR_LENGTH = 4096

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
    SearchEntityType.INDICATOR: ("indicators.search_document"),
    SearchEntityType.VULNERABILITY: ("vulnerabilities.search_document"),
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
        cursor: str | None = None,
    ) -> tuple[str, list[SearchResultRead], str | None]:
        clean_query = self._clean_query(query_text)
        normalized_query = normalize_actor_name(clean_query)
        selected = entity_types or set(SearchEntityType)
        cursor_scope = self._cursor_scope(
            clean_query,
            selected,
            source_id,
            intelligence_type,
            date_from,
            date_to,
        )
        cursor_values = self._decode_cursor(cursor, cursor_scope) if cursor else None
        tsquery = func.websearch_to_tsquery(ENGLISH, clean_query)
        restrict_to_intelligence = any(
            value is not None for value in (intelligence_type, date_from, date_to)
        )
        branches: list[Select[Any]] = []

        if SearchEntityType.ACTOR in selected and not restrict_to_intelligence:
            actor_filters = [Actor.publication_state == PublicationState.PUBLISHED]
            if source_id is not None:
                actor_filters.append(
                    or_(
                        exists(
                            select(literal(1)).where(
                                Alias.actor_id == Actor.id,
                                Alias.source_id == source_id,
                                Alias.publication_state == PublicationState.PUBLISHED,
                                Alias.source.has(
                                    Source.publication_state == PublicationState.PUBLISHED
                                ),
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
                                Observation.publication_state == PublicationState.PUBLISHED,
                                Observation.source.has(
                                    Source.publication_state == PublicationState.PUBLISHED
                                ),
                            )
                        ),
                    )
                )
            branches.append(
                self._branch(
                    SearchEntityType.ACTOR,
                    Actor.id,
                    Actor.canonical_name,
                    Actor.description,
                    exact=Actor.normalized_name == normalized_query,
                    tsquery=tsquery,
                    source_condition=and_(*actor_filters),
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
                    source_condition=and_(
                        Alias.publication_state == PublicationState.PUBLISHED,
                        Alias.actor.has(Actor.publication_state == PublicationState.PUBLISHED),
                        Alias.source.has(Source.publication_state == PublicationState.PUBLISHED),
                        Alias.source_id == source_id if source_id is not None else literal(True),
                    ),
                )
            )

        if SearchEntityType.CAMPAIGN in selected:
            campaign_filters = [
                Campaign.publication_state == PublicationState.PUBLISHED,
                Campaign.source.has(Source.publication_state == PublicationState.PUBLISHED),
            ]
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
            behavior_filters = [Behavior.publication_state == PublicationState.PUBLISHED]
            if source_id is not None:
                behavior_filters.append(
                    exists(
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
                            Observation.publication_state == PublicationState.PUBLISHED,
                            Observation.source.has(
                                Source.publication_state == PublicationState.PUBLISHED
                            ),
                        )
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
                    source_condition=and_(*behavior_filters),
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
                    source_condition=and_(
                        Technique.publication_state == PublicationState.PUBLISHED,
                        Technique.source.has(
                            Source.publication_state == PublicationState.PUBLISHED
                        ),
                        Technique.source_id == source_id
                        if source_id is not None
                        else literal(True),
                    ),
                )
            )

        if SearchEntityType.INDICATOR in selected:
            indicator_filters = [
                Indicator.publication_state == PublicationState.PUBLISHED,
                Indicator.source.has(Source.publication_state == PublicationState.PUBLISHED),
            ]
            if source_id is not None:
                indicator_filters.append(Indicator.source_id == source_id)
            if intelligence_type is not None:
                indicator_filters.append(Indicator.intelligence_type == intelligence_type)
            if date_from is not None:
                indicator_filters.append(
                    or_(Indicator.last_seen.is_(None), Indicator.last_seen >= date_from)
                )
            if date_to is not None:
                indicator_filters.append(
                    or_(Indicator.first_seen.is_(None), Indicator.first_seen <= date_to)
                )
            branches.append(
                self._branch(
                    SearchEntityType.INDICATOR,
                    Indicator.id,
                    Indicator.value,
                    Indicator.description,
                    exact=func.lower(Indicator.normalized_value) == clean_query.casefold(),
                    tsquery=tsquery,
                    source_id=Indicator.source_id,
                    observed_at=Indicator.last_seen,
                    intelligence_type=Indicator.intelligence_type,
                    origin=Indicator.origin,
                    indicator_type=Indicator.indicator_type,
                    indicator_value=Indicator.value,
                    source_condition=and_(*indicator_filters),
                )
            )

        if SearchEntityType.VULNERABILITY in selected:
            vulnerability_filters = [
                Vulnerability.publication_state == PublicationState.PUBLISHED,
                Vulnerability.source.has(Source.publication_state == PublicationState.PUBLISHED),
            ]
            if source_id is not None:
                vulnerability_filters.append(Vulnerability.source_id == source_id)
            if intelligence_type is not None:
                vulnerability_filters.append(Vulnerability.intelligence_type == intelligence_type)
            if date_from is not None:
                vulnerability_filters.append(
                    or_(
                        Vulnerability.published_at.is_(None),
                        Vulnerability.published_at >= date_from,
                    )
                )
            if date_to is not None:
                vulnerability_filters.append(
                    or_(
                        Vulnerability.published_at.is_(None),
                        Vulnerability.published_at <= date_to,
                    )
                )
            branches.append(
                self._branch(
                    SearchEntityType.VULNERABILITY,
                    Vulnerability.id,
                    Vulnerability.cve_id,
                    Vulnerability.description,
                    exact=func.lower(Vulnerability.cve_id) == clean_query.casefold(),
                    tsquery=tsquery,
                    source_id=Vulnerability.source_id,
                    external_id=Vulnerability.cve_id,
                    observed_at=Vulnerability.published_at,
                    intelligence_type=Vulnerability.intelligence_type,
                    origin=Vulnerability.origin,
                    severity=Vulnerability.severity,
                    cvss_score=Vulnerability.cvss_score,
                    source_condition=and_(*vulnerability_filters),
                )
            )

        if SearchEntityType.OBSERVATION in selected:
            observation_filters = [
                Observation.publication_state == PublicationState.PUBLISHED,
                Observation.source.has(Source.publication_state == PublicationState.PUBLISHED),
            ]
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
                    source_condition=and_(
                        Source.publication_state == PublicationState.PUBLISHED,
                        Source.id == source_id if source_id is not None else literal(True),
                    ),
                )
            )

        if not branches:
            return clean_query, [], None
        combined = union_all(*branches).subquery("search_results")
        entity_order = case(
            *[
                (combined.c.entity_type == entity.value, order)
                for entity, order in ENTITY_ORDER.items()
            ],
            else_=len(ENTITY_ORDER),
        )
        sort_title = func.lower(combined.c.title)
        statement = select(
            combined,
            entity_order.label("_entity_order"),
            sort_title.label("_sort_title"),
        )
        if cursor_values is not None:
            cursor_score, cursor_entity_order, cursor_title, cursor_id = cursor_values
            statement = statement.where(
                or_(
                    combined.c.score < cursor_score,
                    and_(
                        combined.c.score == cursor_score,
                        entity_order > cursor_entity_order,
                    ),
                    and_(
                        combined.c.score == cursor_score,
                        entity_order == cursor_entity_order,
                        sort_title > cursor_title,
                    ),
                    and_(
                        combined.c.score == cursor_score,
                        entity_order == cursor_entity_order,
                        sort_title == cursor_title,
                        combined.c.id > cursor_id,
                    ),
                )
            )
        statement = statement.order_by(
            combined.c.score.desc(),
            entity_order,
            sort_title,
            combined.c.id,
        ).limit(limit + 1)
        rows = session.execute(statement).mappings().all()
        page_rows = rows[:limit]
        next_cursor = None
        if len(rows) > limit and page_rows:
            last = page_rows[-1]
            next_cursor = self._encode_cursor(
                float(last["score"]),
                int(last["_entity_order"]),
                str(last["_sort_title"]),
                UUID(str(last["id"])),
                cursor_scope,
            )
        related = self._related_actors(session, page_rows)
        records: list[SearchResultRead] = []
        for row in page_rows:
            values = dict(row)
            actors = related.get((str(row["entity_type"]), UUID(str(row["id"]))), [])
            values["related_actors"] = actors[:3]
            values["related_actors_truncated"] = len(actors) > 3
            records.append(SearchResultRead.model_validate(values))
        return clean_query, records, next_cursor

    def discover_actors(self, session: Session, *, limit: int = 12) -> ActorDiscoveryResponse:
        if not 1 <= limit <= 12:
            raise SearchQueryError("Actor discovery limit must be between 1 and 12.")
        recent_limit = max(1, math.ceil(limit / 2))
        popular_limit = max(0, limit - recent_limit)
        observation_count = (
            select(func.count())
            .select_from(
                actor_observations.join(
                    Observation, Observation.id == actor_observations.c.observation_id
                )
            )
            .where(
                actor_observations.c.actor_id == Actor.id,
                Observation.publication_state == PublicationState.PUBLISHED,
                Observation.source.has(Source.publication_state == PublicationState.PUBLISHED),
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        latest_observed_at = (
            select(func.max(Observation.observed_at))
            .select_from(
                actor_observations.join(
                    Observation, Observation.id == actor_observations.c.observation_id
                )
            )
            .where(
                actor_observations.c.actor_id == Actor.id,
                Observation.publication_state == PublicationState.PUBLISHED,
                Observation.source.has(Source.publication_state == PublicationState.PUBLISHED),
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        alias_count = (
            select(func.count(Alias.id))
            .where(
                Alias.actor_id == Actor.id,
                Alias.publication_state == PublicationState.PUBLISHED,
                Alias.source.has(Source.publication_state == PublicationState.PUBLISHED),
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        indicator_count = (
            select(func.count())
            .select_from(
                actor_indicators.join(Indicator, Indicator.id == actor_indicators.c.indicator_id)
            )
            .where(
                actor_indicators.c.actor_id == Actor.id,
                Indicator.publication_state == PublicationState.PUBLISHED,
                Indicator.source.has(Source.publication_state == PublicationState.PUBLISHED),
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        vulnerability_count = (
            select(func.count())
            .select_from(
                actor_vulnerabilities.join(
                    Vulnerability,
                    Vulnerability.id == actor_vulnerabilities.c.vulnerability_id,
                )
            )
            .where(
                actor_vulnerabilities.c.actor_id == Actor.id,
                Vulnerability.publication_state == PublicationState.PUBLISHED,
                Vulnerability.source.has(Source.publication_state == PublicationState.PUBLISHED),
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        popularity_score = (
            observation_count * 4 + alias_count * 2 + indicator_count * 3 + vulnerability_count * 3
        )
        columns = (
            Actor.id,
            Actor.canonical_name,
            Actor.description,
            latest_observed_at.label("latest_observed_at"),
            observation_count.label("published_observation_count"),
            alias_count.label("published_alias_count"),
            popularity_score.label("popularity_score"),
        )
        base_filter = Actor.publication_state == PublicationState.PUBLISHED
        recent_rows = session.execute(
            select(*columns)
            .where(base_filter)
            .order_by(
                latest_observed_at.desc().nulls_last(),
                Actor.created_at.desc(),
                Actor.canonical_name,
                Actor.id,
            )
            .limit(recent_limit)
        ).mappings()
        popular_rows = session.execute(
            select(*columns)
            .where(base_filter)
            .order_by(
                popularity_score.desc(),
                latest_observed_at.desc().nulls_last(),
                Actor.canonical_name,
                Actor.id,
            )
            .limit(popular_limit)
        ).mappings()
        return ActorDiscoveryResponse(
            recent=[ActorDiscoveryRead.model_validate(dict(row)) for row in recent_rows],
            popular=[ActorDiscoveryRead.model_validate(dict(row)) for row in popular_rows],
            limit=limit,
        )

    @staticmethod
    def _related_actors(
        session: Session, page_rows: Sequence[Any]
    ) -> dict[tuple[str, UUID], list[RelatedActorRead]]:
        targets = {
            entity_type: {
                UUID(str(row["id"])) for row in page_rows if str(row["entity_type"]) == entity_type
            }
            for entity_type in (
                SearchEntityType.INDICATOR.value,
                SearchEntityType.VULNERABILITY.value,
            )
        }
        latest_observed_at = (
            select(func.max(Observation.observed_at))
            .select_from(
                actor_observations.join(
                    Observation, Observation.id == actor_observations.c.observation_id
                )
            )
            .where(
                actor_observations.c.actor_id == Actor.id,
                Observation.publication_state == PublicationState.PUBLISHED,
            )
            .correlate(Actor)
            .scalar_subquery()
        )
        related: dict[tuple[str, UUID], list[RelatedActorRead]] = {}
        associations = (
            (SearchEntityType.INDICATOR.value, actor_indicators, "indicator_id"),
            (SearchEntityType.VULNERABILITY.value, actor_vulnerabilities, "vulnerability_id"),
        )
        for entity_type, association, entity_column in associations:
            entity_ids = targets[entity_type]
            if not entity_ids:
                continue
            rows = session.execute(
                select(
                    association.c[entity_column].label("entity_id"),
                    Actor.id,
                    Actor.canonical_name,
                    Actor.description,
                    latest_observed_at.label("latest_observed_at"),
                )
                .join(Actor, Actor.id == association.c.actor_id)
                .where(
                    association.c[entity_column].in_(entity_ids),
                    Actor.publication_state == PublicationState.PUBLISHED,
                )
                .order_by(
                    association.c[entity_column],
                    latest_observed_at.desc().nulls_last(),
                    Actor.canonical_name,
                    Actor.id,
                )
            ).mappings()
            for row in rows:
                key = (entity_type, UUID(str(row["entity_id"])))
                related.setdefault(key, []).append(
                    RelatedActorRead.model_validate(
                        {
                            "id": row["id"],
                            "canonical_name": row["canonical_name"],
                            "description": row["description"],
                            "latest_observed_at": row["latest_observed_at"],
                        }
                    )
                )
        return related

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
        indicator_type: Any | None = None,
        indicator_value: Any | None = None,
        severity: Any | None = None,
        cvss_score: Any | None = None,
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
            cast(indicator_type if indicator_type is not None else null(), String).label(
                "indicator_type"
            ),
            cast(indicator_value if indicator_value is not None else null(), Text).label(
                "indicator_value"
            ),
            cast(severity if severity is not None else null(), String).label("severity"),
            cast(cvss_score if cvss_score is not None else null(), Float).label("cvss_score"),
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

    @staticmethod
    def _cursor_scope(
        clean_query: str,
        entity_types: set[SearchEntityType],
        source_id: UUID | None,
        intelligence_type: IntelligenceType | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> str:
        scope = {
            "query": clean_query,
            "entity_types": sorted(item.value for item in entity_types),
            "source_id": str(source_id) if source_id else None,
            "intelligence_type": intelligence_type.value if intelligence_type else None,
            "date_from": _datetime_text(date_from),
            "date_to": _datetime_text(date_to),
        }
        encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _encode_cursor(
        score: float,
        entity_order: int,
        title: str,
        entity_id: UUID,
        scope: str,
    ) -> str:
        payload = json.dumps(
            {
                "v": 1,
                "score": score.hex(),
                "entity_order": entity_order,
                "title": title,
                "id": str(entity_id),
                "scope": scope,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        checksum = hashlib.sha256(payload).hexdigest()
        token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        return f"{token}.{checksum}"

    @staticmethod
    def _decode_cursor(cursor: str, expected_scope: str) -> tuple[float, int, str, UUID]:
        try:
            if len(cursor) > MAX_CURSOR_LENGTH:
                raise ValueError
            token, checksum = cursor.split(".", maxsplit=1)
            padding = "=" * (-len(token) % 4)
            payload = base64.urlsafe_b64decode(f"{token}{padding}")
            if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), checksum):
                raise ValueError
            values = json.loads(payload)
            if not isinstance(values, dict) or set(values) != {
                "v",
                "score",
                "entity_order",
                "title",
                "id",
                "scope",
            }:
                raise ValueError
            if values["v"] != 1 or values["scope"] != expected_scope:
                raise ValueError
            score_value = values["score"]
            id_value = values["id"]
            if not isinstance(score_value, str) or not isinstance(id_value, str):
                raise ValueError
            score = float.fromhex(score_value)
            entity_order = values["entity_order"]
            title = values["title"]
            entity_id = UUID(id_value)
            if (
                not math.isfinite(score)
                or isinstance(entity_order, bool)
                or not isinstance(entity_order, int)
                or not 0 <= entity_order < len(ENTITY_ORDER)
                or not isinstance(title, str)
                or not title
                or len(title) > 500
            ):
                raise ValueError
        except (TypeError, ValueError, OverflowError, KeyError, json.JSONDecodeError):
            raise SearchQueryError("The pagination cursor is invalid for this request.") from None
        return score, entity_order, title, entity_id


def _datetime_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()
