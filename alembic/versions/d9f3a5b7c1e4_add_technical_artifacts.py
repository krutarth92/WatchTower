"""add faithful technical artifact storage

Revision ID: d9f3a5b7c1e4
Revises: c8e2f4a6b9d1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d9f3a5b7c1e4"
down_revision: str | Sequence[str] | None = "c8e2f4a6b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

artifact_type = postgresql.ENUM(
    "stix_2_1", "sigma", "attack_technique", name="artifact_type", create_type=False
)
validation_status = postgresql.ENUM(
    "valid", "invalid", name="artifact_validation_status", create_type=False
)
origin = postgresql.ENUM("imported", "watchtower", name="intelligence_origin", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    artifact_type.create(bind, checkfirst=True)
    validation_status.create(bind, checkfirst=True)
    op.create_table(
        "technical_artifacts",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("raw_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("artifact_type", artifact_type, nullable=False),
        sa.Column("origin", origin, nullable=False),
        sa.Column("canonical_id", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("structured_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_status", validation_status, nullable=False),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(canonical_id) <> ''", name="canonical_id_not_blank"),
        sa.CheckConstraint("btrim(title) <> ''", name="title_not_blank"),
        sa.CheckConstraint("btrim(original_content) <> ''", name="original_content_not_blank"),
        sa.CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="content_sha256_lower_hex"),
        sa.CheckConstraint(
            "origin <> 'imported' OR raw_evidence_id IS NOT NULL",
            name="imported_has_raw_evidence",
        ),
        sa.ForeignKeyConstraint(["raw_evidence_id"], ["raw_evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "artifact_type", "content_sha256"),
    )
    op.create_index("ix_technical_artifacts_source_id", "technical_artifacts", ["source_id"])
    op.create_index(
        "ix_technical_artifacts_raw_evidence_id", "technical_artifacts", ["raw_evidence_id"]
    )
    op.create_index(
        "ix_technical_artifacts_type_status",
        "technical_artifacts",
        ["artifact_type", "validation_status"],
    )
    op.create_index(
        "ix_technical_artifacts_search_document",
        "technical_artifacts",
        [
            sa.text(
                "((setweight(to_tsvector('english'::regconfig, coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('english'::regconfig, coalesce(canonical_id, '')), 'A')) "
                "|| setweight(to_tsvector('english'::regconfig, "
                "coalesce(metadata::text, '')), 'D'))"
            )
        ],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_technical_artifacts_search_document", table_name="technical_artifacts")
    op.drop_index("ix_technical_artifacts_type_status", table_name="technical_artifacts")
    op.drop_index("ix_technical_artifacts_raw_evidence_id", table_name="technical_artifacts")
    op.drop_index("ix_technical_artifacts_source_id", table_name="technical_artifacts")
    op.drop_table("technical_artifacts")
    validation_status.drop(op.get_bind(), checkfirst=True)
    artifact_type.drop(op.get_bind(), checkfirst=True)
