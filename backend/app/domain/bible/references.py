import re
from dataclasses import dataclass

from app.domain.bible.books import BOOKS, find_book

_NAME = r"[A-Za-zÀ-ÿ]+(?:\s+(?:dos|das|de)\s+[A-Za-zÀ-ÿ]+)?"
_PREFIX = r"(?:[123]\s?[ºª°]?\s*|I{1,3}\s+|(?:Primeir[oa]|Segund[oa]|Terceir[oa])\s+)?"
_NUMBERS = r"(?P<ch>\d{1,3})(?:\s*[:.]\s*(?P<v1>\d{1,3})(?:\s*[-–]\s*(?P<v2>\d{1,3}))?)?"
_CORE = rf"(?P<book>{_PREFIX}{_NAME})\.?\s*{_NUMBERS}"

_FULL_RE = re.compile(rf"^\s*{_CORE}\s*$", re.IGNORECASE)
REFERENCE_PATTERN = re.compile(rf"(?<![A-Za-zÀ-ÿ0-9]){_CORE}(?![\d:])", re.IGNORECASE)


# Abreviações/nomes que também são palavras comuns em português: na prosa só contam com "cap:vers".
AMBIGUOUS_IN_PROSE = {"os", "na", "am", "ez", "at", "is", "ed", "et", "ne", "ob", "ag", "atos", "números", "numeros"}


@dataclass(frozen=True)
class VerseRange:
    book_id: int
    chapter: int
    verse_start: int | None
    verse_end: int | None


def _to_range(match: re.Match[str]) -> VerseRange | None:
    book = find_book(match["book"])
    if book is None:
        return None
    chapter = int(match["ch"])
    if chapter < 1:
        return None
    if match["v1"] is None:
        return VerseRange(book.id, chapter, None, None)
    start = int(match["v1"])
    end = int(match["v2"]) if match["v2"] else start
    if start < 1 or end < start:
        return None
    return VerseRange(book.id, chapter, start, end)


def parse_reference(text: str) -> VerseRange | None:
    match = _FULL_RE.match(text)
    return _to_range(match) if match else None


def format_reference(r: VerseRange) -> str:
    base = f"{BOOKS[r.book_id - 1].abbrev} {r.chapter}"
    if r.verse_start is None:
        return base
    if r.verse_end is None or r.verse_end == r.verse_start:
        return f"{base}:{r.verse_start}"
    return f"{base}:{r.verse_start}-{r.verse_end}"


def find_references(text: str) -> list[tuple[str, VerseRange | None]]:
    found: list[tuple[str, VerseRange | None]] = []
    position = 0
    while (match := REFERENCE_PATTERN.search(text, position)) is not None:
        token = match["book"].strip().lower().rstrip(".")
        if find_book(match["book"]) is None or (token in AMBIGUOUS_IN_PROSE and match["v1"] is None):
            position = match.start() + 1
            continue
        found.append((match.group(0).strip(), _to_range(match)))
        position = match.end()
    return found
