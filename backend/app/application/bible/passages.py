from app.domain.bible.entities import ResolvedPassage
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import VerseRange, format_reference, parse_reference
from app.domain.bible.repositories import BibleRepository

PRIMARY = "vfl"
FALLBACKS: tuple[tuple[str, str], ...] = (
    ("nvt", "NVT — VFL indisponível neste trecho"),
    ("acf", "ACF — VFL/NVT indisponíveis neste trecho"),
)
KNOWN = {
    "vfl",
    "nvt",
    "acf",
    "ara",
    "naa",
    "arc",
    "rc69",
    "a21",
    "aa",
    "kja",
    "bkj",
    "nvi",
    "nvi2011",
    "ntlh",
    "nbv",
    "ol",
    "tb",
    "bpt09",
}


class PassageService:
    def __init__(self, repo: BibleRepository) -> None:
        self._repo = repo

    async def _validate(self, ref: str | VerseRange) -> VerseRange:
        r = parse_reference(ref) if isinstance(ref, str) else ref
        label = ref if isinstance(ref, str) else format_reference(ref)
        if r is None:
            raise InvalidReference(label)
        last = await self._repo.last_verse(r.book_id, r.chapter)
        if last is None or (r.verse_end or 0) > last or (r.verse_start or 1) > last:
            raise InvalidReference(label)
        return r

    async def _pick_translation(self, r: VerseRange, requested: str) -> tuple[str, str | None]:
        if await self._repo.chapter_ok(r.book_id, r.chapter, requested):
            return requested, None
        if requested != PRIMARY and await self._repo.chapter_ok(r.book_id, r.chapter, PRIMARY):
            return PRIMARY, f"VFL — {requested.upper()} indisponível neste trecho"
        for code, label in FALLBACKS:
            if await self._repo.chapter_ok(r.book_id, r.chapter, code):
                return code, label
        return FALLBACKS[-1][0], FALLBACKS[-1][1]

    async def resolve(self, ref: str | VerseRange, translation: str | None = None) -> ResolvedPassage:
        r = await self._validate(ref)
        asked = (translation or PRIMARY).lower()
        requested = asked if asked in KNOWN else PRIMARY
        chosen, label = await self._pick_translation(r, requested)
        if asked not in KNOWN and label is None:
            label = f"{chosen.upper()} — tradução {asked.upper()} não encontrada"
        verses = await self._repo.get_verses(r, chosen)
        if not verses:
            raise InvalidReference(format_reference(r))
        return ResolvedPassage(r, format_reference(r), requested, chosen, label, tuple(verses))

    async def context(self, r: VerseRange, translation: str, radius: int = 3) -> ResolvedPassage:
        last = await self._repo.last_verse(r.book_id, r.chapter) or 1
        start = max(1, (r.verse_start or 1) - radius)
        end = min(last, (r.verse_end or last) + radius)
        return await self.resolve(VerseRange(r.book_id, r.chapter, start, end), translation)
