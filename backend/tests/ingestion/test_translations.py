from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.ingestion.sources import download
from app.infrastructure.ingestion.translations import (
    TRANSLATIONS,
    IngestionError,
    count_alignment,
    load_translation,
    normalize_for_match,
    parse_translation_json,
    seed_books,
)
from tests.ingestion.helpers import synthetic_bible, write_json


def test_translation_list_has_18_without_catholic_editions() -> None:
    assert len(TRANSLATIONS) == 18
    assert {"vfl", "nvt", "acf"} <= TRANSLATIONS.keys()
    assert not {"avm", "pastoral", "matos"} & TRANSLATIONS.keys()


def test_parse_translation_maps_books_by_position(tmp_path: Path) -> None:
    rows = parse_translation_json(write_json(tmp_path / "pt.json", synthetic_bible()))
    assert len(rows) == 66 * 2 * 3
    assert rows[0] == (1, 1, 1, "Texto sintético Gn 1:1")
    assert rows[-1][:3] == (66, 2, 3)


def test_parse_translation_rejects_wrong_book_order(tmp_path: Path) -> None:
    data = synthetic_bible()
    data[0], data[1] = data[1], data[0]
    with pytest.raises(IngestionError):
        parse_translation_json(write_json(tmp_path / "pt.json", data))


def test_normalize_for_match_strips_accents_and_punctuation() -> None:
    assert normalize_for_match("Não vivam, ansiosos!") == "nao vivam ansiosos"
    assert normalize_for_match("  “Deus — é amor”.  ") == "deus e amor"


async def _load(session: AsyncSession, tmp_path: Path, code: str, overrides=None) -> int:  # type: ignore[no-untyped-def]
    rows = parse_translation_json(write_json(tmp_path / f"{code}.json", synthetic_bible(overrides)))
    return await load_translation(session, code, rows)


async def test_load_translation_is_idempotent(db_session: AsyncSession, tmp_path: Path) -> None:
    await seed_books(db_session)
    assert await _load(db_session, tmp_path, "acf") == 396
    assert await _load(db_session, tmp_path, "acf") == 396
    count = await db_session.execute(text("SELECT count(*) FROM verses WHERE translation_code = 'acf'"))
    assert count.scalar_one() == 396
    tsv = await db_session.execute(text("SELECT tsv @@ plainto_tsquery('portuguese', 'sintetico') FROM verses LIMIT 1"))
    assert tsv.scalar_one() is True


async def test_count_alignment_flags_chapters_with_different_verse_count(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    await seed_books(db_session)
    await _load(db_session, tmp_path, "acf")
    await _load(db_session, tmp_path, "vfl", {(43, 2): 2})
    assert await count_alignment(db_session, "vfl") == 1
    bad = await db_session.execute(
        text("SELECT book_id, chapter, reason FROM chapter_alignment WHERE translation_code='vfl' AND NOT ok")
    )
    assert bad.all() == [(43, 2, "contagem")]


async def test_download_skips_existing_and_retries(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500) if calls["n"] == 1 else httpx.Response(200, content=b"ok")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        dest = await download("https://example.test/a.json", tmp_path / "a.json", client=client, backoff=0)
        assert dest.read_bytes() == b"ok" and calls["n"] == 2
        await download("https://example.test/a.json", tmp_path / "a.json", client=client, backoff=0)
        assert calls["n"] == 2
        assert not (tmp_path / "a.json.part").exists()
