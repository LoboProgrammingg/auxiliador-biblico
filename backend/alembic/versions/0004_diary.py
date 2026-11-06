"""diary: prayer requests and verse notes

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-06 14:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prayer_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="aberto", nullable=False),
        sa.Column("answer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('aberto','respondido')", name="ck_prayer_requests_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "verse_notes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=False),
        sa.Column("book_id", sa.SmallInteger(), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("verse_start", sa.Integer(), nullable=False),
        sa.Column("verse_end", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "chapter", "verse_start", "verse_end", name="uq_verse_notes_range"),
    )


def downgrade() -> None:
    op.drop_table("verse_notes")
    op.drop_table("prayer_requests")
