from dataclasses import dataclass

from app.domain.bible.references import VerseRange


@dataclass(frozen=True)
class Verse:
    book_id: int
    chapter: int
    verse: int
    translation: str
    text: str


@dataclass(frozen=True)
class ResolvedPassage:
    range: VerseRange
    reference: str
    requested_translation: str
    translation: str
    fallback_label: str | None
    verses: tuple[Verse, ...]


@dataclass(frozen=True)
class PassageHit:
    translation: str
    book_id: int
    chapter: int
    verse_start: int
    verse_end: int
    text: str
    score: float


@dataclass(frozen=True)
class OriginalWord:
    verse: int
    position: int
    surface: str
    transliteration: str
    gloss_en: str
    strong: str
    morphology: str
    language: str


@dataclass(frozen=True)
class LexiconEntry:
    strong: str
    lemma: str
    transliteration: str
    gloss: str
    definition: str


@dataclass(frozen=True)
class CrossReference:
    target: VerseRange
    votes: int
