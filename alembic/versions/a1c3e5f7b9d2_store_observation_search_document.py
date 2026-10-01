"""store the measured observation search document

Revision ID: a1c3e5f7b9d2
Revises: d9f3a5b7c1e4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1c3e5f7b9d2"
down_revision: str | Sequence[str] | None = "d9f3a5b7c1e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_DOCUMENT = (
    "setweight(to_tsvector('english'::regconfig, coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(summary, '')), 'B') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(source_native_id, '')), 'C') || "
    "setweight(to_tsvector('english'::regconfig, coalesce(metadata::text, '')), 'D')"
)


def upgrade() -> None:
    op.drop_index("ix_observations_search_document", table_name="observations")
    op.add_column(
        "observations",
        sa.Column(
            "search_document",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_DOCUMENT, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_observations_search_document",
        "observations",
        ["search_document"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_observations_search_document", table_name="observations")
    op.drop_column("observations", "search_document")
    op.create_index(
        "ix_observations_search_document",
        "observations",
        [sa.text(f"({SEARCH_DOCUMENT})")],
        postgresql_using="gin",
    )
