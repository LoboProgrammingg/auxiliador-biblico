from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.ingestion.people import display_name, load_people, parse_tipnr
from app.infrastructure.ingestion.translations import seed_books

FIXTURE = Path(__file__).parent / "fixtures" / "tipnr_amostra.txt"
ISAAC = "Isaac@Gen.17.19-Jas"


def test_parse_person_with_family_and_verses() -> None:
    people = {p.id: p for p in parse_tipnr(FIXTURE.read_text(encoding="utf-8"))}
    assert len(people) == 7
    isaac = people[ISAAC]
    assert (isaac.name_en, isaac.name_pt) == ("Isaac", "Isaque")
    assert isaac.parents == ["Abraham@Gen.11.26-1Pe", "Sarah@Gen.11.29-1Pe"]
    assert isaac.partners == ["Rebekah@Gen.22.23-Rom"]
    assert isaac.offspring == ["Esau@Gen.25.25-Heb", "Israel@Gen.25.26-Rev"]
    assert isaac.brief == "Son of Abraham; father of Jacob and Esau."
    assert (1, 17, 19) in isaac.verses and (40, 1, 2) in isaac.verses
    assert len(set(isaac.verses)) == len(isaac.verses)


def test_display_names_prefer_portuguese() -> None:
    assert display_name("Israel@Gen.25.26-Rev", "Israel") == ("Jacó (Israel)", True)
    assert display_name("Rebekah@Gen.22.23-Rom", "Rebekah") == ("Rebeca", True)
    assert display_name("Iru@1Ch.4.15", "Iru") == ("Iru", False)


async def test_people_in_range_and_family(db_session: AsyncSession) -> None:
    await seed_books(db_session)
    assert await load_people(db_session, FIXTURE) == 7
    repo = SqlBibleRepository(db_session)
    people = await repo.people_in_range(1, 25, 25)
    names = {p.name for p in people}
    assert {"Isaque", "Esaú", "Jacó (Israel)", "Abraão", "Rebeca", "Ismael"} <= names
    relations = await repo.relations([p.id for p in people])
    assert ("Isaac@Gen.17.19-Jas", "filho", "Esau@Gen.25.25-Heb") in {
        (r.person_id, r.kind, r.other_id) for r in relations
    }
    isaac = next(p for p in people if p.id == ISAAC)
    assert isaac.brief and 25 == isaac.verses[0][0]
