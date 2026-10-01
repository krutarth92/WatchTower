"""add provenance-linked evidence embeddings

Revision ID: c8e2f4a6b9d1
Revises: b7d9e1f3a5c2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "c8e2f4a6b9d1"
down_revision: str | Sequence[str] | None = "b7d9e1f3a5c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "evidence_embeddings",
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("btrim(embedding_model) <> ''", name="embedding_model_not_blank"),
        sa.CheckConstraint("content_sha256 ~ '^[0-9a-f]{64}$'", name="content_sha256_lower_hex"),
        sa.CheckConstraint("dimensions > 0", name="dimensions_positive"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", "embedding_model"),
    )
    op.create_index("ix_evidence_embeddings_evidence_id", "evidence_embeddings", ["evidence_id"])
    op.create_index("ix_evidence_embeddings_source_id", "evidence_embeddings", ["source_id"])
    op.create_index(
        "ix_evidence_embeddings_model_dimensions",
        "evidence_embeddings",
        ["embedding_model", "dimensions"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_embeddings_model_dimensions", table_name="evidence_embeddings")
    op.drop_index("ix_evidence_embeddings_source_id", table_name="evidence_embeddings")
    op.drop_index("ix_evidence_embeddings_evidence_id", table_name="evidence_embeddings")
    op.drop_table("evidence_embeddings")
