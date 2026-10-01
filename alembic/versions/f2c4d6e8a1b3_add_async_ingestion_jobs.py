"""add async ingestion jobs

Revision ID: f2c4d6e8a1b3
Revises: e4b8c1d2a6f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2c4d6e8a1b3"
down_revision: str | Sequence[str] | None = "e4b8c1d2a6f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_kind = postgresql.ENUM(
    "mitre_attack_refresh",
    name="ingestion_job_kind",
    create_type=False,
)
job_state = postgresql.ENUM(
    "queued",
    "processing",
    "succeeded",
    "failed",
    name="ingestion_job_state",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    job_kind.create(bind, checkfirst=True)
    job_state.create(bind, checkfirst=True)
    op.create_table(
        "ingestion_jobs",
        sa.Column("job_kind", job_kind, nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("raw_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("state", job_state, server_default=sa.text("'queued'"), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name=op.f("ck_ingestion_jobs_attempts_nonnegative"),
        ),
        sa.CheckConstraint(
            "attempts <= max_attempts",
            name=op.f("ck_ingestion_jobs_attempts_within_limit"),
        ),
        sa.CheckConstraint(
            "btrim(correlation_id) <> ''",
            name=op.f("ck_ingestion_jobs_correlation_id_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(idempotency_key) <> ''",
            name=op.f("ck_ingestion_jobs_idempotency_key_not_blank"),
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 10",
            name=op.f("ck_ingestion_jobs_max_attempts_range"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_ingestion_jobs_state_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_evidence_id"],
            ["raw_evidence.id"],
            name=op.f("fk_ingestion_jobs_raw_evidence_id_raw_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_ingestion_jobs_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
        sa.UniqueConstraint(
            "job_kind",
            "idempotency_key",
            name=op.f("uq_ingestion_jobs_job_kind"),
        ),
    )
    op.create_index(
        op.f("ix_ingestion_jobs_next_attempt_at"),
        "ingestion_jobs",
        ["next_attempt_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_jobs_raw_evidence_id"),
        "ingestion_jobs",
        ["raw_evidence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_jobs_source_id"),
        "ingestion_jobs",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_processing_lease",
        "ingestion_jobs",
        ["state", "lease_expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_state_due",
        "ingestion_jobs",
        ["state", "next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_state_due", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_processing_lease", table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_source_id"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_raw_evidence_id"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_next_attempt_at"), table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    bind = op.get_bind()
    job_state.drop(bind, checkfirst=True)
    job_kind.drop(bind, checkfirst=True)
