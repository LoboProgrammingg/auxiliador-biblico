import uuid
from abc import ABC, abstractmethod

from app.domain.bible.references import VerseRange
from app.domain.diary.entities import Prayer, PrayerStatus, VerseNote


class PrayerRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[Prayer]: ...

    @abstractmethod
    async def create(self, title: str, details: str | None) -> Prayer: ...

    @abstractmethod
    async def update(
        self, prayer_id: uuid.UUID, title: str, details: str | None, status: PrayerStatus, answer_note: str | None
    ) -> Prayer | None: ...

    @abstractmethod
    async def delete(self, prayer_id: uuid.UUID) -> bool: ...


class VerseNoteRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[VerseNote]: ...

    @abstractmethod
    async def get(self, r: VerseRange) -> VerseNote | None: ...

    @abstractmethod
    async def upsert(self, r: VerseRange, reference: str, content: str) -> VerseNote: ...

    @abstractmethod
    async def delete(self, note_id: int) -> bool: ...
