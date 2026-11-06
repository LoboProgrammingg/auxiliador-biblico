from abc import ABC, abstractmethod

from app.domain.bible.entities import (
    CrossReference,
    LexiconEntry,
    OriginalWord,
    PassageHit,
    Person,
    PersonRelation,
    Place,
    Verse,
)
from app.domain.bible.references import VerseRange


class BibleRepository(ABC):
    @abstractmethod
    async def get_verses(self, r: VerseRange, translation: str) -> list[Verse]: ...

    @abstractmethod
    async def chapter_ok(self, book_id: int, chapter: int, translation: str) -> bool: ...

    @abstractmethod
    async def last_verse(self, book_id: int, chapter: int) -> int | None: ...

    @abstractmethod
    async def original_words(self, r: VerseRange) -> list[OriginalWord]: ...

    @abstractmethod
    async def lexicon(self, strongs: list[str]) -> dict[str, LexiconEntry]: ...

    @abstractmethod
    async def cross_references(self, book_id: int, chapter: int, verse: int, limit: int) -> list[CrossReference]: ...

    @abstractmethod
    async def fulltext(self, query: str, translations: list[str], limit: int) -> list[PassageHit]: ...

    @abstractmethod
    async def nearest(self, embedding: list[float], translations: list[str], limit: int) -> list[PassageHit]: ...

    @abstractmethod
    async def find_verse_by_norm(self, norm_fragment: str) -> Verse | None: ...

    @abstractmethod
    async def verse_in_all_translations(self, book_id: int, chapter: int, verse: int) -> list[Verse]: ...

    @abstractmethod
    async def verses_with_strong(self, strong: str, limit: int) -> list[tuple[VerseRange, str]]: ...

    @abstractmethod
    async def translation_names(self) -> dict[str, str]: ...

    @abstractmethod
    async def places_in_chapter(self, book_id: int, chapter: int) -> list[Place]: ...

    @abstractmethod
    async def chapter_sizes(self, translation: str = "acf") -> dict[tuple[int, int], int]: ...

    @abstractmethod
    async def people_in_range(self, book_id: int, chapter_start: int, chapter_end: int) -> list[Person]: ...

    @abstractmethod
    async def relations(self, person_ids: list[str]) -> list[PersonRelation]: ...

    @abstractmethod
    async def strong_by_book(self, strong: str) -> list[tuple[int, int]]: ...
