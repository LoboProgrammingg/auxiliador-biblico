from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from tests.conftest import alembic_config

EXPECTED_TABLES = {
    "books",
    "translations",
    "verses",
    "chapter_alignment",
    "passages",
    "original_words",
    "lexicon",
    "cross_references",
    "conversations",
    "messages",
    "memories",
    "ingestion_checkpoints",
}


async def test_schema_has_all_tables_and_extensions(db_session: AsyncSession) -> None:
    rows = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    assert EXPECTED_TABLES <= {r[0] for r in rows}
    ext = await db_session.execute(text("SELECT extname FROM pg_extension"))
    assert {"vector", "unaccent"} <= {r[0] for r in ext}
    dims = await db_session.execute(
        text("SELECT atttypmod FROM pg_attribute WHERE attrelid = 'passages'::regclass AND attname = 'embedding'")
    )
    assert dims.scalar_one() == 1024


async def test_unaccent_portuguese_tsvector_works(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT to_tsvector('portuguese', unaccent('Não vivam ansiosos')) "
            "@@ plainto_tsquery('portuguese', unaccent('ansioso'))"
        )
    )
    assert result.scalar_one() is True


def test_downgrade_then_upgrade_is_clean(migrated_db: str) -> None:
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
