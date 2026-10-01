"""Faithful validation, idempotent persistence, and bounded artifact retrieval."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import yaml
from sigma.collection import SigmaCollection
from sqlalchemy import func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from stix2 import parse as parse_stix

from watchtower.artifacts.contracts import (
    ArtifactDetailRead,
    ArtifactRead,
    ArtifactSourceRead,
    ArtifactSubmission,
)
from watchtower.db.models import (
    ArtifactType,
    ArtifactValidationStatus,
    Origin,
    RawEvidence,
    Source,
    TechnicalArtifact,
)

CONTROL_CHARACTER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ATTACK_ID = re.compile(r"^T\d{4}(?:\.\d{3})?$")
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_VALIDATION_ERRORS = 20
SEARCH_DOCUMENT = literal_column(
    "((setweight(to_tsvector('english'::regconfig, coalesce(technical_artifacts.title, '')), "
    "'A') || setweight(to_tsvector('english'::regconfig, "
    "coalesce(technical_artifacts.canonical_id, '')), 'A')) || "
    "setweight(to_tsvector('english'::regconfig, "
    "coalesce(technical_artifacts.metadata::text, '')), 'D'))"
)


class ArtifactError(ValueError):
    pass


class ArtifactNotFoundError(ArtifactError):
    pass


class ArtifactQueryError(ArtifactError):
    pass


@dataclass(frozen=True, slots=True)
class ArtifactIngestionResult:
    artifact: TechnicalArtifact
    duplicate: bool


@dataclass(frozen=True, slots=True)
class ArtifactValidation:
    status: ArtifactValidationStatus
    errors: list[str]
    structured_content: dict[str, Any] | list[Any] | None
    canonical_id: str
    title: str
    version: str | None
    derived_metadata: dict[str, Any]


class ArtifactService:
    def ingest(self, session: Session, submission: ArtifactSubmission) -> ArtifactIngestionResult:
        source = session.get(Source, submission.source_id)
        if source is None:
            raise ArtifactError("Artifact source is not registered.")
        raw_evidence = self._validate_provenance(session, submission)
        content = submission.content
        content_bytes = content.encode("utf-8")
        if not content.strip() or CONTROL_CHARACTER.search(content):
            raise ArtifactError("Artifact content must contain safe, non-blank UTF-8 text.")
        if len(content_bytes) > MAX_ARTIFACT_BYTES:
            raise ArtifactError("Artifact content exceeds the 10 MiB limit.")
        try:
            json.dumps(submission.metadata, allow_nan=False)
        except (TypeError, ValueError):
            raise ArtifactError("Artifact metadata must contain finite JSON values.") from None

        digest = hashlib.sha256(content_bytes).hexdigest()
        existing = session.scalar(
            select(TechnicalArtifact).where(
                TechnicalArtifact.source_id == submission.source_id,
                TechnicalArtifact.artifact_type == submission.artifact_type,
                TechnicalArtifact.content_sha256 == digest,
            )
        )
        if existing is not None:
            return ArtifactIngestionResult(existing, True)

        validation = self._validate(submission.artifact_type, content, digest)
        artifact = TechnicalArtifact(
            source_id=source.id,
            raw_evidence_id=raw_evidence.id if raw_evidence else None,
            artifact_type=submission.artifact_type,
            origin=submission.origin,
            canonical_id=validation.canonical_id,
            title=validation.title,
            version=validation.version,
            content_sha256=digest,
            original_content=content,
            structured_content=validation.structured_content,
            validation_status=validation.status,
            validation_errors=validation.errors,
            artifact_metadata={**submission.metadata, **validation.derived_metadata},
        )
        try:
            with session.begin_nested():
                session.add(artifact)
                session.flush()
        except IntegrityError:
            existing = session.scalar(
                select(TechnicalArtifact).where(
                    TechnicalArtifact.source_id == submission.source_id,
                    TechnicalArtifact.artifact_type == submission.artifact_type,
                    TechnicalArtifact.content_sha256 == digest,
                )
            )
            if existing is None:
                raise
            return ArtifactIngestionResult(existing, True)
        return ArtifactIngestionResult(artifact, False)

    def get(self, session: Session, artifact_id: UUID) -> ArtifactDetailRead:
        artifact = session.scalar(
            select(TechnicalArtifact)
            .options(selectinload(TechnicalArtifact.source))
            .where(TechnicalArtifact.id == artifact_id)
        )
        if artifact is None:
            raise ArtifactNotFoundError("Technical artifact was not found.")
        return self._detail(artifact)

    def search(
        self,
        session: Session,
        *,
        query: str | None = None,
        artifact_type: ArtifactType | None = None,
        source_id: UUID | None = None,
        origin: Origin | None = None,
        validation_status: ArtifactValidationStatus | None = None,
        limit: int = 25,
    ) -> list[ArtifactRead]:
        statement = select(TechnicalArtifact).options(selectinload(TechnicalArtifact.source))
        if query is not None:
            cleaned = " ".join(query.split())
            if not 2 <= len(cleaned) <= 200 or CONTROL_CHARACTER.search(query):
                raise ArtifactQueryError("Artifact query must contain 2–200 safe characters.")
            statement = statement.where(
                SEARCH_DOCUMENT.op("@@")(
                    func.websearch_to_tsquery(literal_column("'english'::regconfig"), cleaned)
                )
            )
        if artifact_type is not None:
            statement = statement.where(TechnicalArtifact.artifact_type == artifact_type)
        if source_id is not None:
            statement = statement.where(TechnicalArtifact.source_id == source_id)
        if origin is not None:
            statement = statement.where(TechnicalArtifact.origin == origin)
        if validation_status is not None:
            statement = statement.where(TechnicalArtifact.validation_status == validation_status)
        statement = statement.order_by(
            TechnicalArtifact.created_at.desc(), TechnicalArtifact.id
        ).limit(limit)
        return [self._read(item) for item in session.scalars(statement).all()]

    @staticmethod
    def _validate_provenance(
        session: Session, submission: ArtifactSubmission
    ) -> RawEvidence | None:
        if submission.origin is Origin.IMPORTED and submission.raw_evidence_id is None:
            raise ArtifactError("Imported artifacts require raw evidence provenance.")
        if submission.raw_evidence_id is None:
            return None
        raw = session.get(RawEvidence, submission.raw_evidence_id)
        if raw is None or raw.source_id != submission.source_id:
            raise ArtifactError("Raw evidence must exist and belong to the artifact source.")
        return raw

    def _validate(
        self, artifact_type: ArtifactType, content: str, digest: str
    ) -> ArtifactValidation:
        if artifact_type is ArtifactType.SIGMA:
            return self._validate_sigma(content, digest)
        if artifact_type is ArtifactType.ATTACK_TECHNIQUE:
            return self._validate_attack(content, digest)
        return self._validate_stix(content, digest)

    def _validate_stix(self, content: str, digest: str) -> ArtifactValidation:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("STIX content must be a JSON object.")
            parse_stix(payload, allow_custom=False, version="2.1")
            artifact_type = str(payload.get("type", "stix-object"))
            if payload.get("spec_version") not in {None, "2.1"} or (
                artifact_type == "bundle"
                and any(
                    item.get("spec_version") not in {None, "2.1"}
                    for item in payload.get("objects", [])
                    if isinstance(item, dict)
                )
            ):
                raise ValueError("Only STIX 2.1 artifacts are supported.")
            canonical_id = str(payload.get("id") or f"bundle:{digest}")
            title = str(payload.get("name") or "STIX 2.1 bundle")
            count = len(payload.get("objects", [])) if artifact_type == "bundle" else 1
            return ArtifactValidation(
                ArtifactValidationStatus.VALID,
                [],
                payload,
                canonical_id[:512],
                title[:500],
                "2.1",
                {"stix_type": artifact_type, "object_count": count},
            )
        except Exception as error:
            payload = self._json_structure(content)
            return self._invalid("STIX 2.1 artifact", digest, payload, error)

    def _validate_sigma(self, content: str, digest: str) -> ArtifactValidation:
        structured: dict[str, Any] | list[Any] | None = None
        try:
            loaded = yaml.safe_load(content)
            if isinstance(loaded, (dict, list)):
                structured = loaded
            collection = SigmaCollection.from_yaml(content, collect_errors=True)
            if collection.errors:
                raise ValueError("; ".join(str(error) for error in collection.errors))
            if len(collection.rules) != 1:
                raise ValueError("Exactly one atomic Sigma rule is required.")
            rule = collection.rules[0]
            canonical_id = str(rule.id or f"sigma:{digest}")
            return ArtifactValidation(
                ArtifactValidationStatus.VALID,
                [],
                structured,
                canonical_id[:512],
                str(rule.title)[:500],
                None,
                {"sigma_status": str(rule.status) if rule.status else None},
            )
        except Exception as error:
            return self._invalid("Sigma rule", digest, structured, error)

    def _validate_attack(self, content: str, digest: str) -> ArtifactValidation:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError("ATT&CK technique content must be a JSON object.")
            parse_stix(payload, allow_custom=True, version="2.1")
            if payload.get("type") != "attack-pattern":
                raise ValueError("ATT&CK technique must be a STIX attack-pattern.")
            external_id = next(
                (
                    item.get("external_id")
                    for item in payload.get("external_references", [])
                    if isinstance(item, dict)
                    and item.get("source_name") in {"mitre-attack", "mitre-mobile-attack"}
                    and isinstance(item.get("external_id"), str)
                ),
                None,
            )
            if external_id is None or not ATTACK_ID.fullmatch(external_id):
                raise ValueError("ATT&CK technique requires a valid MITRE technique ID.")
            title = payload.get("name")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("ATT&CK technique requires a name.")
            return ArtifactValidation(
                ArtifactValidationStatus.VALID,
                [],
                payload,
                external_id,
                title[:500],
                str(payload.get("x_mitre_version") or "2.1")[:100],
                {"stix_id": payload.get("id")},
            )
        except Exception as error:
            return self._invalid(
                "ATT&CK technique reference", digest, self._json_structure(content), error
            )

    @staticmethod
    def _invalid(
        title: str,
        digest: str,
        structured: dict[str, Any] | list[Any] | None,
        error: Exception,
    ) -> ArtifactValidation:
        message = " ".join(str(error).split())[:500] or type(error).__name__
        return ArtifactValidation(
            ArtifactValidationStatus.INVALID,
            [message][:MAX_VALIDATION_ERRORS],
            structured,
            f"invalid:{digest}",
            f"Invalid {title}"[:500],
            None,
            {},
        )

    @staticmethod
    def _json_structure(content: str) -> dict[str, Any] | list[Any] | None:
        try:
            loaded = json.loads(content)
            return loaded if isinstance(loaded, (dict, list)) else None
        except (json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _read(artifact: TechnicalArtifact) -> ArtifactRead:
        return ArtifactRead(
            id=artifact.id,
            artifact_type=artifact.artifact_type,
            origin=artifact.origin,
            canonical_id=artifact.canonical_id,
            title=artifact.title,
            version=artifact.version,
            content_sha256=artifact.content_sha256,
            validation_status=artifact.validation_status,
            validation_errors=artifact.validation_errors,
            metadata=artifact.artifact_metadata,
            raw_evidence_id=artifact.raw_evidence_id,
            source=ArtifactSourceRead(
                id=artifact.source.id,
                name=artifact.source.name,
                kind=artifact.source.kind,
                base_url=artifact.source.base_url,
            ),
            created_at=artifact.created_at,
        )

    @classmethod
    def _detail(cls, artifact: TechnicalArtifact) -> ArtifactDetailRead:
        summary = cls._read(artifact)
        return ArtifactDetailRead(
            **summary.model_dump(),
            original_content=artifact.original_content,
            structured_content=artifact.structured_content,
        )
