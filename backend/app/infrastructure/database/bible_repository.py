import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.entities import CrossReference, LexiconEntry, OriginalWord, PassageHit, Verse
from app.domain.bible.references import VerseRange
from app.domain.bible.repositories import BibleRepository
from app.infrastructure.ingestion.translations import REFERENCE_TRANSLATION

_OR_QUERY = "to_tsquery('portuguese', replace(plainto_tsquery('portuguese', unaccent(:q))::text, '&', '|'))"


class SqlBibleRepository(BibleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_verses(self, r: VerseRange, translation: str) -> list[Verse]:
        result = await self._session.execute(
            text(
                "SELECT verse, text FROM verses WHERE translation_code = :t AND book_id = :b AND chapter = :c "
                "AND verse BETWEEN :s AND :e ORDER BY verse"
            ),
            {"t": translation, "b": r.book_id, "c": r.chapter, "s": r.verse_start or 1, "e": r.verse_end or 999},
        )
        return [Verse(r.book_id, r.chapter, v, translation, t) for v, t in result.all()]

    async def chapter_ok(self, book_id: int, chapter: int, translation: str) -> bool:
        result = await self._session.execute(
            text("SELECT ok FROM chapter_alignment WHERE translation_code = :t AND book_id = :b AND chapter = :c"),
            {"t": translation, "b": book_id, "c": chapter},
        )
        return bool(result.scalar_one_or_none())

    async def last_verse(self, book_id: int, chapter: int) -> int | None:
        result = await self._session.execute(
            text("SELECT max(verse) FROM verses WHERE translation_code = :t AND book_id = :b AND chapter = :c"),
            {"t": REFERENCE_TRANSLATION, "b": book_id, "c": chapter},
        )
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None

    async def original_words(self, r: VerseRange) -> list[OriginalWord]:
        result = await self._session.execute(
            text(
                "SELECT verse, position, surface, transliteration, gloss_en, strong, morphology, language "
                "FROM original_words WHERE book_id = :b AND chapter = :c AND verse BETWEEN :s AND :e "
                "ORDER BY verse, position, id"
            ),
            {"b": r.book_id, "c": r.chapter, "s": r.verse_start or 1, "e": r.verse_end or 999},
        )
        return [OriginalWord(*row) for row in result.all()]

    async def lexicon(self, strongs: list[str]) -> dict[str, LexiconEntry]:
        if not strongs:
            return {}
        result = await self._session.execute(
            text(
                "SELECT strong, lemma, transliteration, gloss, definition FROM lexicon "
                "WHERE strong = ANY(CAST(:s AS text[]))"
            ),
            {"s": sorted(set(strongs))},
        )
        return {row[0]: LexiconEntry(*row) for row in result.all()}

    async def cross_references(self, book_id: int, chapter: int, verse: int, limit: int) -> list[CrossReference]:
        result = await self._session.execute(
            text(
                "SELECT to_book, to_chapter_start, to_verse_start, to_chapter_end, to_verse_end, votes "
                "FROM cross_references WHERE from_book = :b AND from_chapter = :c AND from_verse = :v "
                "ORDER BY votes DESC, id LIMIT :n"
            ),
            {"b": book_id, "c": chapter, "v": verse, "n": limit},
        )
        refs: list[CrossReference] = []
        for tb, tcs, tvs, tce, tve, votes in result.all():
            end = tve if tce == tcs else tvs
            refs.append(CrossReference(VerseRange(tb, tcs, tvs, end), votes))
        return refs

    async def fulltext(self, query: str, translations: list[str], limit: int) -> list[PassageHit]:
        result = await self._session.execute(
            text(
                "SELECT translation_code, book_id, chapter, verse_start, verse_end, text, "
                f"ts_rank(tsv, {_OR_QUERY}) AS rank FROM passages "
                f"WHERE translation_code = ANY(CAST(:t AS text[])) AND tsv @@ {_OR_QUERY} "
                "ORDER BY rank DESC LIMIT :n"
            ),
            {"q": query, "t": translations, "n": limit},
        )
        return [PassageHit(*row) for row in result.all()]

    async def nearest(self, embedding: list[float], translations: list[str], limit: int) -> list[PassageHit]:
        result = await self._session.execute(
            text(
                "SELECT translation_code, book_id, chapter, verse_start, verse_end, text, "
                "1 - (embedding <=> CAST(:e AS vector)) AS score FROM passages "
                "WHERE translation_code = ANY(CAST(:t AS text[])) AND embedding IS NOT NULL "
                "ORDER BY embedding <=> CAST(:e AS vector) LIMIT :n"
            ),
            {"e": json.dumps(embedding), "t": translations, "n": limit},
        )
        return [PassageHit(*row) for row in result.all()]

    async def find_verse_by_norm(self, norm_fragment: str) -> Verse | None:
        result = await self._session.execute(
            text(
                "SELECT book_id, chapter, verse, translation_code, text FROM verses "
                "WHERE position(:f in text_norm) > 0 LIMIT 1"
            ),
            {"f": norm_fragment},
        )
        row = result.first()
        return Verse(row[0], row[1], row[2], row[3], row[4]) if row else None

    async def verse_in_all_translations(self, book_id: int, chapter: int, verse: int) -> list[Verse]:
        result = await self._session.execute(
            text(
                "SELECT v.translation_code, v.text FROM verses v JOIN chapter_alignment a "
                "ON a.translation_code = v.translation_code AND a.book_id = v.book_id AND a.chapter = v.chapter "
                "WHERE v.book_id = :b AND v.chapter = :c AND v.verse = :v AND a.ok ORDER BY v.translation_code"
            ),
            {"b": book_id, "c": chapter, "v": verse},
        )
        return [Verse(book_id, chapter, verse, t, x) for t, x in result.all()]

    async def verses_with_strong(self, strong: str, limit: int) -> list[tuple[VerseRange, str]]:
        result = await self._session.execute(
            text(
                "SELECT DISTINCT ON (book_id, chapter, verse) book_id, chapter, verse, surface FROM original_words "
                "WHERE strong = :s AND verse > 0 ORDER BY book_id, chapter, verse, position LIMIT :n"
            ),
            {"s": strong, "n": limit},
        )
        return [(VerseRange(b, c, v, v), surface) for b, c, v, surface in result.all()]

    async def translation_names(self) -> dict[str, str]:
        result = await self._session.execute(text("SELECT code, name FROM translations"))
        return dict(result.all())
