"""add normalization ledger

Revision ID: d7a9b2f1c4e8
Revises: 83c89c27e40c
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7a9b2f1c4e8"
down_revision: str | Sequence[str] | None = "83c89c27e40c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

normalization_status = postgresql.ENUM(
    "processing",
    "succeeded",
    "deduplicated",
    "rejected",
    "failed",
    name="normalization_status",
    create_type=False,
)
normalization_stage = postgresql.ENUM(
    "parse",
    "normalize",
    "validate",
    "deduplicate",
    "persist",
    name="normalization_stage",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    normalization_status.create(bind, checkfirst=True)
    normalization_stage.create(bind, checkfirst=True)
    op.create_table(
        "normalization_records",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("raw_evidence_id", sa.Uuid(), nullable=False),
        sa.Column("observation_id", sa.Uuid(), nullable=True),
        sa.Column("source_native_id", sa.String(length=512), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_index", sa.Integer(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", normalization_status, nullable=False),
        sa.Column("stage", normalization_stage, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status NOT IN ('rejected', 'failed') OR (reason IS NOT NULL AND btrim(reason) <> '')",
            name=op.f("ck_normalization_records_failure_reason_present"),
        ),
        sa.CheckConstraint(
            "object_index >= 0",
            name=op.f("ck_normalization_records_object_index_nonnegative"),
        ),
        sa.CheckConstraint(
            "btrim(object_type) <> ''",
            name=op.f("ck_normalization_records_object_type_not_blank"),
        ),
        sa.CheckConstraint(
            "payload_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_normalization_records_payload_sha256_lower_hex"),
        ),
        sa.CheckConstraint(
            "btrim(source_native_id) <> ''",
            name=op.f("ck_normalization_records_source_native_id_not_blank"),
        ),
        sa.CheckConstraint("attempts > 0", name=op.f("ck_normalization_records_attempts_positive")),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observations.id"],
            name=op.f("fk_normalization_records_observation_id_observations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_evidence_id"],
            ["raw_evidence.id"],
            name=op.f("fk_normalization_records_raw_evidence_id_raw_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_normalization_records_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_normalization_records")),
        sa.UniqueConstraint(
            "raw_evidence_id",
            "object_index",
            name=op.f("uq_normalization_records_raw_evidence_id"),
        ),
    )
    op.create_index(
        "ix_normalization_records_source_native",
        "normalization_records",
        ["source_id", "source_native_id"],
        unique=False,
    )
    op.create_index(
        "ix_normalization_records_status",
        "normalization_records",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_normalization_records_status", table_name="normalization_records")
    op.drop_index("ix_normalization_records_source_native", table_name="normalization_records")
    op.drop_table("normalization_records")
    bind = op.get_bind()
    normalization_stage.drop(bind, checkfirst=True)
    normalization_status.drop(bind, checkfirst=True)
