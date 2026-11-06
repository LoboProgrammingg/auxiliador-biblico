import re
from collections.abc import Callable
from dataclasses import astuple, dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS

STEP_TO_BOOK = {b.step_code: b.id for b in BOOKS}
WORD_FILES = (
    "TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
    "TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
)
LEXICON_FILES = (
    "TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt",
    "TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt",
)
FOLDERS = {"TAHOT": "Translators Amalgamated OT+NT", "TAGNT": "Translators Amalgamated OT+NT"}

_REF = re.compile(
    r"^(?P<book>[1-3]?[A-Z][a-z]{1,2})\.(?P<ch>\d+)\.(?P<v>\d+)(?:\([^)]*\))?(?:\[[^\]]*\])?#(?P<pos>\d+)=(?P<type>\S+)$"
)
_BRACED_STRONG = re.compile(r"\{([HG]\d{4}[A-Za-z]?)\}")
_ANY_STRONG = re.compile(r"[HG]\d{4}[A-Za-z]?")
_LEXICON_LINE = re.compile(r"^[GH]\d{4}[A-Za-z]?\t")
_SURFACE = re.compile(r"^(?P<surface>.*?)\s*\((?P<translit>[^)]*)\)\s*$")
_BATCH = 5000


@dataclass(frozen=True)
class OriginalWordRow:
    book_id: int
    chapter: int
    verse: int
    position: int
    surface: str
    transliteration: str
    gloss_en: str
    strong: str
    morphology: str
    language: str
    editions: str | None


@dataclass(frozen=True)
class LexiconRow:
    strong: str
    lemma: str
    transliteration: str
    gloss: str
    definition: str


def folder_for(filename: str) -> str:
    return FOLDERS.get(filename[:5], "Lexicons")


def _split_ref(cell: str) -> tuple[int, int, int, int, str] | None:
    match = _REF.match(cell)
    if not match or match["book"] not in STEP_TO_BOOK:
        return None
    return STEP_TO_BOOK[match["book"]], int(match["ch"]), int(match["v"]), int(match["pos"]), match["type"]


def parse_tagnt_line(line: str) -> OriginalWordRow | None:
    cols = line.rstrip("\n").split("\t")
    if len(cols) < 6 or (ref := _split_ref(cols[0])) is None:
        return None
    book_id, chapter, verse, position, _ = ref
    surface_match = _SURFACE.match(cols[1])
    surface, translit = (surface_match["surface"], surface_match["translit"]) if surface_match else (cols[1], "")
    strong, _, morphology = cols[3].partition("=")
    return OriginalWordRow(
        book_id,
        chapter,
        verse,
        position,
        surface.strip(),
        translit.strip(),
        cols[2].strip(),
        strong.strip(),
        morphology.strip(),
        "grc",
        cols[5].strip() or None,
    )


def parse_tahot_line(line: str) -> OriginalWordRow | None:
    cols = line.rstrip("\n").split("\t")
    if len(cols) < 6 or (ref := _split_ref(cols[0])) is None:
        return None
    book_id, chapter, verse, position, word_type = ref
    braced = _BRACED_STRONG.search(cols[4])
    candidates = _ANY_STRONG.findall(cols[4])
    strong = braced.group(1) if braced else (candidates[-1] if candidates else "")
    language = "arc" if cols[5].startswith("A") else "heb"
    return OriginalWordRow(
        book_id,
        chapter,
        verse,
        position,
        cols[1].strip(),
        cols[2].strip(),
        cols[3].strip(),
        strong,
        cols[5].strip(),
        language,
        word_type,
    )


def parse_lexicon_line(line: str) -> LexiconRow | None:
    if not _LEXICON_LINE.match(line):
        return None
    cols = line.rstrip("\n").split("\t")
    if len(cols) < 8:
        return None
    strong = cols[1].split()[0] if cols[1].strip() else cols[0]
    return LexiconRow(strong, cols[3].strip(), cols[4].strip(), cols[6].strip(), cols[7].strip())


async def load_word_file(session: AsyncSession, path: Path, parser: Callable[[str], OriginalWordRow | None]) -> int:
    rows = [w for line in path.read_text(encoding="utf-8").splitlines() if (w := parser(line))]
    for start in range(0, len(rows), _BATCH):
        columns = list(zip(*(astuple(r) for r in rows[start : start + _BATCH]), strict=True))
        await session.execute(
            text(
                "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, "
                "gloss_en, strong, morphology, language, editions) "
                "SELECT * FROM unnest(CAST(:b AS int[]), CAST(:c AS int[]), CAST(:v AS int[]), "
                "CAST(:p AS int[]), CAST(:s AS text[]), CAST(:t AS text[]), CAST(:g AS text[]), "
                "CAST(:st AS text[]), CAST(:m AS text[]), CAST(:l AS text[]), CAST(:e AS text[]))"
            ),
            dict(zip(("b", "c", "v", "p", "s", "t", "g", "st", "m", "l", "e"), map(list, columns), strict=True)),
        )
    return len(rows)


async def load_lexicon_file(session: AsyncSession, path: Path) -> int:
    rows = [e for line in path.read_text(encoding="utf-8").splitlines() if (e := parse_lexicon_line(line))]
    for start in range(0, len(rows), _BATCH):
        columns = list(zip(*(astuple(r) for r in rows[start : start + _BATCH]), strict=True))
        await session.execute(
            text(
                "INSERT INTO lexicon (strong, lemma, transliteration, gloss, definition) "
                "SELECT * FROM unnest(CAST(:s AS text[]), CAST(:l AS text[]), CAST(:t AS text[]), "
                "CAST(:g AS text[]), CAST(:d AS text[])) ON CONFLICT (strong) DO NOTHING"
            ),
            dict(zip(("s", "l", "t", "g", "d"), map(list, columns), strict=True)),
        )
    return len(rows)
