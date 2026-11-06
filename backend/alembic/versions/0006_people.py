"""biblical people (STEPBible TIPNR)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-06 15:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.Column("name_pt", sa.String(length=120), nullable=True),
        sa.Column("brief", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "person_relations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("person_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("other_id", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_person_relations_person", "person_relations", ["person_id"])
    op.create_table(
        "person_verses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("person_id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.SmallInteger(), nullable=False),
        sa.Column("chapter", sa.Integer(), nullable=False),
        sa.Column("verse", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_person_verses_ref", "person_verses", ["book_id", "chapter", "verse"])


def downgrade() -> None:
    op.drop_index("ix_person_verses_ref", table_name="person_verses")
    op.drop_table("person_verses")
    op.drop_index("ix_person_relations_person", table_name="person_relations")
    op.drop_table("person_relations")
    op.drop_table("people")
