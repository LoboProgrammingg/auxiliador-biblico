import json
import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.ingestion.translations import REFERENCE_TRANSLATION

MARGIN = 0.02


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def misaligned_verses(own: list[list[float]], ref: list[list[float]]) -> list[int]:
    """Índices cujo vetor se parece claramente mais com o versículo vizinho da referência do que com o próprio."""
    flagged: list[int] = []
    for i, vector in enumerate(own):
        if i >= len(ref):
            flagged.append(i)
            continue
        neighbors = [_cos(vector, ref[j]) for j in (i - 1, i + 1) if 0 <= j < len(ref)]
        if neighbors and _cos(vector, ref[i]) < max(neighbors) - MARGIN:
            flagged.append(i)
    return flagged


def _direction(own: list[float], ref: list[list[float]], i: int) -> int:
    """-1/+1 se o versículo casa claramente melhor com o vizinho anterior/seguinte da referência; 0 se com o próprio."""
    if i >= len(ref):
        return 1
    own_score = _cos(own, ref[i])
    prev = _cos(own, ref[i - 1]) if i > 0 else -1.0
    nxt = _cos(own, ref[i + 1]) if i + 1 < len(ref) else -1.0
    if max(prev, nxt) < own_score + MARGIN:
        return 0
    return -1 if prev > nxt else 1


def chapter_shifted(own: list[list[float]], ref: list[list[float]], min_run: int = 2) -> bool:
    """Desalinhamento real = deslocamento: min_run versículos seguidos casando com o vizinho na mesma direção."""
    run, last = 0, 0
    for i, vector in enumerate(own):
        direction = _direction(vector, ref, i)
        run = run + 1 if direction != 0 and direction == last else (1 if direction != 0 else 0)
        last = direction
        if run >= min_run:
            return True
    return False


async def _chapter_vectors(session: AsyncSession, translation: str, book_id: int, chapter: int) -> list[list[float]]:
    result = await session.execute(
        text(
            "SELECT embedding::text FROM passages WHERE translation_code = :t AND book_id = :b AND chapter = :c "
            "AND verse_start = verse_end AND embedding IS NOT NULL ORDER BY verse_start"
        ),
        {"t": translation, "b": book_id, "c": chapter},
    )
    return [json.loads(row[0]) for row in result.all()]


async def semantic_alignment(session: AsyncSession, translation: str) -> int:
    await session.execute(
        text(
            "UPDATE chapter_alignment SET ok = true, reason = NULL WHERE translation_code = :t AND reason = 'semântico'"
        ),
        {"t": translation},
    )
    chapters = await session.execute(
        text("SELECT book_id, chapter FROM chapter_alignment WHERE translation_code = :t AND ok ORDER BY 1, 2"),
        {"t": translation},
    )
    failed = 0
    for book_id, chapter in chapters.all():
        own = await _chapter_vectors(session, translation, book_id, chapter)
        ref = await _chapter_vectors(session, REFERENCE_TRANSLATION, book_id, chapter)
        if chapter_shifted(own, ref):
            failed += 1
            await session.execute(
                text(
                    "UPDATE chapter_alignment SET ok = false, reason = 'semântico' "
                    "WHERE translation_code = :t AND book_id = :b AND chapter = :c"
                ),
                {"t": translation, "b": book_id, "c": chapter},
            )
    return failed
