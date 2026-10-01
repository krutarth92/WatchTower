"""add actor resolution audit

Revision ID: e4b8c1d2a6f0
Revises: d7a9b2f1c4e8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4b8c1d2a6f0"
down_revision: str | Sequence[str] | None = "d7a9b2f1c4e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

resolution_decision = postgresql.ENUM(
    "auto_link",
    "unresolved",
    "manual_link",
    "manual_unlink",
    name="resolution_decision",
    create_type=False,
)
resolution_method = postgresql.ENUM(
    "exact_actor_name",
    "known_alias",
    "exact_candidates",
    "ambiguous_exact",
    "similarity_candidates",
    "no_match",
    "existing_link",
    "manual",
    name="resolution_method",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    resolution_decision.create(bind, checkfirst=True)
    resolution_method.create(bind, checkfirst=True)
    op.create_table(
        "actor_alias_rules",
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "btrim(alias_name) <> ''", name=op.f("ck_actor_alias_rules_alias_name_not_blank")
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name=op.f("ck_actor_alias_rules_confidence_range"),
        ),
        sa.CheckConstraint(
            "btrim(created_by) <> ''", name=op.f("ck_actor_alias_rules_created_by_not_blank")
        ),
        sa.CheckConstraint(
            "btrim(normalized_alias) <> ''",
            name=op.f("ck_actor_alias_rules_normalized_alias_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''", name=op.f("ck_actor_alias_rules_reason_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["actors.id"],
            name=op.f("fk_actor_alias_rules_actor_id_actors"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name=op.f("fk_actor_alias_rules_evidence_id_evidence"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_actor_alias_rules")),
        sa.UniqueConstraint("normalized_alias", name=op.f("uq_actor_alias_rules_normalized_alias")),
    )
    op.create_index(
        op.f("ix_actor_alias_rules_actor_id"), "actor_alias_rules", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_actor_alias_rules_evidence_id"),
        "actor_alias_rules",
        ["evidence_id"],
        unique=False,
    )
    op.create_table(
        "actor_resolution_decisions",
        sa.Column("alias_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("previous_actor_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("decision", resolution_decision, nullable=False),
        sa.Column("method", resolution_method, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("decided_by", sa.String(length=255), nullable=False),
        sa.Column(
            "candidates",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("decision_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "sequence",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(decision IN ('auto_link', 'manual_link') AND actor_id IS NOT NULL) OR "
            "(decision IN ('unresolved', 'manual_unlink') AND actor_id IS NULL)",
            name=op.f("ck_actor_resolution_decisions_actor_shape"),
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100",
            name=op.f("ck_actor_resolution_decisions_confidence_range"),
        ),
        sa.CheckConstraint(
            "btrim(decided_by) <> ''",
            name=op.f("ck_actor_resolution_decisions_decided_by_not_blank"),
        ),
        sa.CheckConstraint(
            "decision_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_actor_resolution_decisions_decision_hash_lower_hex"),
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''", name=op.f("ck_actor_resolution_decisions_reason_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["actors.id"],
            name=op.f("fk_actor_resolution_decisions_actor_id_actors"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["alias_id"],
            ["aliases.id"],
            name=op.f("fk_actor_resolution_decisions_alias_id_aliases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            name=op.f("fk_actor_resolution_decisions_evidence_id_evidence"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["previous_actor_id"],
            ["actors.id"],
            name=op.f("fk_actor_resolution_decisions_previous_actor_id_actors"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_actor_resolution_decisions")),
        sa.UniqueConstraint(
            "alias_id",
            "decision_hash",
            name=op.f("uq_actor_resolution_decisions_alias_id"),
        ),
        sa.UniqueConstraint("sequence", name=op.f("uq_actor_resolution_decisions_sequence")),
    )
    op.create_index(
        "ix_actor_resolution_decisions_alias_sequence",
        "actor_resolution_decisions",
        ["alias_id", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_actor_resolution_decisions_alias_sequence",
        table_name="actor_resolution_decisions",
    )
    op.drop_table("actor_resolution_decisions")
    op.drop_index(op.f("ix_actor_alias_rules_evidence_id"), table_name="actor_alias_rules")
    op.drop_index(op.f("ix_actor_alias_rules_actor_id"), table_name="actor_alias_rules")
    op.drop_table("actor_alias_rules")
    bind = op.get_bind()
    resolution_method.drop(bind, checkfirst=True)
    resolution_decision.drop(bind, checkfirst=True)
