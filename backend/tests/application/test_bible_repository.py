from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.references import VerseRange
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.ingestion.passages import embed_passages, embedding_input
from tests.fakes import FakeEmbedder, fake_vector


async def test_fulltext_finds_passage_with_or_semantics(bible_db: AsyncSession) -> None:
    repo = SqlBibleRepository(bible_db)
    hits = await repo.fulltext("palavra-inexistente sintético Filipenses Fp", ["vfl"], 5)
    assert hits and all(h.translation == "vfl" for h in hits)


async def test_nearest_returns_exact_passage_first(bible_db: AsyncSession) -> None:
    await embed_passages(bible_db, FakeEmbedder(), "acf", batch_size=1000)
    repo = SqlBibleRepository(bible_db)
    target = embedding_input(50, 2, 3, 3, "Texto sintético Fp 2:3")
    hits = await repo.nearest(fake_vector(target), ["acf"], 3)
    assert (hits[0].book_id, hits[0].chapter, hits[0].verse_start, hits[0].verse_end) == (50, 2, 3, 3)


async def test_find_verse_by_norm(bible_db: AsyncSession) -> None:
    repo = SqlBibleRepository(bible_db)
    verse = await repo.find_verse_by_norm("texto sintetico fp 2 3")
    assert verse is not None and (verse.book_id, verse.chapter, verse.verse) == (50, 2, 3)
    assert await repo.find_verse_by_norm("deus ajuda quem cedo madruga") is None


async def test_original_words_lexicon_and_strong_concordance(bible_db: AsyncSession) -> None:
    await bible_db.execute(
        text(
            "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
            "strong, morphology, language) VALUES "
            "(50, 2, 3, 1, 'μεριμνᾶτε', 'merimnate', 'be anxious', 'G3309', 'V-PAM-2P', 'grc'), "
            "(40, 1, 2, 4, 'μεριμνήσητε', 'merimnēsēte', 'be anxious', 'G3309', 'V-AAS-2P', 'grc')"
        )
    )
    await bible_db.execute(text("INSERT INTO lexicon VALUES ('G3309', 'μεριμνάω', 'merimnaō', 'to worry', 'def')"))
    repo = SqlBibleRepository(bible_db)
    words = await repo.original_words(VerseRange(50, 2, 3, 3))
    assert [w.strong for w in words] == ["G3309"]
    assert (await repo.lexicon(["G3309"]))["G3309"].gloss == "to worry"
    concord = await repo.verses_with_strong("G3309", 10)
    assert [r.book_id for r, _ in concord] == [40, 50]


async def test_verse_in_all_translations_skips_misaligned_chapters(bible_db: AsyncSession) -> None:
    repo = SqlBibleRepository(bible_db)
    assert {v.translation for v in await repo.verse_in_all_translations(43, 2, 1)} == {"acf", "nvt"}
    assert {v.translation for v in await repo.verse_in_all_translations(43, 1, 1)} == {"acf", "nvt", "vfl"}


async def test_cross_references_ordered_by_votes(bible_db: AsyncSession) -> None:
    await bible_db.execute(
        text(
            "INSERT INTO cross_references (from_book, from_chapter, from_verse, to_book, to_chapter_start, "
            "to_verse_start, to_chapter_end, to_verse_end, votes) VALUES "
            "(50, 2, 3, 40, 1, 1, 1, 2, 5), (50, 2, 3, 60, 2, 1, 2, 1, 50)"
        )
    )
    refs = await SqlBibleRepository(bible_db).cross_references(50, 2, 3, 10)
    assert [r.target for r in refs] == [VerseRange(60, 2, 1, 1), VerseRange(40, 1, 1, 2)]


async def _crossrefs(db: AsyncSession, rows: list[tuple[int, int, int, int, int, int, int]]) -> None:
    for fb, fc, fv, tb, tc, tv, votes in rows:
        await db.execute(
            text(
                "INSERT INTO cross_references (from_book, from_chapter, from_verse, to_book, to_chapter_start, "
                "to_verse_start, to_chapter_end, to_verse_end, votes) VALUES (:fb, :fc, :fv, :tb, :tc, :tv, :tc, :tv, :n)"
            ),
            {"fb": fb, "fc": fc, "fv": fv, "tb": tb, "tc": tc, "tv": tv, "n": votes},
        )


async def test_range_cross_references_sums_votes_over_the_whole_range(bible_db: AsyncSession) -> None:
    await _crossrefs(
        bible_db,
        [
            (43, 1, 1, 1, 1, 1, 10),
            (43, 1, 2, 1, 1, 1, 15),  # mesmo alvo por outro versículo do trecho: soma 25
            (43, 1, 1, 19, 2, 1, 20),
            (43, 1, 3, 43, 1, 2, 50),  # alvo dentro do próprio trecho: fora
            (43, 1, 1, 23, 1, 1, -3),  # votos negativos: fora
            (43, 1, 1, 66, 1, 1, 5),
            (43, 2, 1, 40, 1, 1, 99),  # outro capítulo: fora
        ],
    )
    repo = SqlBibleRepository(bible_db)
    expected = [(VerseRange(1, 1, 1, 1), 25), (VerseRange(19, 2, 1, 1), 20), (VerseRange(66, 1, 1, 1), 5)]
    got = await repo.range_cross_references(VerseRange(43, 1, 1, 3), 10)
    assert [(r.target, r.votes) for r in got] == expected
    whole = await repo.range_cross_references(VerseRange(43, 1, None, None), 10)
    assert [(r.target, r.votes) for r in whole] == expected
    assert len(await repo.range_cross_references(VerseRange(43, 1, 1, 3), 2)) == 2
