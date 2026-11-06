import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.verification.markers import (
    InvalidRefOut,
    MarkerStreamProcessor,
    RouteOut,
    TextOut,
    ThreadOut,
    TimelineOut,
)
from app.infrastructure.database.bible_repository import SqlBibleRepository


@pytest.fixture
async def proc(bible_db: AsyncSession) -> MarkerStreamProcessor:
    places = [
        ("p1", "Bethlehem", "Belém", "settlement", 35.2, 31.7, [1, 3]),
        ("p2", "Jerusalem", "Jerusalém", "settlement", 35.23, 31.78, [2]),
        ("p3", "Egypt", "Egito", "region", 31.3, 30.1, [2]),
        ("p4", "East", "Oriente", "region", 35.9, 31.9, [1]),
    ]
    for pid, en, pt, kind, lon, lat, verses in places:
        await bible_db.execute(
            text("INSERT INTO places (id, name_en, name_pt, kind, lon, lat) VALUES (:i, :e, :p, :k, :lon, :lat)"),
            {"i": pid, "e": en, "p": pt, "k": kind, "lon": lon, "lat": lat},
        )
        for v in verses:
            await bible_db.execute(
                text("INSERT INTO place_verses (place_id, book_id, chapter, verse) VALUES (:i, 40, 2, :v)"),
                {"i": pid, "v": v},
            )
    await bible_db.execute(
        text("INSERT INTO people (id, name_en, name_pt, brief) VALUES ('h', 'Herod', 'Herodes', NULL)")
    )
    await bible_db.execute(
        text("INSERT INTO person_verses (person_id, book_id, chapter, verse) VALUES ('h', 40, 2, 3)")
    )
    for from_v, to_b, to_c, to_v, votes in ((1, 33, 1, 2, 90), (2, 28, 1, 1, 50), (3, 19, 2, 1, 10), (1, 41, 1, 1, 99)):
        await bible_db.execute(
            text(
                "INSERT INTO cross_references (from_book, from_chapter, from_verse, to_book, to_chapter_start, "
                "to_verse_start, to_chapter_end, to_verse_end, votes) VALUES (40, 2, :f, :b, :c, :v, :c, :v, :n)"
            ),
            {"f": from_v, "b": to_b, "c": to_c, "v": to_v, "n": votes},
        )
    return MarkerStreamProcessor(PassageService(SqlBibleRepository(bible_db)))


async def _run(proc: MarkerStreamProcessor, s: str) -> list:  # type: ignore[type-arg]
    return [o for o in await proc.feed(s) + await proc.flush() if not isinstance(o, TextOut)]


async def test_route_marker_validates_every_stop(proc: MarkerStreamProcessor) -> None:
    out = await _run(proc, "[[rota:Mt 2|Oriente>Jerusalém>Belém=os sábios;Belém>Egito=a família;Belém>Roma=inventado]]")
    route = out[0]
    assert isinstance(route, RouteOut) and route.reference == "Mt 2"
    assert [[s["name"] for s in leg["stops"]] for leg in route.legs] == [
        ["Oriente", "Jerusalém", "Belém"],
        ["Belém", "Egito"],
    ]
    assert route.legs[0]["who"] == "os sábios"
    first = route.legs[0]["stops"][0]
    assert first["direction"] is True and first["kind"] == "region"
    assert route.legs[1]["stops"][1]["region"] is True and route.legs[1]["stops"][0]["region"] is False


async def test_route_without_valid_leg_is_invalid(proc: MarkerStreamProcessor) -> None:
    assert [type(o) for o in await _run(proc, "[[rota:Mt 2|Roma>Atenas]]")] == [InvalidRefOut]


async def test_thread_marker_links_to_the_other_testament(proc: MarkerStreamProcessor) -> None:
    out = await _run(proc, "[[fio:Mt 2]]")
    thread = out[0]
    assert isinstance(thread, ThreadOut) and thread.reference == "Mt 2"
    assert [(link["from_verse"], link["target"]["reference"]) for link in thread.links] == [
        (1, "Mq 1:2"),
        (2, "Os 1:1"),
        (3, "Sl 2:1"),
    ]
    assert thread.links[0]["from_text"] and thread.links[0]["target"]["verses"][0]["text"]
    assert len(thread.books) == 66 and thread.books[39]["abbrev"] == "Mt"


async def test_thread_without_links_is_dropped(proc: MarkerStreamProcessor) -> None:
    assert await _run(proc, "[[fio:Gn 1]]") == []


async def test_timeline_sections_carry_people_places_and_key_verse(proc: MarkerStreamProcessor) -> None:
    out = await _run(proc, "[[linha:Mt 2|1-2=Chegada;3-3=Herodes]]")
    timeline = out[0]
    assert isinstance(timeline, TimelineOut)
    first, second = timeline.sections
    assert [p["name"] for p in first["places"]] == ["Belém", "Oriente", "Egito", "Jerusalém"]
    assert first["people"] == [] and [p["name"] for p in second["people"]] == ["Herodes"]
    assert second["key"]["n"] == 3 and second["key"]["text"]
