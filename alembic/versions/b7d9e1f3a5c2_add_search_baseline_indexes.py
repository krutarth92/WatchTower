"""add deterministic search baseline indexes

Revision ID: b7d9e1f3a5c2
Revises: f2c4d6e8a1b3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d9e1f3a5c2"
down_revision: str | Sequence[str] | None = "f2c4d6e8a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_INDEXES = {
    "sources": (
        "ix_sources_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(kind, '') || ' ' || "
        "coalesce(policy_notes, '') || ' ' || coalesce(license_name, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "actors": (
        "ix_actors_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(canonical_name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(description, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "aliases": (
        "ix_aliases_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(source_native_id, '')), 'C') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "campaigns": (
        "ix_campaigns_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(description, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "behaviors": (
        "ix_behaviors_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(description, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "techniques": (
        "ix_techniques_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(external_id, '') || ' ' || "
        "coalesce(name, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(description, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
    "observations": (
        "ix_observations_search_document",
        "setweight(to_tsvector('english'::regconfig, coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(summary, '')), 'B') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(source_native_id, '')), 'C') || "
        "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')",
    ),
}


def upgrade() -> None:
    for table_name, (index_name, expression) in SEARCH_INDEXES.items():
        op.create_index(
            index_name,
            table_name,
            [sa.text(f"({expression})")],
            unique=False,
            postgresql_using="gin",
        )


def downgrade() -> None:
    for table_name, (index_name, _) in reversed(SEARCH_INDEXES.items()):
        op.drop_index(index_name, table_name=table_name)
