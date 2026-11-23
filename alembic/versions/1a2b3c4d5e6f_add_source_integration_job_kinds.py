"""Add approved source integration job kinds.

Revision ID: 1a2b3c4d5e6f
Revises: f6a1c2d3e4b5
"""

from collections.abc import Sequence

from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "f6a1c2d3e4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_VALUES = (
    "misp_galaxy_refresh",
    "cisa_kev_refresh",
    "microsoft_threat_intelligence_refresh",
    "unit_42_refresh",
    "the_hacker_news_refresh",
)


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE ingestion_job_kind ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    values = ", ".join(f"'{value}'" for value in NEW_VALUES)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM ingestion_jobs WHERE job_kind::text IN ({values})
            ) THEN
                RAISE EXCEPTION
                    'Cannot remove source integration job kinds while matching jobs exist';
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE ingestion_jobs ALTER COLUMN job_kind TYPE text USING job_kind::text")
    op.execute("DROP TYPE ingestion_job_kind")
    op.execute("CREATE TYPE ingestion_job_kind AS ENUM ('mitre_attack_refresh')")
    op.execute(
        "ALTER TABLE ingestion_jobs ALTER COLUMN job_kind TYPE ingestion_job_kind "
        "USING job_kind::ingestion_job_kind"
    )
