"""Conservative, deterministic STIX 2.1 export for actor intelligence."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from stix2 import parse as parse_stix

from watchtower.db.models import (
    Actor,
    Alias,
    Campaign,
    Evidence,
    Observation,
    Relationship,
    Source,
    Technique,
)

EXPORT_NAMESPACE = uuid5(NAMESPACE_URL, "https://watchtower.local/stix/2.1/export/v1")
MAX_REFERENCE_DESCRIPTION = 1000


class StixExportError(ValueError):
    """Base class for controlled export errors."""


class StixActorNotFoundError(StixExportError):
    """Raised when the requested actor does not exist."""


class StixExportService:
    """Build a standards-valid STIX bundle without changing internal records."""

    def export_actor(self, session: Session, actor_id: UUID) -> dict[str, Any]:
        actor = session.scalar(self._actor_statement(actor_id))
        if actor is None:
            raise StixActorNotFoundError("Actor was not found.")

        actor_ref = _stix_id("intrusion-set", actor.id)
        objects: list[dict[str, Any]] = [self._intrusion_set(actor)]

        observations = sorted(actor.observations, key=lambda item: str(item.id))
        techniques = {
            technique.id: technique
            for observation in observations
            for technique in observation.techniques
        }
        for technique in sorted(techniques.values(), key=lambda item: str(item.id)):
            objects.append(self._attack_pattern(technique))

        for observation in observations:
            objects.append(self._note(observation, actor_ref))

        support: dict[UUID, list[Observation]] = defaultdict(list)
        for observation in observations:
            for technique in observation.techniques:
                support[technique.id].append(observation)
        for technique_id in sorted(support, key=str):
            objects.append(
                self._uses_relationship(
                    actor,
                    techniques[technique_id],
                    support[technique_id],
                )
            )

        approved_relationships = sorted(
            (
                relationship
                for relationship in actor.relationships
                if relationship.relationship_type.strip().casefold() == "attributed-to"
            ),
            key=lambda item: str(item.id),
        )
        campaigns: dict[UUID, Campaign] = {}
        for relationship in approved_relationships:
            campaigns[relationship.campaign.id] = relationship.campaign
        for campaign in sorted(campaigns.values(), key=lambda item: str(item.id)):
            objects.append(self._campaign(campaign))
        for relationship in approved_relationships:
            objects.append(self._attribution_relationship(relationship))

        objects.sort(key=lambda item: (str(item["type"]), str(item["id"])))
        object_ids = ",".join(str(item["id"]) for item in objects)
        bundle: dict[str, Any] = {
            "type": "bundle",
            "id": f"bundle--{uuid5(EXPORT_NAMESPACE, f'bundle:actor:{actor.id}:{object_ids}')}",
            "objects": objects,
        }
        # Keep validation at the boundary so an implementation regression cannot
        # return custom or malformed STIX content.
        parse_stix(bundle, allow_custom=False, version="2.1")
        return bundle

    @staticmethod
    def _actor_statement(actor_id: UUID):
        return (
            select(Actor)
            .where(Actor.id == actor_id)
            .options(
                selectinload(Actor.aliases).selectinload(Alias.source),
                selectinload(Actor.observations).selectinload(Observation.source),
                selectinload(Actor.observations)
                .selectinload(Observation.evidence)
                .selectinload(Evidence.source),
                selectinload(Actor.observations)
                .selectinload(Observation.techniques)
                .selectinload(Technique.source),
                selectinload(Actor.relationships)
                .selectinload(Relationship.campaign)
                .selectinload(Campaign.source),
                selectinload(Actor.relationships).selectinload(Relationship.source),
                selectinload(Actor.relationships)
                .selectinload(Relationship.evidence)
                .selectinload(Evidence.source),
            )
        )

    def _intrusion_set(self, actor: Actor) -> dict[str, Any]:
        result = self._base("intrusion-set", actor.id, actor.created_at, actor.updated_at)
        result["name"] = actor.canonical_name
        if actor.description:
            result["description"] = actor.description
        aliases = sorted({item.name for item in actor.aliases if item.name != actor.canonical_name})
        if aliases:
            result["aliases"] = aliases
        references = [
            _external_reference(item.source, item.source_native_id)
            for item in sorted(actor.aliases, key=lambda alias: str(alias.id))
        ]
        _add_references(result, references)
        return result

    def _attack_pattern(self, technique: Technique) -> dict[str, Any]:
        result = self._base(
            "attack-pattern",
            technique.id,
            technique.created_at,
            technique.updated_at,
        )
        result["name"] = technique.name
        if technique.description:
            result["description"] = technique.description
        _add_references(
            result,
            [_external_reference(technique.source, technique.external_id)],
        )
        return result

    def _note(self, observation: Observation, actor_ref: str) -> dict[str, Any]:
        result = self._base("note", observation.id, observation.created_at, observation.updated_at)
        result["content"] = _note_content(observation)
        result["labels"] = [f"watchtower:{observation.intelligence_type.value}"]
        object_refs = [actor_ref]
        object_refs.extend(
            _stix_id("attack-pattern", technique.id)
            for technique in sorted(observation.techniques, key=lambda item: str(item.id))
        )
        result["object_refs"] = object_refs
        if observation.confidence is not None:
            result["confidence"] = observation.confidence
        references = [_external_reference(observation.source, observation.source_native_id)]
        references.extend(_evidence_reference(item) for item in observation.evidence)
        _add_references(result, references)
        return result

    def _campaign(self, campaign: Campaign) -> dict[str, Any]:
        result = self._base("campaign", campaign.id, campaign.created_at, campaign.updated_at)
        result["name"] = campaign.name
        if campaign.description:
            result["description"] = campaign.description
        if campaign.first_seen is not None:
            result["first_seen"] = _stix_time(campaign.first_seen)
        if campaign.last_seen is not None:
            result["last_seen"] = _stix_time(campaign.last_seen)
        if campaign.confidence is not None:
            result["confidence"] = campaign.confidence
        _add_references(
            result,
            [_external_reference(campaign.source, campaign.source_native_id)],
        )
        return result

    def _uses_relationship(
        self,
        actor: Actor,
        technique: Technique,
        observations: list[Observation],
    ) -> dict[str, Any]:
        created = min(item.created_at for item in observations)
        modified = max(item.updated_at for item in observations)
        stable_key = f"{actor.id}:{technique.id}"
        result = self._base("relationship", stable_key, created, modified)
        result.update(
            {
                "relationship_type": "uses",
                "source_ref": _stix_id("intrusion-set", actor.id),
                "target_ref": _stix_id("attack-pattern", technique.id),
            }
        )
        references: list[dict[str, str]] = []
        for observation in observations:
            references.append(_external_reference(observation.source, observation.source_native_id))
            references.extend(_evidence_reference(item) for item in observation.evidence)
        _add_references(result, references)
        return result

    def _attribution_relationship(self, relationship: Relationship) -> dict[str, Any]:
        result = self._base(
            "relationship",
            relationship.id,
            relationship.created_at,
            relationship.updated_at,
        )
        result.update(
            {
                "relationship_type": "attributed-to",
                "source_ref": _stix_id("campaign", relationship.campaign_id),
                "target_ref": _stix_id("intrusion-set", relationship.actor_id),
            }
        )
        if relationship.first_seen is not None:
            result["start_time"] = _stix_time(relationship.first_seen)
        if relationship.last_seen is not None:
            result["stop_time"] = _stix_time(relationship.last_seen)
        if relationship.confidence is not None:
            result["confidence"] = relationship.confidence
        references = [_external_reference(relationship.source)]
        if relationship.evidence is not None:
            references.append(_evidence_reference(relationship.evidence))
        _add_references(result, references)
        return result

    @staticmethod
    def _base(
        object_type: str,
        key: UUID | str,
        created: datetime,
        modified: datetime,
    ) -> dict[str, Any]:
        return {
            "type": object_type,
            "spec_version": "2.1",
            "id": _stix_id(object_type, key),
            "created": _stix_time(created),
            "modified": _stix_time(modified),
        }


def _stix_id(object_type: str, key: UUID | str) -> str:
    return f"{object_type}--{uuid5(EXPORT_NAMESPACE, f'{object_type}:{key}')}"


def _stix_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _external_reference(
    source: Source,
    external_id: str | None = None,
    *,
    url: str | None = None,
    description: str | None = None,
) -> dict[str, str]:
    reference = {"source_name": source.name}
    if external_id:
        reference["external_id"] = external_id
    safe_url = _safe_url(url) or _safe_url(source.base_url)
    if safe_url:
        reference["url"] = safe_url
    if description:
        reference["description"] = description[:MAX_REFERENCE_DESCRIPTION]
    return reference


def _evidence_reference(evidence: Evidence) -> dict[str, str]:
    description = evidence.citation
    if evidence.excerpt:
        description = f"{description} — {evidence.excerpt}"
    return _external_reference(
        evidence.source,
        url=evidence.locator,
        description=description,
    )


def _add_references(target: dict[str, Any], references: list[dict[str, str]]) -> None:
    unique = {json.dumps(item, sort_keys=True): item for item in references}
    if unique:
        target["external_references"] = [unique[key] for key in sorted(unique)]


def _note_content(observation: Observation) -> str:
    timestamps = [f"WATCHTOWER intelligence time: {_stix_time(observation.observed_at)}"]
    if observation.first_seen is not None:
        timestamps.append(f"First seen: {_stix_time(observation.first_seen)}")
    if observation.last_seen is not None:
        timestamps.append(f"Last seen: {_stix_time(observation.last_seen)}")
    return f"{observation.title}\n\n{observation.summary}\n\n" + "\n".join(timestamps)
