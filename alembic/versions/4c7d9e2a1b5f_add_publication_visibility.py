"""Add fail-closed publication visibility to public intelligence records.

Revision ID: 4c7d9e2a1b5f
Revises: 0218f83cad8e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4c7d9e2a1b5f"
down_revision: str | Sequence[str] | None = "0218f83cad8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

publication_state = postgresql.ENUM(
    "internal", "published", name="publication_state", create_type=False
)
PUBLIC_TABLES = (
    "sources",
    "actors",
    "aliases",
    "observations",
    "evidence",
    "behaviors",
    "techniques",
    "campaigns",
)


def upgrade() -> None:
    bind = op.get_bind()
    publication_state.create(bind, checkfirst=True)
    for table in PUBLIC_TABLES:
        op.add_column(
            table,
            sa.Column(
                "publication_state",
                publication_state,
                server_default=sa.text("'internal'"),
                nullable=False,
            ),
        )
        op.create_index(f"ix_{table}_publication_state", table, ["publication_state"], unique=False)


def downgrade() -> None:
    for table in reversed(PUBLIC_TABLES):
        op.drop_index(f"ix_{table}_publication_state", table_name=table)
        op.drop_column(table, "publication_state")
    publication_state.drop(op.get_bind(), checkfirst=True)
