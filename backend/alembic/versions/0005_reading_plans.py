"""reading plans

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-06 14:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reading_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plan_days_done",
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["reading_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("plan_id", "day"),
    )


def downgrade() -> None:
    op.drop_table("plan_days_done")
    op.drop_table("reading_plans")
