from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from watchtower.db.base import Base


class IntelligenceType(StrEnum):
    OBSERVED = "observed"
    ASSESSED = "assessed"


class Origin(StrEnum):
    IMPORTED = "imported"
    WATCHTOWER = "watchtower"


class RetrievalStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProcessingState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NormalizationStatus(StrEnum):
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    DEDUPLICATED = "deduplicated"
    REJECTED = "rejected"
    FAILED = "failed"


class NormalizationStage(StrEnum):
    PARSE = "parse"
    NORMALIZE = "normalize"
    VALIDATE = "validate"
    DEDUPLICATE = "deduplicate"
    PERSIST = "persist"


class ResolutionDecision(StrEnum):
    AUTO_LINK = "auto_link"
    UNRESOLVED = "unresolved"
    MANUAL_LINK = "manual_link"
    MANUAL_UNLINK = "manual_unlink"


class ResolutionMethod(StrEnum):
    EXACT_ACTOR_NAME = "exact_actor_name"
    KNOWN_ALIAS = "known_alias"
    EXACT_CANDIDATES = "exact_candidates"
    AMBIGUOUS_EXACT = "ambiguous_exact"
    SIMILARITY_CANDIDATES = "similarity_candidates"
    NO_MATCH = "no_match"
    EXISTING_LINK = "existing_link"
    MANUAL = "manual"


class IngestionJobKind(StrEnum):
    MITRE_ATTACK_REFRESH = "mitre_attack_refresh"


class IngestionJobState(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ArtifactType(StrEnum):
    STIX_2_1 = "stix_2_1"
    SIGMA = "sigma"
    ATTACK_TECHNIQUE = "attack_technique"


class ArtifactValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class AdvisoryStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class AdvisorySectionType(StrEnum):
    WHAT_HAPPENED = "what_happened"
    ACTOR_CONTEXT = "actor_context"
    TECHNICAL_ANALYSIS = "technical_analysis"
    DETECTION = "detection"
    RESPONSE = "response"
    MITIGATION = "mitigation"
    WATCHTOWER_ASSESSMENT = "watchtower_assessment"


intelligence_type_enum = Enum(
    IntelligenceType,
    name="intelligence_type",
    values_callable=lambda values: [value.value for value in values],
)
origin_enum = Enum(
    Origin,
    name="intelligence_origin",
    values_callable=lambda values: [value.value for value in values],
)
retrieval_status_enum = Enum(
    RetrievalStatus,
    name="retrieval_status",
    values_callable=lambda values: [value.value for value in values],
)
processing_state_enum = Enum(
    ProcessingState,
    name="processing_state",
    values_callable=lambda values: [value.value for value in values],
)
normalization_status_enum = Enum(
    NormalizationStatus,
    name="normalization_status",
    values_callable=lambda values: [value.value for value in values],
)
normalization_stage_enum = Enum(
    NormalizationStage,
    name="normalization_stage",
    values_callable=lambda values: [value.value for value in values],
)
resolution_decision_enum = Enum(
    ResolutionDecision,
    name="resolution_decision",
    values_callable=lambda values: [value.value for value in values],
)
resolution_method_enum = Enum(
    ResolutionMethod,
    name="resolution_method",
    values_callable=lambda values: [value.value for value in values],
)
ingestion_job_kind_enum = Enum(
    IngestionJobKind,
    name="ingestion_job_kind",
    values_callable=lambda values: [value.value for value in values],
)
ingestion_job_state_enum = Enum(
    IngestionJobState,
    name="ingestion_job_state",
    values_callable=lambda values: [value.value for value in values],
)
artifact_type_enum = Enum(
    ArtifactType,
    name="artifact_type",
    values_callable=lambda values: [value.value for value in values],
)
artifact_validation_status_enum = Enum(
    ArtifactValidationStatus,
    name="artifact_validation_status",
    values_callable=lambda values: [value.value for value in values],
)
advisory_status_enum = Enum(
    AdvisoryStatus,
    name="advisory_status",
    values_callable=lambda values: [value.value for value in values],
)
advisory_section_type_enum = Enum(
    AdvisorySectionType,
    name="advisory_section_type",
    values_callable=lambda values: [value.value for value in values],
)


class IdMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


actor_observations = Table(
    "actor_observations",
    Base.metadata,
    Column("actor_id", Uuid, ForeignKey("actors.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "observation_id", Uuid, ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    ),
)

observation_evidence = Table(
    "observation_evidence",
    Base.metadata,
    Column(
        "observation_id", Uuid, ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
)

observation_behaviors = Table(
    "observation_behaviors",
    Base.metadata,
    Column(
        "observation_id", Uuid, ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("behavior_id", Uuid, ForeignKey("behaviors.id", ondelete="CASCADE"), primary_key=True),
)

observation_techniques = Table(
    "observation_techniques",
    Base.metadata,
    Column(
        "observation_id", Uuid, ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("technique_id", Uuid, ForeignKey("techniques.id", ondelete="CASCADE"), primary_key=True),
)


class Source(IdMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        CheckConstraint("btrim(kind) <> ''", name="kind_not_blank"),
        Index(
            "ix_sources_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, "
                "COALESCE(name, ''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, (((COALESCE(kind, "
                "''::character varying)::text || ' '::text) || COALESCE(policy_notes, "
                "''::text)) || ' '::text) || COALESCE(license_name, "
                "''::character varying)::text), 'B'::\"char\")) || "
                "setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    policy_notes: Mapped[str | None] = mapped_column(Text)
    license_name: Mapped[str | None] = mapped_column(String(255))
    license_url: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    raw_evidence: Mapped[list[RawEvidence]] = orm_relationship(back_populates="source")
    aliases: Mapped[list[Alias]] = orm_relationship(back_populates="source")
    observations: Mapped[list[Observation]] = orm_relationship(back_populates="source")
    evidence: Mapped[list[Evidence]] = orm_relationship(back_populates="source")
    techniques: Mapped[list[Technique]] = orm_relationship(back_populates="source")
    campaigns: Mapped[list[Campaign]] = orm_relationship(back_populates="source")
    relationships: Mapped[list[Relationship]] = orm_relationship(back_populates="source")
    normalization_records: Mapped[list[NormalizationLedger]] = orm_relationship(
        back_populates="source"
    )
    ingestion_jobs: Mapped[list[IngestionJob]] = orm_relationship(back_populates="source")
    evidence_embeddings: Mapped[list[EvidenceEmbedding]] = orm_relationship(back_populates="source")
    technical_artifacts: Mapped[list[TechnicalArtifact]] = orm_relationship(back_populates="source")


class RawEvidence(IdMixin, TimestampMixin, Base):
    __tablename__ = "raw_evidence"
    __table_args__ = (
        UniqueConstraint("source_id", "content_sha256"),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="sha256_lower_hex"),
        CheckConstraint("btrim(storage_uri) <> ''", name="storage_uri_not_blank"),
        CheckConstraint(
            "source_locator IS NULL OR btrim(source_locator) <> ''",
            name="source_locator_not_blank",
        ),
        CheckConstraint(
            "storage_key IS NULL OR btrim(storage_key) <> ''", name="storage_key_not_blank"
        ),
        CheckConstraint(
            "original_filename IS NULL OR btrim(original_filename) <> ''",
            name="original_filename_not_blank",
        ),
        CheckConstraint(
            "content_size_bytes IS NULL OR content_size_bytes > 0", name="content_size_positive"
        ),
        CheckConstraint("processing_attempts >= 0", name="processing_attempts_nonnegative"),
        UniqueConstraint("storage_key"),
        Index("ix_raw_evidence_content_sha256", "content_sha256"),
        Index("ix_raw_evidence_storage_uri", "storage_uri"),
        Index("ix_raw_evidence_processing_state", "processing_state"),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    source_locator: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    source_native_id: Mapped[str | None] = mapped_column(String(512))
    retrieval_status: Mapped[RetrievalStatus] = mapped_column(
        retrieval_status_enum,
        nullable=False,
        default=RetrievalStatus.SUCCEEDED,
        server_default=text("'succeeded'"),
    )
    processing_state: Mapped[ProcessingState] = mapped_column(
        processing_state_enum,
        nullable=False,
        default=ProcessingState.PENDING,
        server_default=text("'pending'"),
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    processing_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="raw_evidence")
    observations: Mapped[list[Observation]] = orm_relationship(back_populates="raw_evidence")
    evidence: Mapped[list[Evidence]] = orm_relationship(back_populates="raw_evidence")
    normalization_records: Mapped[list[NormalizationLedger]] = orm_relationship(
        back_populates="raw_evidence"
    )
    ingestion_jobs: Mapped[list[IngestionJob]] = orm_relationship(back_populates="raw_evidence")
    technical_artifacts: Mapped[list[TechnicalArtifact]] = orm_relationship(
        back_populates="raw_evidence"
    )


class IngestionJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("job_kind", "idempotency_key"),
        CheckConstraint("btrim(correlation_id) <> ''", name="correlation_id_not_blank"),
        CheckConstraint("btrim(idempotency_key) <> ''", name="idempotency_key_not_blank"),
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        CheckConstraint("max_attempts BETWEEN 1 AND 10", name="max_attempts_range"),
        CheckConstraint("attempts <= max_attempts", name="attempts_within_limit"),
        CheckConstraint(
            "(state = 'queued' AND finished_at IS NULL AND lease_expires_at IS NULL "
            "AND lease_token IS NULL AND next_attempt_at IS NOT NULL) OR "
            "(state = 'processing' AND started_at IS NOT NULL AND finished_at IS NULL "
            "AND lease_expires_at IS NOT NULL AND lease_token IS NOT NULL "
            "AND next_attempt_at IS NULL) OR "
            "(state = 'succeeded' AND finished_at IS NOT NULL AND lease_expires_at IS NULL "
            "AND lease_token IS NULL AND next_attempt_at IS NULL AND failure_reason IS NULL) OR "
            "(state = 'failed' AND finished_at IS NOT NULL AND lease_expires_at IS NULL "
            "AND lease_token IS NULL AND next_attempt_at IS NULL AND failure_reason IS NOT NULL "
            "AND btrim(failure_reason) <> '')",
            name="state_shape",
        ),
        Index("ix_ingestion_jobs_state_due", "state", "next_attempt_at"),
        Index("ix_ingestion_jobs_processing_lease", "state", "lease_expires_at"),
    )

    job_kind: Mapped[IngestionJobKind] = mapped_column(ingestion_job_kind_enum, nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raw_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_evidence.id", ondelete="RESTRICT"), index=True
    )
    state: Mapped[IngestionJobState] = mapped_column(
        ingestion_job_state_enum,
        nullable=False,
        default=IngestionJobState.QUEUED,
        server_default=text("'queued'"),
    )
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = orm_relationship(back_populates="ingestion_jobs")
    raw_evidence: Mapped[RawEvidence | None] = orm_relationship(back_populates="ingestion_jobs")


class Actor(IdMixin, TimestampMixin, Base):
    __tablename__ = "actors"
    __table_args__ = (
        CheckConstraint("btrim(canonical_name) <> ''", name="canonical_name_not_blank"),
        CheckConstraint("btrim(normalized_name) <> ''", name="normalized_name_not_blank"),
        Index(
            "ix_actors_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, COALESCE(canonical_name, "
                "''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(description, "
                "''::text)), 'B'::\"char\")) || setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    actor_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    aliases: Mapped[list[Alias]] = orm_relationship(back_populates="actor")
    observations: Mapped[list[Observation]] = orm_relationship(
        secondary=actor_observations, back_populates="actors"
    )
    relationships: Mapped[list[Relationship]] = orm_relationship(back_populates="actor")
    alias_rules: Mapped[list[ActorAliasRule]] = orm_relationship(back_populates="actor")
    resolution_decisions: Mapped[list[ActorResolutionDecision]] = orm_relationship(
        back_populates="actor", foreign_keys="ActorResolutionDecision.actor_id"
    )


class Alias(IdMixin, TimestampMixin, Base):
    __tablename__ = "aliases"
    __table_args__ = (
        UniqueConstraint("source_id", "normalized_name"),
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        CheckConstraint("btrim(normalized_name) <> ''", name="normalized_name_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
        Index("ix_aliases_normalized_name", "normalized_name"),
        Index(
            "ix_aliases_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, COALESCE(name, "
                "''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(source_native_id, "
                "''::character varying)::text), 'C'::\"char\")) || "
                "setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("actors.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_native_id: Mapped[str | None] = mapped_column(String(512))
    confidence: Mapped[int | None] = mapped_column(Integer)
    alias_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="aliases")
    actor: Mapped[Actor | None] = orm_relationship(back_populates="aliases")
    resolution_decisions: Mapped[list[ActorResolutionDecision]] = orm_relationship(
        back_populates="alias"
    )


class ActorAliasRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "actor_alias_rules"
    __table_args__ = (
        CheckConstraint("btrim(alias_name) <> ''", name="alias_name_not_blank"),
        CheckConstraint("btrim(normalized_alias) <> ''", name="normalized_alias_not_blank"),
        CheckConstraint("btrim(reason) <> ''", name="reason_not_blank"),
        CheckConstraint("btrim(created_by) <> ''", name="created_by_not_blank"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="confidence_range"),
    )

    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    actor: Mapped[Actor] = orm_relationship(back_populates="alias_rules")
    evidence: Mapped[Evidence | None] = orm_relationship()


class ActorResolutionDecision(IdMixin, Base):
    __tablename__ = "actor_resolution_decisions"
    __table_args__ = (
        UniqueConstraint("alias_id", "decision_hash"),
        CheckConstraint("btrim(reason) <> ''", name="reason_not_blank"),
        CheckConstraint("btrim(decided_by) <> ''", name="decided_by_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
        CheckConstraint(
            "(decision IN ('auto_link', 'manual_link') AND actor_id IS NOT NULL) OR "
            "(decision IN ('unresolved', 'manual_unlink') AND actor_id IS NULL)",
            name="actor_shape",
        ),
        CheckConstraint("decision_hash ~ '^[0-9a-f]{64}$'", name="decision_hash_lower_hex"),
        Index("ix_actor_resolution_decisions_alias_sequence", "alias_id", "sequence"),
    )

    alias_id: Mapped[UUID] = mapped_column(
        ForeignKey("aliases.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("actors.id", ondelete="RESTRICT"))
    previous_actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("actors.id", ondelete="RESTRICT")
    )
    evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence.id", ondelete="RESTRICT"))
    decision: Mapped[ResolutionDecision] = mapped_column(resolution_decision_enum, nullable=False)
    method: Mapped[ResolutionMethod] = mapped_column(resolution_method_enum, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    decision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    alias: Mapped[Alias] = orm_relationship(back_populates="resolution_decisions")
    actor: Mapped[Actor | None] = orm_relationship(
        back_populates="resolution_decisions", foreign_keys=[actor_id]
    )
    previous_actor: Mapped[Actor | None] = orm_relationship(foreign_keys=[previous_actor_id])
    evidence: Mapped[Evidence | None] = orm_relationship()


class Observation(IdMixin, TimestampMixin, Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("source_id", "source_native_id"),
        CheckConstraint("btrim(title) <> ''", name="title_not_blank"),
        CheckConstraint("btrim(summary) <> ''", name="summary_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
        CheckConstraint(
            "first_seen IS NULL OR last_seen IS NULL OR first_seen <= last_seen",
            name="time_range_order",
        ),
        Index("ix_observations_observed_at", "observed_at"),
        Index("ix_observations_first_seen", "first_seen"),
        Index("ix_observations_last_seen", "last_seen"),
        Index("ix_observations_search_document", "search_document", postgresql_using="gin"),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raw_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_evidence.id", ondelete="RESTRICT"), index=True
    )
    source_native_id: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[int | None] = mapped_column(Integer)
    intelligence_type: Mapped[IntelligenceType] = mapped_column(
        intelligence_type_enum, nullable=False
    )
    origin: Mapped[Origin] = mapped_column(origin_enum, nullable=False)
    observation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    search_document: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english'::regconfig, coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english'::regconfig, coalesce(summary, '')), 'B') || "
            "setweight(to_tsvector('english'::regconfig, coalesce(source_native_id, '')), 'C') "
            "|| setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
            persisted=True,
        ),
        nullable=False,
    )

    source: Mapped[Source] = orm_relationship(back_populates="observations")
    raw_evidence: Mapped[RawEvidence | None] = orm_relationship(back_populates="observations")
    actors: Mapped[list[Actor]] = orm_relationship(
        secondary=actor_observations, back_populates="observations"
    )
    evidence: Mapped[list[Evidence]] = orm_relationship(
        secondary=observation_evidence, back_populates="observations"
    )
    behaviors: Mapped[list[Behavior]] = orm_relationship(
        secondary=observation_behaviors, back_populates="observations"
    )
    techniques: Mapped[list[Technique]] = orm_relationship(
        secondary=observation_techniques, back_populates="observations"
    )
    normalization_records: Mapped[list[NormalizationLedger]] = orm_relationship(
        back_populates="observation"
    )


class NormalizationLedger(IdMixin, TimestampMixin, Base):
    __tablename__ = "normalization_records"
    __table_args__ = (
        UniqueConstraint("raw_evidence_id", "object_index"),
        CheckConstraint("btrim(source_native_id) <> ''", name="source_native_id_not_blank"),
        CheckConstraint("btrim(object_type) <> ''", name="object_type_not_blank"),
        CheckConstraint("object_index >= 0", name="object_index_nonnegative"),
        CheckConstraint("payload_sha256 ~ '^[0-9a-f]{64}$'", name="payload_sha256_lower_hex"),
        CheckConstraint("attempts > 0", name="attempts_positive"),
        CheckConstraint(
            "status NOT IN ('rejected', 'failed') OR (reason IS NOT NULL AND btrim(reason) <> '')",
            name="failure_reason_present",
        ),
        Index("ix_normalization_records_source_native", "source_id", "source_native_id"),
        Index("ix_normalization_records_status", "status"),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    raw_evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("raw_evidence.id", ondelete="RESTRICT"), nullable=False
    )
    observation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT")
    )
    source_native_id: Mapped[str] = mapped_column(String(512), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[NormalizationStatus] = mapped_column(normalization_status_enum, nullable=False)
    stage: Mapped[NormalizationStage] = mapped_column(normalization_stage_enum, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = orm_relationship(back_populates="normalization_records")
    raw_evidence: Mapped[RawEvidence] = orm_relationship(back_populates="normalization_records")
    observation: Mapped[Observation | None] = orm_relationship(
        back_populates="normalization_records"
    )


class Evidence(IdMixin, TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint("btrim(citation) <> ''", name="citation_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raw_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_evidence.id", ondelete="RESTRICT"), index=True
    )
    citation: Mapped[str] = mapped_column(String(500), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    locator: Mapped[str | None] = mapped_column(String(1000))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    confidence: Mapped[int | None] = mapped_column(Integer)
    origin: Mapped[Origin] = mapped_column(origin_enum, nullable=False)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="evidence")
    raw_evidence: Mapped[RawEvidence | None] = orm_relationship(back_populates="evidence")
    observations: Mapped[list[Observation]] = orm_relationship(
        secondary=observation_evidence, back_populates="evidence"
    )
    relationships: Mapped[list[Relationship]] = orm_relationship(back_populates="evidence")
    embeddings: Mapped[list[EvidenceEmbedding]] = orm_relationship(back_populates="evidence")


class EvidenceEmbedding(IdMixin, TimestampMixin, Base):
    """Provider-neutral vector tied to the exact evidence and source it represents."""

    __tablename__ = "evidence_embeddings"
    __table_args__ = (
        UniqueConstraint("evidence_id", "embedding_model"),
        CheckConstraint("btrim(embedding_model) <> ''", name="embedding_model_not_blank"),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="content_sha256_lower_hex"),
        CheckConstraint("dimensions > 0", name="dimensions_positive"),
        Index("ix_evidence_embeddings_model_dimensions", "embedding_model", "dimensions"),
    )

    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(), nullable=False)

    evidence: Mapped[Evidence] = orm_relationship(back_populates="embeddings")
    source: Mapped[Source] = orm_relationship(back_populates="evidence_embeddings")


class TechnicalArtifact(IdMixin, TimestampMixin, Base):
    """Faithful structured technical artifact with validation and provenance."""

    __tablename__ = "technical_artifacts"
    __table_args__ = (
        UniqueConstraint("source_id", "artifact_type", "content_sha256"),
        CheckConstraint("btrim(canonical_id) <> ''", name="canonical_id_not_blank"),
        CheckConstraint("btrim(title) <> ''", name="title_not_blank"),
        CheckConstraint("btrim(original_content) <> ''", name="original_content_not_blank"),
        CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="content_sha256_lower_hex"),
        CheckConstraint(
            "origin <> 'imported' OR raw_evidence_id IS NOT NULL",
            name="imported_has_raw_evidence",
        ),
        Index("ix_technical_artifacts_type_status", "artifact_type", "validation_status"),
        Index(
            "ix_technical_artifacts_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, COALESCE(title, '')), 'A') || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(canonical_id, '')), 'A')) "
                "|| setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, '')), 'D'))"
            ),
            postgresql_using="gin",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    raw_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_evidence.id", ondelete="RESTRICT"), index=True
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(artifact_type_enum, nullable=False)
    origin: Mapped[Origin] = mapped_column(origin_enum, nullable=False)
    canonical_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_content: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    validation_status: Mapped[ArtifactValidationStatus] = mapped_column(
        artifact_validation_status_enum, nullable=False
    )
    validation_errors: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    artifact_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="technical_artifacts")
    raw_evidence: Mapped[RawEvidence | None] = orm_relationship(
        back_populates="technical_artifacts"
    )


class Behavior(IdMixin, TimestampMixin, Base):
    __tablename__ = "behaviors"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        CheckConstraint("btrim(normalized_name) <> ''", name="normalized_name_not_blank"),
        Index(
            "ix_behaviors_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, COALESCE(name, "
                "''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(description, "
                "''::text)), 'B'::\"char\")) || setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    behavior_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    observations: Mapped[list[Observation]] = orm_relationship(
        secondary=observation_behaviors, back_populates="behaviors"
    )


class Technique(IdMixin, TimestampMixin, Base):
    __tablename__ = "techniques"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id"),
        CheckConstraint("btrim(external_id) <> ''", name="external_id_not_blank"),
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        Index(
            "ix_techniques_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, "
                "(COALESCE(external_id, ''::character varying)::text || ' '::text) || "
                "COALESCE(name, ''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(description, "
                "''::text)), 'B'::\"char\")) || setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    technique_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="techniques")
    observations: Mapped[list[Observation]] = orm_relationship(
        secondary=observation_techniques, back_populates="techniques"
    )


class Campaign(IdMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("source_id", "normalized_name"),
        CheckConstraint("btrim(name) <> ''", name="name_not_blank"),
        CheckConstraint("btrim(normalized_name) <> ''", name="normalized_name_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
        CheckConstraint(
            "first_seen IS NULL OR last_seen IS NULL OR first_seen <= last_seen",
            name="time_range_order",
        ),
        Index("ix_campaigns_first_seen", "first_seen"),
        Index("ix_campaigns_last_seen", "last_seen"),
        Index(
            "ix_campaigns_search_document",
            text(
                "((setweight(to_tsvector('english'::regconfig, COALESCE(name, "
                "''::character varying)::text), 'A'::\"char\") || "
                "setweight(to_tsvector('english'::regconfig, COALESCE(description, "
                "''::text)), 'B'::\"char\")) || setweight(to_tsvector('english'::regconfig, "
                "COALESCE(metadata::text, ''::text)), 'D'::\"char\"))"
            ),
            postgresql_using="gin",
        ),
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_native_id: Mapped[str | None] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[int | None] = mapped_column(Integer)
    intelligence_type: Mapped[IntelligenceType] = mapped_column(
        intelligence_type_enum, nullable=False
    )
    origin: Mapped[Origin] = mapped_column(origin_enum, nullable=False)
    campaign_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    source: Mapped[Source] = orm_relationship(back_populates="campaigns")
    relationships: Mapped[list[Relationship]] = orm_relationship(back_populates="campaign")


class Relationship(IdMixin, TimestampMixin, Base):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint("actor_id", "relationship_type", "campaign_id", "source_id"),
        CheckConstraint("btrim(relationship_type) <> ''", name="type_not_blank"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100", name="confidence_range"
        ),
        CheckConstraint(
            "first_seen IS NULL OR last_seen IS NULL OR first_seen <= last_seen",
            name="time_range_order",
        ),
        Index("ix_relationships_first_seen", "first_seen"),
        Index("ix_relationships_last_seen", "last_seen"),
    )

    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evidence.id", ondelete="RESTRICT"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[int | None] = mapped_column(Integer)
    intelligence_type: Mapped[IntelligenceType] = mapped_column(
        intelligence_type_enum, nullable=False
    )
    origin: Mapped[Origin] = mapped_column(origin_enum, nullable=False)
    relationship_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    actor: Mapped[Actor] = orm_relationship(back_populates="relationships")
    campaign: Mapped[Campaign] = orm_relationship(back_populates="relationships")
    source: Mapped[Source] = orm_relationship(back_populates="relationships")
    evidence: Mapped[Evidence | None] = orm_relationship(back_populates="relationships")


advisory_revision_evidence = Table(
    "advisory_revision_evidence",
    Base.metadata,
    Column(
        "revision_id",
        Uuid,
        ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True),
)

advisory_revision_actors = Table(
    "advisory_revision_actors",
    Base.metadata,
    Column(
        "revision_id",
        Uuid,
        ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("actor_id", Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), primary_key=True),
)

advisory_revision_campaigns = Table(
    "advisory_revision_campaigns",
    Base.metadata,
    Column(
        "revision_id",
        Uuid,
        ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("campaign_id", Uuid, ForeignKey("campaigns.id", ondelete="RESTRICT"), primary_key=True),
)

advisory_revision_techniques = Table(
    "advisory_revision_techniques",
    Base.metadata,
    Column(
        "revision_id",
        Uuid,
        ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "technique_id", Uuid, ForeignKey("techniques.id", ondelete="RESTRICT"), primary_key=True
    ),
)

advisory_update_evidence = Table(
    "advisory_update_evidence",
    Base.metadata,
    Column(
        "update_id",
        Uuid,
        ForeignKey("advisory_updates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("evidence_id", Uuid, ForeignKey("evidence.id", ondelete="RESTRICT"), primary_key=True),
)


class Advisory(IdMixin, TimestampMixin, Base):
    __tablename__ = "advisories"
    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_safe_format"),
        CheckConstraint(
            "(status = 'draft' AND published_revision IS NULL AND published_at IS NULL) OR "
            "(status = 'published' AND published_revision IS NOT NULL AND "
            "published_at IS NOT NULL)",
            name="publication_shape",
        ),
        CheckConstraint(
            "published_revision IS NULL OR published_revision > 0",
            name="published_revision_positive",
        ),
        Index("ix_advisories_public", "status", "published_at", "id"),
    )

    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    status: Mapped[AdvisoryStatus] = mapped_column(
        advisory_status_enum,
        nullable=False,
        default=AdvisoryStatus.DRAFT,
        server_default=text("'draft'"),
    )
    published_revision: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    revisions: Mapped[list[AdvisoryRevision]] = orm_relationship(
        back_populates="advisory", cascade="all, delete-orphan"
    )
    updates: Mapped[list[AdvisoryUpdate]] = orm_relationship(
        back_populates="advisory", cascade="all, delete-orphan"
    )


class AdvisoryRevision(IdMixin, Base):
    __tablename__ = "advisory_revisions"
    __table_args__ = (
        UniqueConstraint("advisory_id", "version"),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint("btrim(title) <> ''", name="title_not_blank"),
        CheckConstraint("btrim(summary) <> ''", name="summary_not_blank"),
        CheckConstraint("btrim(created_by) <> ''", name="created_by_not_blank"),
        CheckConstraint(
            "(published_at IS NULL AND published_by IS NULL) OR "
            "(published_at IS NOT NULL AND published_by IS NOT NULL AND btrim(published_by) <> '')",
            name="publication_shape",
        ),
        Index("ix_advisory_revisions_publication", "advisory_id", "published_at", "version"),
    )

    advisory_id: Mapped[UUID] = mapped_column(
        ForeignKey("advisories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(255))

    advisory: Mapped[Advisory] = orm_relationship(back_populates="revisions")
    sections: Mapped[list[AdvisorySection]] = orm_relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        order_by="AdvisorySection.position",
    )
    evidence: Mapped[list[Evidence]] = orm_relationship(secondary=advisory_revision_evidence)
    actors: Mapped[list[Actor]] = orm_relationship(secondary=advisory_revision_actors)
    campaigns: Mapped[list[Campaign]] = orm_relationship(secondary=advisory_revision_campaigns)
    techniques: Mapped[list[Technique]] = orm_relationship(secondary=advisory_revision_techniques)
    updates: Mapped[list[AdvisoryUpdate]] = orm_relationship(back_populates="revision")


class AdvisorySection(IdMixin, Base):
    __tablename__ = "advisory_sections"
    __table_args__ = (
        UniqueConstraint(
            "revision_id", "section_type", name="uq_advisory_sections_revision_section_type"
        ),
        UniqueConstraint("revision_id", "position", name="uq_advisory_sections_revision_position"),
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint("btrim(content) <> ''", name="content_not_blank"),
    )

    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("advisory_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[AdvisorySectionType] = mapped_column(
        advisory_section_type_enum, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    intelligence_type: Mapped[IntelligenceType] = mapped_column(
        intelligence_type_enum, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    revision: Mapped[AdvisoryRevision] = orm_relationship(back_populates="sections")


class AdvisoryUpdate(IdMixin, Base):
    __tablename__ = "advisory_updates"
    __table_args__ = (
        UniqueConstraint("advisory_id", "sequence"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint("btrim(title) <> ''", name="title_not_blank"),
        CheckConstraint("btrim(summary) <> ''", name="summary_not_blank"),
        CheckConstraint("btrim(created_by) <> ''", name="created_by_not_blank"),
        Index("ix_advisory_updates_timeline", "advisory_id", "sequence"),
    )

    advisory_id: Mapped[UUID] = mapped_column(
        ForeignKey("advisories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("advisory_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    intelligence_type: Mapped[IntelligenceType] = mapped_column(
        intelligence_type_enum, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    advisory: Mapped[Advisory] = orm_relationship(back_populates="updates")
    revision: Mapped[AdvisoryRevision] = orm_relationship(back_populates="updates")
    evidence: Mapped[list[Evidence]] = orm_relationship(secondary=advisory_update_evidence)
