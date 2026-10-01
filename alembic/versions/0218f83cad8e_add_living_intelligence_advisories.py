"""Add append-only living intelligence advisories.

Revision ID: 0218f83cad8e
Revises: a1c3e5f7b9d2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0218f83cad8e"
down_revision: str | Sequence[str] | None = "a1c3e5f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

advisory_status = postgresql.ENUM("draft", "published", name="advisory_status", create_type=False)
section_type = postgresql.ENUM(
    "what_happened",
    "actor_context",
    "technical_analysis",
    "detection",
    "response",
    "mitigation",
    "watchtower_assessment",
    name="advisory_section_type",
    create_type=False,
)
intelligence_type = postgresql.ENUM(
    "observed", "assessed", name="intelligence_type", create_type=False
)


def _revision_link(table: str, target: str, column: str) -> None:
    op.create_table(
        table,
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            column,
            sa.Uuid(),
            sa.ForeignKey(f"{target}.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    advisory_status.create(bind, checkfirst=True)
    section_type.create(bind, checkfirst=True)
    op.create_table(
        "advisories",
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("status", advisory_status, server_default=sa.text("'draft'"), nullable=False),
        sa.Column("published_revision", sa.Integer()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="ck_advisories_slug_safe_format"
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND published_revision IS NULL AND published_at IS NULL) OR "
            "(status = 'published' AND published_revision IS NOT NULL "
            "AND published_at IS NOT NULL)",
            name="ck_advisories_publication_shape",
        ),
        sa.CheckConstraint(
            "published_revision IS NULL OR published_revision > 0",
            name="ck_advisories_published_revision_positive",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_advisories"),
        sa.UniqueConstraint("slug", name="uq_advisories_slug"),
    )
    op.create_index("ix_advisories_public", "advisories", ["status", "published_at", "id"])
    op.create_index("ix_advisories_published_at", "advisories", ["published_at"])
    op.create_table(
        "advisory_revisions",
        sa.Column(
            "advisory_id",
            sa.Uuid(),
            sa.ForeignKey("advisories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_by", sa.String(255)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_advisory_revisions_version_positive"),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_advisory_revisions_title_not_blank"),
        sa.CheckConstraint("btrim(summary) <> ''", name="ck_advisory_revisions_summary_not_blank"),
        sa.CheckConstraint(
            "btrim(created_by) <> ''", name="ck_advisory_revisions_created_by_not_blank"
        ),
        sa.CheckConstraint(
            "(published_at IS NULL AND published_by IS NULL) OR "
            "(published_at IS NOT NULL AND published_by IS NOT NULL "
            "AND btrim(published_by) <> '')",
            name="ck_advisory_revisions_publication_shape",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_advisory_revisions"),
        sa.UniqueConstraint("advisory_id", "version", name="uq_advisory_revisions_advisory_id"),
    )
    op.create_index(
        "ix_advisory_revisions_publication",
        "advisory_revisions",
        ["advisory_id", "published_at", "version"],
    )
    op.create_index("ix_advisory_revisions_advisory_id", "advisory_revisions", ["advisory_id"])
    op.create_table(
        "advisory_sections",
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("advisory_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", section_type, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("intelligence_type", intelligence_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_advisory_sections_position_nonnegative"),
        sa.CheckConstraint("btrim(content) <> ''", name="ck_advisory_sections_content_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_advisory_sections"),
        sa.UniqueConstraint(
            "revision_id",
            "section_type",
            name="uq_advisory_sections_revision_section_type",
        ),
        sa.UniqueConstraint(
            "revision_id", "position", name="uq_advisory_sections_revision_position"
        ),
    )
    op.create_index("ix_advisory_sections_revision_id", "advisory_sections", ["revision_id"])
    _revision_link("advisory_revision_evidence", "evidence", "evidence_id")
    _revision_link("advisory_revision_actors", "actors", "actor_id")
    _revision_link("advisory_revision_campaigns", "campaigns", "campaign_id")
    _revision_link("advisory_revision_techniques", "techniques", "technique_id")
    op.create_table(
        "advisory_updates",
        sa.Column(
            "advisory_id",
            sa.Uuid(),
            sa.ForeignKey("advisories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("advisory_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("intelligence_type", intelligence_type, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_advisory_updates_sequence_positive"),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_advisory_updates_title_not_blank"),
        sa.CheckConstraint("btrim(summary) <> ''", name="ck_advisory_updates_summary_not_blank"),
        sa.CheckConstraint(
            "btrim(created_by) <> ''", name="ck_advisory_updates_created_by_not_blank"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_advisory_updates"),
        sa.UniqueConstraint("advisory_id", "sequence", name="uq_advisory_updates_advisory_id"),
    )
    op.create_index("ix_advisory_updates_advisory_id", "advisory_updates", ["advisory_id"])
    op.create_index("ix_advisory_updates_revision_id", "advisory_updates", ["revision_id"])
    op.create_index("ix_advisory_updates_timeline", "advisory_updates", ["advisory_id", "sequence"])
    op.create_table(
        "advisory_update_evidence",
        sa.Column(
            "update_id",
            sa.Uuid(),
            sa.ForeignKey("advisory_updates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            sa.ForeignKey("evidence.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("advisory_update_evidence")
    op.drop_index("ix_advisory_updates_timeline", table_name="advisory_updates")
    op.drop_index("ix_advisory_updates_revision_id", table_name="advisory_updates")
    op.drop_index("ix_advisory_updates_advisory_id", table_name="advisory_updates")
    op.drop_table("advisory_updates")
    op.drop_table("advisory_revision_techniques")
    op.drop_table("advisory_revision_campaigns")
    op.drop_table("advisory_revision_actors")
    op.drop_table("advisory_revision_evidence")
    op.drop_index("ix_advisory_sections_revision_id", table_name="advisory_sections")
    op.drop_table("advisory_sections")
    op.drop_index("ix_advisory_revisions_advisory_id", table_name="advisory_revisions")
    op.drop_index("ix_advisory_revisions_publication", table_name="advisory_revisions")
    op.drop_table("advisory_revisions")
    op.drop_index("ix_advisories_published_at", table_name="advisories")
    op.drop_index("ix_advisories_public", table_name="advisories")
    op.drop_table("advisories")
    bind = op.get_bind()
    section_type.drop(bind, checkfirst=True)
    advisory_status.drop(bind, checkfirst=True)
