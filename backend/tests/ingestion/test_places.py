from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.ingestion.places import load_places, parse_place, pt_name
from app.infrastructure.ingestion.translations import seed_books

FIXTURE = Path(__file__).parent / "fixtures" / "places_amostra.jsonl"


def records() -> list[dict]:  # type: ignore[type-arg]
    import json

    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines()]


def test_parse_place_reads_coordinates_and_verses() -> None:
    nazareth = next(parse_place(r) for r in records() if r["friendly_id"] == "Nazareth")
    assert nazareth is not None
    assert nazareth.name_en == "Nazareth" and nazareth.name_pt == "Nazaré" and nazareth.kind == "settlement"
    assert round(nazareth.lon, 2) == 35.3 and round(nazareth.lat, 2) == 32.7
    assert (40, 2, 23) in nazareth.verses


def test_parse_place_strips_numeric_suffix_and_skips_missing_coordinates() -> None:
    galilee = next(parse_place(r) for r in records() if r["friendly_id"] == "Galilee 1")
    assert galilee is not None and galilee.name_en == "Galilee" and galilee.name_pt == "Galileia"
    assert next(parse_place(r) for r in records() if r["friendly_id"] == "Sem Coordenada") is None


def test_pt_name_falls_back_to_english() -> None:
    assert pt_name("Jerusalem") == "Jerusalém" and pt_name("Unknownville") is None


async def test_places_in_chapter(db_session: AsyncSession) -> None:
    await seed_books(db_session)
    assert await load_places(db_session, FIXTURE) >= 4
    places = await SqlBibleRepository(db_session).places_in_chapter(40, 2)
    assert "Nazaré" in [p.name for p in places]
    nazare = next(p for p in places if p.name == "Nazaré")
    assert nazare.verses == [23]
