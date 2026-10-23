"""Add searchable indicators, vulnerabilities and actor associations.

Revision ID: f6a1c2d3e4b5
Revises: 4c7d9e2a1b5f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a1c2d3e4b5"
down_revision: str | Sequence[str] | None = "4c7d9e2a1b5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

indicator_type = postgresql.ENUM(
    "ipv4",
    "ipv6",
    "domain",
    "url",
    "email",
    "md5",
    "sha1",
    "sha256",
    name="indicator_type",
    create_type=False,
)
publication_state = postgresql.ENUM(
    "internal", "published", name="publication_state", create_type=False
)
intelligence_type = postgresql.ENUM(
    "observed", "assessed", name="intelligence_type", create_type=False
)
intelligence_origin = postgresql.ENUM(
    "imported", "watchtower", name="intelligence_origin", create_type=False
)


def upgrade() -> None:
    indicator_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "indicators",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("indicator_type", indicator_type, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.Integer()),
        sa.Column("intelligence_type", intelligence_type, nullable=False),
        sa.Column("origin", intelligence_origin, nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "search_document",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple'::regconfig, coalesce(value, '')), 'A') || "
                "setweight(to_tsvector('english'::regconfig, coalesce(description, '')), 'B') || "
                "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "publication_state",
            publication_state,
            server_default=sa.text("'internal'"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(value) <> ''", name="ck_indicators_value_not_blank"),
        sa.CheckConstraint(
            "btrim(normalized_value) <> ''", name="ck_indicators_normalized_value_not_blank"
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 100",
            name="ck_indicators_confidence_range",
        ),
        sa.CheckConstraint(
            "first_seen IS NULL OR last_seen IS NULL OR first_seen <= last_seen",
            name="ck_indicators_time_range_order",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "indicator_type",
            "normalized_value",
            name="uq_indicators_source_type_value",
        ),
    )
    op.create_index("ix_indicators_source_id", "indicators", ["source_id"])
    op.create_index("ix_indicators_first_seen", "indicators", ["first_seen"])
    op.create_index("ix_indicators_last_seen", "indicators", ["last_seen"])
    op.create_index("ix_indicators_publication_state", "indicators", ["publication_state"])
    op.create_index(
        "ix_indicators_search_document",
        "indicators",
        ["search_document"],
        postgresql_using="gin",
    )

    op.create_table(
        "vulnerabilities",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("cve_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("severity", sa.String(length=20)),
        sa.Column("cvss_score", sa.Float()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("modified_at", sa.DateTime(timezone=True)),
        sa.Column("intelligence_type", intelligence_type, nullable=False),
        sa.Column("origin", intelligence_origin, nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "search_document",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple'::regconfig, coalesce(cve_id, '')), 'A') || "
                "setweight(to_tsvector('english'::regconfig, coalesce(title, '') || ' ' || "
                "coalesce(description, '')), 'B') || setweight(to_tsvector('english'::regconfig, "
                "coalesce(metadata::text, '')), 'D')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "publication_state",
            publication_state,
            server_default=sa.text("'internal'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cve_id ~ '^CVE-[0-9]{4}-[0-9]{4,}$'", name="ck_vulnerabilities_cve_id_format"
        ),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_vulnerabilities_title_not_blank"),
        sa.CheckConstraint(
            "cvss_score IS NULL OR cvss_score BETWEEN 0 AND 10",
            name="ck_vulnerabilities_cvss_range",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN ('unknown', 'low', 'medium', 'high', 'critical')",
            name="ck_vulnerabilities_severity_value",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "cve_id", name="uq_vulnerabilities_source_cve"),
    )
    op.create_index("ix_vulnerabilities_source_id", "vulnerabilities", ["source_id"])
    op.create_index("ix_vulnerabilities_cve_id", "vulnerabilities", ["cve_id"])
    op.create_index("ix_vulnerabilities_published_at", "vulnerabilities", ["published_at"])
    op.create_index(
        "ix_vulnerabilities_publication_state", "vulnerabilities", ["publication_state"]
    )
    op.create_index(
        "ix_vulnerabilities_search_document",
        "vulnerabilities",
        ["search_document"],
        postgresql_using="gin",
    )

    op.create_table(
        "actor_indicators",
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("indicator_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("actor_id", "indicator_id"),
    )
    op.create_index("ix_actor_indicators_indicator_id", "actor_indicators", ["indicator_id"])

    op.create_table(
        "actor_vulnerabilities",
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("vulnerability_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vulnerability_id"], ["vulnerabilities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("actor_id", "vulnerability_id"),
    )
    op.create_index(
        "ix_actor_vulnerabilities_vulnerability_id",
        "actor_vulnerabilities",
        ["vulnerability_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_actor_vulnerabilities_vulnerability_id", table_name="actor_vulnerabilities")
    op.drop_table("actor_vulnerabilities")
    op.drop_index("ix_actor_indicators_indicator_id", table_name="actor_indicators")
    op.drop_table("actor_indicators")
    op.drop_table("vulnerabilities")
    op.drop_table("indicators")
    indicator_type.drop(op.get_bind(), checkfirst=True)
