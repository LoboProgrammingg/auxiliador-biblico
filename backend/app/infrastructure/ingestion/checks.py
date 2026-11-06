from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS
from app.infrastructure.ingestion.translations import REFERENCE_TRANSLATION


def _label(book_id: int, chapter: int, verse: int) -> str:
    return f"{BOOKS[book_id - 1].abbrev} {chapter}:{verse}"


async def check_original_coverage(session: AsyncSession) -> dict[str, list[str]]:
    """Versículos sem palavra original e palavras sem versículo na referência (títulos v.0 fora)."""
    missing = await session.execute(
        text(
            "SELECT v.book_id, v.chapter, v.verse FROM verses v WHERE v.translation_code = :ref "
            "AND NOT EXISTS (SELECT 1 FROM original_words o WHERE o.book_id = v.book_id "
            "AND o.chapter = v.chapter AND o.verse = v.verse) ORDER BY 1, 2, 3"
        ),
        {"ref": REFERENCE_TRANSLATION},
    )
    orphan = await session.execute(
        text(
            "SELECT DISTINCT o.book_id, o.chapter, o.verse FROM original_words o WHERE o.verse > 0 "
            "AND NOT EXISTS (SELECT 1 FROM verses v WHERE v.translation_code = :ref "
            "AND v.book_id = o.book_id AND v.chapter = o.chapter AND v.verse = o.verse) ORDER BY 1, 2, 3"
        ),
        {"ref": REFERENCE_TRANSLATION},
    )
    return {
        "versiculos_sem_original": [_label(*r) for r in missing],
        "original_sem_versiculo": [_label(*r) for r in orphan],
    }
