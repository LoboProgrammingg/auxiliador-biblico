"""physical geography (Natural Earth)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "geo_features",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("points", postgresql.JSONB(), nullable=False),
        sa.Column("min_lon", sa.Double(), nullable=False),
        sa.Column("min_lat", sa.Double(), nullable=False),
        sa.Column("max_lon", sa.Double(), nullable=False),
        sa.Column("max_lat", sa.Double(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("geo_features")
