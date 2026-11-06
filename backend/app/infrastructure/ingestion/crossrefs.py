import io
import re
import zipfile
from dataclasses import astuple, dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS
from app.infrastructure.ingestion.translations import REFERENCE_TRANSLATION

OSIS_TO_BOOK = {b.osis: b.id for b in BOOKS}
_REF = re.compile(r"^([1-3]?[A-Z][A-Za-z]+)\.(\d+)\.(\d+)$")
_BATCH = 10000


@dataclass(frozen=True)
class CrossRefRow:
    from_book: int
    from_chapter: int
    from_verse: int
    to_book: int
    to_chapter_start: int
    to_verse_start: int
    to_chapter_end: int
    to_verse_end: int
    votes: int


def _ref(value: str) -> tuple[int, int, int] | None:
    match = _REF.match(value)
    if not match or match.group(1) not in OSIS_TO_BOOK:
        return None
    return OSIS_TO_BOOK[match.group(1)], int(match.group(2)), int(match.group(3))


def parse_crossref_line(line: str) -> CrossRefRow | None:
    cols = line.strip().split("\t")
    if len(cols) < 3 or not cols[2].lstrip("-").isdigit():
        return None
    votes = int(cols[2])
    start_text, _, end_text = cols[1].partition("-")
    source, start = _ref(cols[0]), _ref(start_text)
    end = _ref(end_text) if end_text else start
    if votes < 0 or source is None or start is None or end is None or end[0] != start[0]:
        return None
    return CrossRefRow(*source, start[0], start[1], start[2], end[1], end[2], votes)


def read_crossref_zip(path: Path) -> list[CrossRefRow]:
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".txt"))
        content = io.TextIOWrapper(archive.open(name), encoding="utf-8").read()
    return [row for line in content.splitlines() if (row := parse_crossref_line(line))]


async def load_crossrefs(session: AsyncSession, rows: list[CrossRefRow]) -> dict[str, int]:
    await session.execute(text("DELETE FROM cross_references"))
    keys = ("fb", "fc", "fv", "tb", "tcs", "tvs", "tce", "tve", "votes")
    for start in range(0, len(rows), _BATCH):
        columns = list(zip(*(astuple(r) for r in rows[start : start + _BATCH]), strict=True))
        await session.execute(
            text(
                "INSERT INTO cross_references (from_book, from_chapter, from_verse, to_book, "
                "to_chapter_start, to_verse_start, to_chapter_end, to_verse_end, votes) SELECT * FROM unnest("
                + ", ".join(f"CAST(:{k} AS int[])" for k in keys)
                + ")"
            ),
            dict(zip(keys, map(list, columns), strict=True)),
        )
    removed = await session.execute(
        text(
            "DELETE FROM cross_references c WHERE NOT EXISTS (SELECT 1 FROM verses v "
            "WHERE v.translation_code = :ref AND v.book_id = c.to_book "
            "AND v.chapter = c.to_chapter_start AND v.verse = c.to_verse_start)"
        ),
        {"ref": REFERENCE_TRANSLATION},
    )
    return {"lidas": len(rows), "destino_inexistente": int(removed.rowcount or 0)}
