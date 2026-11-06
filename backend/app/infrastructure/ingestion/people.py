"""Pessoas bíblicas e suas famílias — STEPBible TIPNR (CC BY 4.0), para as árvores genealógicas."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS

TIPNR_URL = (
    "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Proper%20Nouns/"
    "TIPNR%20-%20Translators%20Individualised%20Proper%20Names%20with%20all%20References%20-%20STEPBible.org%20CC%20BY.txt"
)
STEP_TO_BOOK = {b.step_code: b.id for b in BOOKS}
_REF = re.compile(r"^([1-3]?[A-Z][a-z]{1,2})\.(\d+)\.(\d+)[a-z]?$")
_NAME_LINES = ("– Named", "– Spelled", "– Greek", "– Aramaic", "– Name combined", "– Spelled combined")

# Nomes em português (grafia das Bíblias brasileiras) das pessoas mais citadas; sem entrada → nome em inglês.
PT_PERSON_NAMES = {
    "Adam": "Adão",
    "Eve": "Eva",
    "Cain": "Caim",
    "Abel": "Abel",
    "Seth": "Sete",
    "Enoch": "Enoque",
    "Methuselah": "Matusalém",
    "Lamech": "Lameque",
    "Noah": "Noé",
    "Shem": "Sem",
    "Ham": "Cam",
    "Japheth": "Jafé",
    "Terah": "Terá",
    "Abraham": "Abraão",
    "Sarah": "Sara",
    "Hagar": "Agar",
    "Keturah": "Quetura",
    "Lot": "Ló",
    "Nahor": "Naor",
    "Haran": "Harã",
    "Milcah": "Milca",
    "Bethuel": "Betuel",
    "Laban": "Labão",
    "Isaac": "Isaque",
    "Ishmael": "Ismael",
    "Rebekah": "Rebeca",
    "Esau": "Esaú",
    "Rachel": "Raquel",
    "Leah": "Lia",
    "Bilhah": "Bila",
    "Zilpah": "Zilpa",
    "Reuben": "Rúben",
    "Simeon": "Simeão",
    "Levi": "Levi",
    "Judah": "Judá",
    "Dan": "Dã",
    "Naphtali": "Naftali",
    "Gad": "Gade",
    "Asher": "Aser",
    "Issachar": "Issacar",
    "Zebulun": "Zebulom",
    "Dinah": "Diná",
    "Joseph": "José",
    "Benjamin": "Benjamim",
    "Manasseh": "Manassés",
    "Ephraim": "Efraim",
    "Asenath": "Azenate",
    "Tamar": "Tamar",
    "Er": "Er",
    "Onan": "Onã",
    "Shelah": "Selá",
    "Perez": "Perez",
    "Zerah": "Zerá",
    "Hezron": "Hezrom",
    "Ram": "Rão",
    "Amminadab": "Aminadabe",
    "Nahshon": "Naassom",
    "Salmon": "Salmom",
    "Boaz": "Boaz",
    "Ruth": "Rute",
    "Naomi": "Noemi",
    "Obed": "Obede",
    "Jesse": "Jessé",
    "David": "Davi",
    "Eliab": "Eliabe",
    "Abinadab": "Abinadabe",
    "Shammah": "Samá",
    "Zeruiah": "Zeruia",
    "Joab": "Joabe",
    "Abishai": "Abisai",
    "Asahel": "Asael",
    "Michal": "Mical",
    "Abigail": "Abigail",
    "Bathsheba": "Bate-Seba",
    "Uriah": "Urias",
    "Solomon": "Salomão",
    "Absalom": "Absalão",
    "Amnon": "Amnom",
    "Adonijah": "Adonias",
    "Nathan": "Natã",
    "Rehoboam": "Roboão",
    "Abijah": "Abias",
    "Asa": "Asa",
    "Jehoshaphat": "Josafá",
    "Jehoram": "Jeorão",
    "Joram": "Jorão",
    "Ahaziah": "Acazias",
    "Joash": "Joás",
    "Amaziah": "Amazias",
    "Uzziah": "Uzias",
    "Jotham": "Jotão",
    "Ahaz": "Acaz",
    "Hezekiah": "Ezequias",
    "Amon": "Amom",
    "Josiah": "Josias",
    "Jehoiakim": "Jeoaquim",
    "Jehoiachin": "Joaquim",
    "Jeconiah": "Jeconias",
    "Zedekiah": "Zedequias",
    "Shealtiel": "Salatiel",
    "Zerubbabel": "Zorobabel",
    "Jeroboam": "Jeroboão",
    "Ahab": "Acabe",
    "Jezebel": "Jezabel",
    "Saul": "Saul",
    "Kish": "Quis",
    "Jonathan": "Jônatas",
    "Abner": "Abner",
    "Ish-bosheth": "Isbosete",
    "Mephibosheth": "Mefibosete",
    "Samuel": "Samuel",
    "Hannah": "Ana",
    "Elkanah": "Elcana",
    "Eli": "Eli",
    "Moses": "Moisés",
    "Aaron": "Arão",
    "Miriam": "Miriã",
    "Amram": "Anrão",
    "Jochebed": "Joquebede",
    "Zipporah": "Zípora",
    "Jethro": "Jetro",
    "Gershom": "Gérson",
    "Gershon": "Gérson",
    "Eliezer": "Eliézer",
    "Kohath": "Coate",
    "Merari": "Merari",
    "Nadab": "Nadabe",
    "Abihu": "Abiú",
    "Eleazar": "Eleazar",
    "Ithamar": "Itamar",
    "Phinehas": "Fineias",
    "Korah": "Corá",
    "Hur": "Hur",
    "Joshua": "Josué",
    "Nun": "Num",
    "Caleb": "Calebe",
    "Othniel": "Otniel",
    "Ehud": "Eúde",
    "Deborah": "Débora",
    "Barak": "Baraque",
    "Gideon": "Gideão",
    "Jephthah": "Jefté",
    "Samson": "Sansão",
    "Manoah": "Manoá",
    "Rahab": "Raabe",
    "Elijah": "Elias",
    "Elisha": "Eliseu",
    "Isaiah": "Isaías",
    "Amoz": "Amoz",
    "Jeremiah": "Jeremias",
    "Ezekiel": "Ezequiel",
    "Daniel": "Daniel",
    "Hosea": "Oseias",
    "Jonah": "Jonas",
    "Ezra": "Esdras",
    "Nehemiah": "Neemias",
    "Esther": "Ester",
    "Mordecai": "Mardoqueu",
    "Job": "Jó",
    "Jesus": "Jesus",
    "Mary": "Maria",
    "Elizabeth": "Isabel",
    "Zechariah": "Zacarias",
    "John": "João",
    "James": "Tiago",
    "Zebedee": "Zebedeu",
    "Peter": "Pedro",
    "Simon": "Simão",
    "Andrew": "André",
    "Philip": "Filipe",
    "Matthew": "Mateus",
    "Thomas": "Tomé",
    "Judas": "Judas",
    "Lazarus": "Lázaro",
    "Martha": "Marta",
    "Herod": "Herodes",
    "Paul": "Paulo",
    "Barnabas": "Barnabé",
    "Mark": "Marcos",
    "Luke": "Lucas",
    "Timothy": "Timóteo",
    "Eunice": "Eunice",
    "Lois": "Loide",
    "Priscilla": "Priscila",
    "Aquila": "Áquila",
    "Stephen": "Estêvão",
    "Cornelius": "Cornélio",
    "Nicodemus": "Nicodemos",
    "Zacchaeus": "Zaqueu",
    "Anna": "Ana",
    "Joanna": "Joana",
    "Salome": "Salomé",
    "Cleopas": "Cleopas",
    "Matthias": "Matias",
    "Silas": "Silas",
    "Titus": "Tito",
    "Lydia": "Lídia",
    "Apollos": "Apolo",
}
# Pessoas cujo nome principal no TIPNR não é o mais conhecido em português.
ID_NAMES = {"Israel@Gen.25.26-Rev": "Jacó (Israel)"}


@dataclass(frozen=True)
class PersonRow:
    id: str
    name_en: str
    name_pt: str | None
    brief: str | None
    parents: list[str] = field(default_factory=list)
    siblings: list[str] = field(default_factory=list)
    partners: list[str] = field(default_factory=list)
    offspring: list[str] = field(default_factory=list)
    verses: list[tuple[int, int, int]] = field(default_factory=list)


def display_name(person_id: str, name_en: str) -> tuple[str, bool]:
    if person_id in ID_NAMES:
        return ID_NAMES[person_id], True
    pt = PT_PERSON_NAMES.get(name_en)
    return (pt, True) if pt else (name_en, False)


def _ids(cell: str, sep: str) -> list[str]:
    return [part.strip() for part in cell.split(sep) if "@" in part]


def _verses(cell: str) -> list[tuple[int, int, int]]:
    found = []
    for raw in cell.split(";"):
        match = _REF.match(raw.strip())
        if match and match.group(1) in STEP_TO_BOOK:
            found.append((STEP_TO_BOOK[match.group(1)], int(match.group(2)), int(match.group(3))))
    return found


def _person(lines: list[str]) -> PersonRow | None:
    head = lines[0].split("\t")
    if len(head) < 6 or "=" not in head[0]:
        return None
    person_id = head[0].split("=")[0].strip()
    name_en = person_id.split("@")[0].split("|")[-1]
    verses: list[tuple[int, int, int]] = []
    brief = None
    for line in lines[1:]:
        if line.startswith(_NAME_LINES):
            cells = line.split("\t")
            verses += _verses(cells[4]) if len(cells) > 4 else []
        elif line.startswith("@Brief="):
            brief = line.removeprefix("@Brief=").strip() or None
    unique = list(dict.fromkeys(verses))
    return PersonRow(
        person_id,
        name_en,
        display_name(person_id, name_en)[0] if display_name(person_id, name_en)[1] else None,
        brief,
        _ids(head[2], "+"),
        _ids(head[3], ","),
        _ids(head[4], ","),
        _ids(head[5], ","),
        unique,
    )


def parse_tipnr(content: str) -> list[PersonRow]:
    people = []
    for block in content.replace("\r", "").split("$========== ")[1:]:
        lines = [line.rstrip("\t") for line in block.split("\n")]
        if not lines[0].startswith("PERSON(s)") or len(lines) < 2:
            continue
        if (person := _person(lines[1:])) is not None:
            people.append(person)
    return people


async def load_people(session: AsyncSession, path: Path) -> int:
    await session.execute(text("DELETE FROM people"))
    people = parse_tipnr(path.read_text(encoding="utf-8"))
    for p in people:
        await session.execute(
            text("INSERT INTO people (id, name_en, name_pt, brief) VALUES (:i, :e, :p, :b)"),
            {"i": p.id, "e": p.name_en, "p": p.name_pt, "b": p.brief},
        )
        links = [("pai_mae", o) for o in p.parents] + [("conjuge", o) for o in p.partners]
        links += [("filho", o) for o in p.offspring] + [("irmao", o) for o in p.siblings]
        if links:
            await session.execute(
                text(
                    "INSERT INTO person_relations (person_id, kind, other_id) SELECT :i, u.k, u.o "
                    "FROM unnest(CAST(:k AS text[]), CAST(:o AS text[])) AS u(k, o)"
                ),
                {"i": p.id, "k": [k for k, _ in links], "o": [o for _, o in links]},
            )
        if p.verses:
            await session.execute(
                text(
                    "INSERT INTO person_verses (person_id, book_id, chapter, verse) SELECT :i, u.b, u.c, u.v "
                    "FROM unnest(CAST(:b AS int[]), CAST(:c AS int[]), CAST(:v AS int[])) AS u(b, c, v)"
                ),
                {
                    "i": p.id,
                    "b": [v[0] for v in p.verses],
                    "c": [v[1] for v in p.verses],
                    "v": [v[2] for v in p.verses],
                },
            )
    return len(people)
