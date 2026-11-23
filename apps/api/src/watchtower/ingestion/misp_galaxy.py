"""Versioned MISP Galaxy threat-actor ingestion."""

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from watchtower.db.models import Actor, Alias, Observation
from watchtower.ingestion.contracts import SourceRegistration
from watchtower.ingestion.fixed_source import (
    FixedSourceDefinition,
    InvalidSourcePayloadError,
    ParsedSourcePayload,
    SourceObject,
)
from watchtower.ingestion.normalization import (
    CanonicalObservation,
    DeduplicationAction,
    DeduplicationDecision,
    NormalizationRecord,
    RejectedSourceRecord,
    SqlAlchemyObservationRepository,
)
from watchtower.services.actor_resolution import ActorResolutionError, normalize_actor_name

MISP_GALAXY_VERSION = "2026031300"
MISP_GALAXY_RELEASED_AT = datetime(2026, 3, 13, tzinfo=UTC)
MISP_GALAXY_URL = (
    "https://raw.githubusercontent.com/MISP/misp-galaxy/"
    f"{MISP_GALAXY_VERSION}/clusters/threat-actor.json"
)

MISP_GALAXY_DEFINITION = FixedSourceDefinition(
    key="misp-galaxy",
    url=MISP_GALAXY_URL,
    filename=f"misp-galaxy-threat-actor-{MISP_GALAXY_VERSION}.json",
    accepted_media_types=frozenset({"application/json", "application/octet-stream", "text/plain"}),
    registration=SourceRegistration.model_validate(
        {
            "name": "MISP Galaxy Threat Actors",
            "kind": "dataset",
            "base_url": "https://github.com/MISP/misp-galaxy/",
            "policy_notes": (
                "Versioned threat-actor galaxy import. Preserve cluster UUIDs, synonyms, "
                "references and upstream attribution."
            ),
            "license_name": "CC0 1.0 or BSD 2-Clause",
            "license_url": "https://github.com/MISP/misp-galaxy/blob/main/LICENSE.md",
            "metadata": {
                "collection": "threat-actor",
                "format": "MISP Galaxy JSON",
                "version": MISP_GALAXY_VERSION,
            },
        }
    ),
)


class MispGalaxyDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    type: Literal["threat-actor"]
    uuid: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    version: int = Field(ge=1)
    values: list[dict[str, Any]] = Field(max_length=5000)


class ParsedMispActor(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    uuid: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=255)
    description: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    related: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("value")
    @classmethod
    def clean_value(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Actor value cannot be blank")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class MispGalaxyPayloadParser:
    def parse(self, content: bytes, *, fetched_at: datetime) -> ParsedSourcePayload:
        del fetched_at
        try:
            payload = json.loads(content)
            document = MispGalaxyDocument.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
            raise InvalidSourcePayloadError(
                "Payload is not a valid MISP threat-actor galaxy document"
            ) from error
        objects: list[SourceObject] = []
        for index, value in enumerate(document.values):
            try:
                actor = ParsedMispActor.model_validate(value)
            except ValidationError as error:
                raise InvalidSourcePayloadError(
                    f"MISP threat-actor object {index} is invalid"
                ) from error
            objects.append(
                SourceObject(
                    source_native_id=actor.uuid,
                    object_type="misp-galaxy-threat-actor",
                    payload=actor.model_dump(mode="json"),
                )
            )
        return ParsedSourcePayload(
            source_native_id=f"misp-galaxy:{document.uuid}:{document.version}",
            published_at=MISP_GALAXY_RELEASED_AT,
            metadata={
                "collection_uuid": document.uuid,
                "collection_name": document.name,
                "collection_version": document.version,
                "release": MISP_GALAXY_VERSION,
            },
            objects=tuple(objects),
        )


class MispActorRecordParser:
    def parse(self, record: NormalizationRecord) -> ParsedMispActor:
        if record.object_type != "misp-galaxy-threat-actor":
            raise RejectedSourceRecord("unsupported MISP Galaxy object type")
        try:
            actor = ParsedMispActor.model_validate(record.payload)
        except ValidationError as error:
            raise RejectedSourceRecord("invalid MISP threat-actor fields") from error
        if actor.uuid != record.source_native_id:
            raise RejectedSourceRecord("MISP cluster UUID does not match source-native ID")
        return actor


class MispActorNormalizer:
    def normalize(
        self, parsed: ParsedMispActor, record: NormalizationRecord
    ) -> CanonicalObservation:
        synonyms = self._string_list(parsed.meta.get("synonyms"), maximum=200)
        references = self._string_list(parsed.meta.get("refs"), maximum=200)
        confidence = self._confidence(parsed.meta.get("attribution-confidence"))
        metadata: dict[str, Any] = {
            "cluster_uuid": parsed.uuid,
            "actor_name": parsed.value,
            "synonyms": synonyms,
            "references": references,
            "related": parsed.related[:100],
            "galaxy_release": MISP_GALAXY_VERSION,
        }
        for field in ("country", "cfr-suspected-state-sponsor", "cfr-type-of-incident"):
            value = parsed.meta.get(field)
            if isinstance(value, str) and value.strip():
                metadata[field] = value.strip()
        return CanonicalObservation(
            source_id=record.source_id,
            raw_evidence_id=record.raw_evidence_id,
            source_native_id=parsed.uuid,
            title=parsed.value,
            summary=parsed.description or f"MISP Galaxy threat-actor cluster for {parsed.value}.",
            observed_at=MISP_GALAXY_RELEASED_AT,
            confidence=confidence,
            metadata=metadata,
        )

    @staticmethod
    def _string_list(value: Any, *, maximum: int) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value[:maximum]:
            if isinstance(item, str) and item.strip():
                result.append(item.strip()[:2048])
        return result

    @staticmethod
    def _confidence(value: Any) -> int | None:
        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            return parsed if 0 <= parsed <= 100 else None
        if isinstance(value, int) and 0 <= value <= 100:
            return value
        return None


class MispActorObservationRepository(SqlAlchemyObservationRepository):
    """Persist an internal actor candidate and source-preserved aliases."""

    def persist(
        self,
        session: Session,
        canonical: CanonicalObservation,
        fingerprint: str,
        decision: DeduplicationDecision,
    ) -> Observation:
        observation = super().persist(session, canonical, fingerprint, decision)
        if decision.action is DeduplicationAction.KEEP:
            return observation
        source_metadata = canonical.metadata
        actor_name = source_metadata.get("actor_name")
        if not isinstance(actor_name, str):
            raise RejectedSourceRecord("MISP actor name is missing from canonical metadata")
        normalized_name = normalize_actor_name(actor_name)
        actor = session.scalar(select(Actor).where(Actor.normalized_name == normalized_name))
        if actor is None:
            actor = Actor(
                canonical_name=actor_name,
                normalized_name=normalized_name,
                description=canonical.summary,
                actor_metadata={
                    "created_from_source": "MISP Galaxy",
                    "cluster_uuid": canonical.source_native_id,
                },
            )
            session.add(actor)
            session.flush()
        if actor not in observation.actors:
            observation.actors.append(actor)

        aliases = source_metadata.get("synonyms")
        if isinstance(aliases, list):
            for alias_name in aliases:
                if not isinstance(alias_name, str):
                    continue
                try:
                    normalized_alias = normalize_actor_name(alias_name)
                except ActorResolutionError:
                    # The source string remains in observation metadata, but an unsafe or
                    # overlong value must not become a canonical alias key.
                    continue
                if not normalized_alias or normalized_alias == normalized_name:
                    continue
                alias = session.scalar(
                    select(Alias).where(
                        Alias.source_id == canonical.source_id,
                        Alias.normalized_name == normalized_alias,
                    )
                )
                if alias is None:
                    session.add(
                        Alias(
                            source_id=canonical.source_id,
                            actor_id=actor.id,
                            name=alias_name[:255],
                            normalized_name=normalized_alias[:255],
                            source_native_id=canonical.source_native_id,
                            confidence=canonical.confidence,
                            alias_metadata={"cluster_uuid": canonical.source_native_id},
                        )
                    )
                elif alias.alias_metadata.get("resolution_status") == "ambiguous":
                    self._retain_ambiguous_candidate(alias, actor, canonical.source_native_id)
                elif alias.actor_id not in {None, actor.id}:
                    self._mark_alias_ambiguous(alias, actor, canonical.source_native_id)
                else:
                    alias.actor_id = actor.id
        session.flush()
        return observation

    @staticmethod
    def _mark_alias_ambiguous(alias: Alias, actor: Actor, cluster_uuid: str) -> None:
        candidate_actor_ids = {str(actor.id)}
        if alias.actor_id is not None:
            candidate_actor_ids.add(str(alias.actor_id))
        cluster_uuids = {cluster_uuid}
        existing_cluster = alias.alias_metadata.get("cluster_uuid")
        if isinstance(existing_cluster, str):
            cluster_uuids.add(existing_cluster)
        alias.actor_id = None
        alias.source_native_id = None
        alias.confidence = None
        alias.alias_metadata = {
            "resolution_status": "ambiguous",
            "candidate_actor_ids": sorted(candidate_actor_ids),
            "cluster_uuids": sorted(cluster_uuids),
        }

    @staticmethod
    def _retain_ambiguous_candidate(alias: Alias, actor: Actor, cluster_uuid: str) -> None:
        metadata = alias.alias_metadata
        candidate_actor_ids = {
            value for value in metadata.get("candidate_actor_ids", []) if isinstance(value, str)
        }
        candidate_actor_ids.add(str(actor.id))
        cluster_uuids = {
            value for value in metadata.get("cluster_uuids", []) if isinstance(value, str)
        }
        cluster_uuids.add(cluster_uuid)
        alias.actor_id = None
        alias.source_native_id = None
        alias.confidence = None
        alias.alias_metadata = {
            "resolution_status": "ambiguous",
            "candidate_actor_ids": sorted(candidate_actor_ids),
            "cluster_uuids": sorted(cluster_uuids),
        }
