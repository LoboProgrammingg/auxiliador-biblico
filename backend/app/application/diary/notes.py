from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import VerseRange, format_reference, parse_reference
from app.domain.bible.repositories import BibleRepository


async def note_range(ref: str, bible: BibleRepository) -> tuple[VerseRange, str]:
    """Anotação só em capítulo ou versículos que existem no banco."""
    r = parse_reference(ref.strip())
    if r is None:
        raise InvalidReference(ref)
    last = await bible.last_verse(r.book_id, r.chapter)
    if last is None or (r.verse_end or 0) > last:
        raise InvalidReference(ref)
    return r, format_reference(r)
