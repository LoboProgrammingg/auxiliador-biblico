import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def range_cross_references(self, r: VerseRange, limit: int) -> list[CrossReference]:
        """Ligações de todos os versículos do trecho (capítulo inteiro sem versículo), votos somados por alvo."""
        start = r.verse_start or 1
        end = r.verse_end or (r.verse_start if r.verse_start else 10_000)
        result = await self._session.execute(
            text(
                "SELECT to_book, to_chapter_start, to_verse_start, "
                "MAX(CASE WHEN to_chapter_end = to_chapter_start THEN to_verse_end ELSE to_verse_start END), "
                "SUM(votes) AS total FROM cross_references "
                "WHERE from_book = :b AND from_chapter = :c AND from_verse BETWEEN :vs AND :ve "
                "AND NOT (to_book = :b AND to_chapter_start = :c AND to_verse_start BETWEEN :vs AND :ve) "
                "GROUP BY to_book, to_chapter_start, to_verse_start HAVING SUM(votes) > 0 "
                "ORDER BY total DESC, to_book, to_chapter_start, to_verse_start LIMIT :n"
            ),
            {"b": r.book_id, "c": r.chapter, "vs": start, "ve": end, "n": limit},
        )
        return [CrossReference(VerseRange(tb, tc, tv, te), int(total)) for tb, tc, tv, te, total in result.all()]

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

    async def places_in_chapter(self, book_id: int, chapter: int) -> list[Place]:
        result = await self._session.execute(
            text(
                "SELECT COALESCE(p.name_pt, p.name_en), p.kind, p.lon, p.lat, "
                "array_agg(DISTINCT v.verse ORDER BY v.verse) "
                "FROM places p JOIN place_verses v ON v.place_id = p.id "
                "WHERE v.book_id = :b AND v.chapter = :c GROUP BY p.id ORDER BY min(v.verse), 1"
            ),
            {"b": book_id, "c": chapter},
        )
        return [
            Place(name, kind, float(lon), float(lat), list(verses)) for name, kind, lon, lat, verses in result.all()
        ]

    async def chapter_sizes(self, translation: str = "acf") -> dict[tuple[int, int], int]:
        result = await self._session.execute(
            text(
                "SELECT book_id, chapter, count(*) FROM verses WHERE translation_code = :t "
                "GROUP BY book_id, chapter ORDER BY book_id, chapter"
            ),
            {"t": translation},
        )
        return {(b, c): n for b, c, n in result.all()}

    async def people_in_range(self, book_id: int, chapter_start: int, chapter_end: int) -> list[Person]:
        result = await self._session.execute(
            text(
                "SELECT p.id, COALESCE(p.name_pt, p.name_en), p.name_pt IS NOT NULL, p.brief, "
                "array_agg(DISTINCT v.chapter * 1000 + v.verse) "
                "FROM people p JOIN person_verses v ON v.person_id = p.id "
                "WHERE v.book_id = :b AND v.chapter BETWEEN :c1 AND :c2 "
                "GROUP BY p.id ORDER BY min(v.chapter * 1000 + v.verse), 2"
            ),
            {"b": book_id, "c1": chapter_start, "c2": chapter_end},
        )
        return [
            Person(pid, name, is_pt, brief, [(k // 1000, k % 1000) for k in sorted(keys)])
            for pid, name, is_pt, brief, keys in result.all()
        ]

    async def relations(self, person_ids: list[str]) -> list[PersonRelation]:
        result = await self._session.execute(
            text(
                "SELECT r.person_id, r.kind, r.other_id, COALESCE(o.name_pt, o.name_en), o.name_pt IS NOT NULL "
                "FROM person_relations r LEFT JOIN people o ON o.id = r.other_id "
                "WHERE r.person_id = ANY(:ids) ORDER BY r.id"
            ),
            {"ids": person_ids},
        )
        return [PersonRelation(a, k, o, name, bool(pt)) for a, k, o, name, pt in result.all()]

    async def strong_by_book(self, strong: str) -> list[tuple[int, int]]:
        result = await self._session.execute(
            text(
                "SELECT book_id, count(*) FROM original_words WHERE strong = :s AND verse > 0 "
                "GROUP BY book_id ORDER BY book_id"
            ),
            {"s": strong},
        )
        return [(b, n) for b, n in result.all()]

    async def geo_features(
        self, west: float, south: float, east: float, north: float
    ) -> list[tuple[str, str | None, list[list[float]]]]:
        result = await self._session.execute(
            text(
                "SELECT kind, name, points FROM geo_features "
                "WHERE max_lon >= :w AND min_lon <= :e AND max_lat >= :s AND min_lat <= :n "
                "ORDER BY CASE kind WHEN 'land' THEN 0 WHEN 'river' THEN 1 ELSE 2 END, id"
            ),
            {"w": west, "e": east, "s": south, "n": north},
        )
        return [(k, n, p) for k, n, p in result.all()]

    async def chapter_links(self, book_id: int, chapter: int, limit: int) -> list[tuple[int, VerseRange, int]]:
        """Referências cruzadas do capítulo para o outro Testamento, as mais votadas primeiro."""
        result = await self._session.execute(
            text(
                "SELECT DISTINCT ON (to_book, to_chapter_start, to_verse_start) from_verse, to_book, "
                "to_chapter_start, to_verse_start, votes FROM cross_references "
                "WHERE from_book = :b AND from_chapter = :c AND (to_book < 40) <> (:b < 40) "
                "ORDER BY to_book, to_chapter_start, to_verse_start, votes DESC"
            ),
            {"b": book_id, "c": chapter},
        )
        rows = sorted(result.all(), key=lambda r: -r[4])[:limit]
        return [(fv, VerseRange(tb, tc, tv, tv), votes) for fv, tb, tc, tv, votes in rows]

    async def people_named(self, names: list[str]) -> list[tuple[str, str]]:
        result = await self._session.execute(
            text(
                "SELECT id, COALESCE(name_pt, name_en) FROM people "
                "WHERE COALESCE(name_pt, name_en) = ANY(:n) OR split_part(name_pt, ' (', 1) = ANY(:n)"
            ),
            {"n": names},
        )
        return [(i, n) for i, n in result.all()]

    async def strong_stats(self, strong: str) -> tuple[int, int, list[int]]:
        """Ocorrências, versículos distintos e livros (em ordem canônica) de uma palavra do original."""
        result = await self._session.execute(
            text(
                "SELECT count(*), count(DISTINCT (book_id, chapter, verse)), "
                "COALESCE(array_agg(DISTINCT book_id ORDER BY book_id), '{}') "
                "FROM original_words WHERE strong = :s AND verse > 0"
            ),
            {"s": strong},
        )
        total, verses, books = result.one()
        return int(total), int(verses), list(books)

    async def person_names(self, ids: list[str]) -> dict[str, str]:
        result = await self._session.execute(
            text("SELECT id, COALESCE(name_pt, name_en) FROM people WHERE id = ANY(:ids)"), {"ids": ids}
        )
        return {i: n for i, n in result.all()}
