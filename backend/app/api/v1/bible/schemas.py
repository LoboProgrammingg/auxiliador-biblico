from pydantic import BaseModel

from app.domain.bible.books import BOOKS
from app.domain.bible.entities import ResolvedPassage


class VerseOut(BaseModel):
    n: int
    text: str
    cited: bool = True


class PassageOut(BaseModel):
    reference: str
    book: str
    book_id: int
    chapter: int
    verse_start: int | None
    verse_end: int | None
    requested_translation: str
    translation: str
    fallback_label: str | None
    verses: list[VerseOut]

    @classmethod
    def build(cls, p: ResolvedPassage, cited: tuple[int, int] | None = None) -> "PassageOut":
        low, high = cited if cited else (p.verses[0].verse, p.verses[-1].verse)
        return cls(
            reference=p.reference,
            book=BOOKS[p.range.book_id - 1].pt_name,
            book_id=p.range.book_id,
            chapter=p.range.chapter,
            verse_start=p.range.verse_start,
            verse_end=p.range.verse_end,
            requested_translation=p.requested_translation,
            translation=p.translation,
            fallback_label=p.fallback_label,
            verses=[VerseOut(n=v.verse, text=v.text, cited=low <= v.verse <= high) for v in p.verses],
        )


class CompareItem(BaseModel):
    translation: str
    name: str
    verses: list[VerseOut] | None
    note: str | None = None


class CompareOut(BaseModel):
    reference: str
    items: list[CompareItem]


class WordOut(BaseModel):
    verse: int
    position: int
    surface: str
    transliteration: str
    gloss_en: str
    strong: str
    morphology: str
    language: str
    lemma: str | None
    lexicon_gloss: str | None


class OriginalOut(BaseModel):
    reference: str
    words: list[WordOut]


class CrossRefItem(BaseModel):
    reference: str
    votes: int


class CrossRefOut(BaseModel):
    reference: str
    items: list[CrossRefItem]


class SearchOut(BaseModel):
    items: list[PassageOut]
