from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.illustrations import genealogy, route, word_profile
from app.domain.bible.errors import InvalidReference
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.ingestion.people import load_people
from app.infrastructure.ingestion.translations import seed_books

TIPNR = Path(__file__).parents[1] / "ingestion" / "fixtures" / "tipnr_amostra.txt"


@pytest.fixture
async def repo(db_session: AsyncSession) -> SqlBibleRepository:
    await seed_books(db_session)
    return SqlBibleRepository(db_session)


async def test_genealogy_links_parents_children_and_spouses(repo: SqlBibleRepository, db_session: AsyncSession) -> None:
    await load_people(db_session, TIPNR)
    tree = await genealogy(repo, "Gn 25")
    assert tree is not None and tree["reference"] == "Gn 25"
    names = {p["id"]: p["name"] for p in tree["people"]}
    assert names["Isaac@Gen.17.19-Jas"] == "Isaque"
    links = {(link["from"], link["to"], link["kind"]) for link in tree["links"]}
    assert ("Abraham@Gen.11.26-1Pe", "Isaac@Gen.17.19-Jas", "pai") in links
    assert ("Isaac@Gen.17.19-Jas", "Esau@Gen.25.25-Heb", "pai") in links
    assert ("Isaac@Gen.17.19-Jas", "Rebekah@Gen.22.23-Rom", "conjuge") in links
    assert len(links) == len(tree["links"])
    every = set(names)
    assert all(link["from"] in every and link["to"] in every for link in tree["links"])
    isaac = next(p for p in tree["people"] if p["id"] == "Isaac@Gen.17.19-Jas")
    assert isaac["in_text"] is True and isaac["brief"]


async def test_genealogy_without_people_is_none(repo: SqlBibleRepository) -> None:
    assert await genealogy(repo, "Ap 1") is None


async def test_genealogy_rejects_bad_reference(repo: SqlBibleRepository) -> None:
    with pytest.raises(InvalidReference):
        await genealogy(repo, "Livro 1")


async def _place(session: AsyncSession, pid: str, name: str, lon: float, verses: list[tuple[int, int]]) -> None:
    await session.execute(
        text("INSERT INTO places (id, name_en, name_pt, kind, lon, lat) VALUES (:i, :n, :n, 'settlement', :lon, 31)"),
        {"i": pid, "n": name, "lon": lon},
    )
    for chapter, verse in verses:
        await session.execute(
            text("INSERT INTO place_verses (place_id, book_id, chapter, verse) VALUES (:i, 40, :c, :v)"),
            {"i": pid, "c": chapter, "v": verse},
        )


async def test_route_orders_places_by_first_mention(repo: SqlBibleRepository, db_session: AsyncSession) -> None:
    await _place(db_session, "a", "Belém", 35.2, [(2, 1), (2, 9)])
    await _place(db_session, "b", "Jerusalém", 35.23, [(2, 3)])
    await _place(db_session, "c", "Nazaré", 35.3, [(3, 1)])
    trip = await route(repo, "Mt 2", 3)
    assert trip is not None and trip["reference"] == "Mt 2–3"
    assert [(s["name"], s["first"]) for s in trip["stops"]] == [
        ("Belém", "2:1"),
        ("Jerusalém", "2:3"),
        ("Nazaré", "3:1"),
    ]
    assert await route(repo, "Mt 3") is None


async def test_word_profile_counts_by_book(repo: SqlBibleRepository, db_session: AsyncSession) -> None:
    for book, chapter, verse in ((40, 6, 25), (40, 6, 27), (50, 4, 6)):
        await db_session.execute(
            text(
                "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
                "strong, morphology, language) VALUES (:b, :c, :v, 1, 'μεριμνάω', 'merimnaō', 'worry', 'G3309', "
                "'V', 'grc')"
            ),
            {"b": book, "c": chapter, "v": verse},
        )
    await db_session.execute(text("INSERT INTO lexicon VALUES ('G3309', 'μεριμνάω', 'merimnaō', 'to worry', 'def')"))
    profile = await word_profile(repo, "G3309")
    assert profile is not None and profile["lemma"] == "μεριμνάω" and profile["total"] == 3
    assert profile["by_book"] == [{"book": "Mateus", "count": 2}, {"book": "Filipenses", "count": 1}]
    assert await word_profile(repo, "G0000") is None
