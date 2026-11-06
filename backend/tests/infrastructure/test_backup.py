import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.infrastructure.backup import BackupError, backup_name, create_backup, restore_backup, to_prune


def test_prune_keeps_last_30_days(tmp_path: Path) -> None:
    today = date(2026, 11, 6)
    files = [tmp_path / backup_name(today - timedelta(days=n)) for n in range(40)]
    other = tmp_path / "manual-antes-v3.dump"
    pruned = to_prune([*files, other], today, keep_days=30)
    assert sorted(pruned) == sorted(files[30:])


def test_backup_name_is_dated() -> None:
    assert backup_name(date(2026, 1, 2)) == "biblia-2026-01-02.dump"


@pytest.fixture
async def committed_rows(migrated_db: str):  # type: ignore[no-untyped-def]
    engine = create_async_engine(migrated_db)
    cid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO conversations (id, title, kind) VALUES (:id, 'backup-teste', 'chat')"), {"id": cid}
        )
        await conn.execute(
            text("INSERT INTO messages (conversation_id, seq, role, text) VALUES (:id, 1, 'user', 'olá backup')"),
            {"id": cid},
        )
        await conn.execute(text("INSERT INTO memories (path, content) VALUES ('teste-backup', 'conteúdo')"))
    yield engine, cid
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": cid})
        await conn.execute(text("DELETE FROM memories WHERE path = 'teste-backup'"))
    await engine.dispose()


async def _count(engine, cid) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    async with engine.connect() as conn:
        messages = (
            await conn.execute(text("SELECT count(*) FROM messages WHERE conversation_id = :id"), {"id": cid})
        ).scalar_one()
        memories = (await conn.execute(text("SELECT count(*) FROM memories WHERE path = 'teste-backup'"))).scalar_one()
    return messages, memories


async def test_one_backup_per_day(committed_rows, migrated_db: str, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    first = await create_backup(migrated_db, tmp_path, date(2026, 11, 6))
    assert first is not None and first.name == "biblia-2026-11-06.dump" and first.stat().st_size > 0
    assert await create_backup(migrated_db, tmp_path, date(2026, 11, 6)) is None


async def test_backup_and_restore_roundtrip(committed_rows, migrated_db: str, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    engine, cid = committed_rows
    dump = await create_backup(migrated_db, tmp_path, date(2026, 11, 6))
    assert dump is not None
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": cid})
        await conn.execute(text("DELETE FROM memories WHERE path = 'teste-backup'"))
    assert await _count(engine, cid) == (0, 0)
    await restore_backup(migrated_db, dump, tmp_path)
    assert await _count(engine, cid) == (1, 1)
    assert any(p.name.startswith("biblia-antes-restauracao-") for p in tmp_path.iterdir())
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO messages (conversation_id, seq, role, text) VALUES (:id, 2, 'user', 'depois')"),
            {"id": cid},
        )


async def test_restore_rejects_invalid_file_without_touching_data(
    committed_rows, migrated_db: str, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    engine, cid = committed_rows
    bad = tmp_path / "biblia-2026-11-01.dump"
    bad.write_bytes(b"isto nao e um backup")
    with pytest.raises(BackupError):
        await restore_backup(migrated_db, bad, tmp_path)
    assert await _count(engine, cid) == (1, 1)
