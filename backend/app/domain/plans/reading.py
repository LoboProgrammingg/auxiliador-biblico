from dataclasses import dataclass

from app.domain.bible.books import BOOKS


@dataclass(frozen=True)
class Reading:
    """Leitura de um dia: capítulos inteiros de um livro, ou um trecho de um capítulo."""

    book_id: int
    chapter_start: int
    chapter_end: int
    verse_start: int | None = None
    verse_end: int | None = None

    @property
    def label(self) -> str:
        abbrev = BOOKS[self.book_id - 1].abbrev
        if self.verse_start is not None:
            return f"{abbrev} {self.chapter_start}:{self.verse_start}-{self.verse_end}"
        if self.chapter_start == self.chapter_end:
            return f"{abbrev} {self.chapter_start}"
        return f"{abbrev} {self.chapter_start}–{self.chapter_end}"
