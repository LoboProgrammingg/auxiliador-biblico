"""message status

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 13:40:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("status", sa.String(length=12), server_default="ok", nullable=False))


def downgrade() -> None:
    op.drop_column("messages", "status")
