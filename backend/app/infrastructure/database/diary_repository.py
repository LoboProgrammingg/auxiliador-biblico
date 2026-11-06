import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.references import VerseRange
from app.domain.diary.entities import Prayer, PrayerStatus, VerseNote
from app.domain.diary.repositories import PrayerRepository, VerseNoteRepository

_PRAYER_COLS = "id, title, details, status, answer_note, created_at, answered_at"
_NOTE_COLS = "id, reference, content, updated_at"


def _verses(r: VerseRange) -> tuple[int, int]:
    """0..0 marca o capítulo inteiro."""
    return (r.verse_start or 0, r.verse_end or r.verse_start or 0)


class SqlPrayerRepository(PrayerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Prayer]:
        result = await self._session.execute(
            text(f"SELECT {_PRAYER_COLS} FROM prayer_requests ORDER BY created_at DESC")
        )
        return [Prayer(*row) for row in result.all()]

    async def create(self, title: str, details: str | None) -> Prayer:
        result = await self._session.execute(
            text(f"INSERT INTO prayer_requests (id, title, details) VALUES (:id, :t, :d) RETURNING {_PRAYER_COLS}"),
            {"id": uuid.uuid4(), "t": title, "d": details},
        )
        prayer = Prayer(*result.one())
        await self._session.commit()
        return prayer

    async def update(
        self, prayer_id: uuid.UUID, title: str, details: str | None, status: PrayerStatus, answer_note: str | None
    ) -> Prayer | None:
        result = await self._session.execute(
            text(
                "UPDATE prayer_requests SET title = :t, details = :d, status = CAST(:s AS varchar), answer_note = :n, "
                "answered_at = CASE WHEN CAST(:s AS varchar) = 'respondido' THEN COALESCE(answered_at, now()) END "
                f"WHERE id = :id RETURNING {_PRAYER_COLS}"
            ),
            {"t": title, "d": details, "s": status, "n": answer_note, "id": prayer_id},
        )
        row = result.first()
        await self._session.commit()
        return Prayer(*row) if row else None

    async def delete(self, prayer_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            text("DELETE FROM prayer_requests WHERE id = :id RETURNING id"), {"id": prayer_id}
        )
        deleted = result.first() is not None
        await self._session.commit()
        return deleted


class SqlVerseNoteRepository(VerseNoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[VerseNote]:
        result = await self._session.execute(
            text(f"SELECT {_NOTE_COLS} FROM verse_notes ORDER BY book_id, chapter, verse_start")
        )
        return [VerseNote(*row) for row in result.all()]

    async def get(self, r: VerseRange) -> VerseNote | None:
        start, end = _verses(r)
        result = await self._session.execute(
            text(
                f"SELECT {_NOTE_COLS} FROM verse_notes "
                "WHERE book_id = :b AND chapter = :c AND verse_start = :s AND verse_end = :e"
            ),
            {"b": r.book_id, "c": r.chapter, "s": start, "e": end},
        )
        row = result.first()
        return VerseNote(*row) if row else None

    async def upsert(self, r: VerseRange, reference: str, content: str) -> VerseNote:
        start, end = _verses(r)
        result = await self._session.execute(
            text(
                "INSERT INTO verse_notes (reference, book_id, chapter, verse_start, verse_end, content) "
                "VALUES (:ref, :b, :c, :s, :e, :content) "
                "ON CONFLICT ON CONSTRAINT uq_verse_notes_range "
                "DO UPDATE SET content = EXCLUDED.content, updated_at = now() "
                f"RETURNING {_NOTE_COLS}"
            ),
            {"ref": reference, "b": r.book_id, "c": r.chapter, "s": start, "e": end, "content": content},
        )
        note = VerseNote(*result.one())
        await self._session.commit()
        return note

    async def delete(self, note_id: int) -> bool:
        result = await self._session.execute(
            text("DELETE FROM verse_notes WHERE id = :id RETURNING id"), {"id": note_id}
        )
        deleted = result.first() is not None
        await self._session.commit()
        return deleted
