from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command
from app.core.config import get_settings
from app.infrastructure.ingestion.passages import create_passages
from app.infrastructure.ingestion.translations import (
    count_alignment,
    load_translation,
    parse_translation_json,
    seed_books,
)
from app.main import create_app

# Sl 2 com 6 versículos em todas; Jo 2 com 2 versículos só na VFL (capítulo VFL reprovado → fallback NVT)
COMMON = {(19, 2): 6}

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url_test)
    return cfg


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[str]:
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield get_settings().database_url_test


@pytest.fixture
async def db_session(migrated_db: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_db)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as c:
        yield c


@pytest.fixture
async def bible_db(db_session: AsyncSession, tmp_path: Path) -> AsyncSession:
    from tests.ingestion.helpers import synthetic_bible, write_json

    await seed_books(db_session, {b: 2 for b in range(1, 67)})
    for code, extra in (("acf", {}), ("nvt", {}), ("vfl", {(43, 2): 2})):
        rows = parse_translation_json(write_json(tmp_path / f"{code}.json", synthetic_bible({**COMMON, **extra})))
        await load_translation(db_session, code, rows)
    for code in ("acf", "nvt", "vfl"):
        await count_alignment(db_session, code)
        await create_passages(db_session, code)
    return db_session
