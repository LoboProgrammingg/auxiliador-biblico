import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from itertools import groupby

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat.ports import Embedder, EmbeddingUnavailable
from app.domain.bible.books import BOOKS

_INSERT_BATCH = 5000
logger = logging.getLogger(__name__)
RATE_LIMIT_WAIT = 65.0
MAX_RATE_LIMIT_RETRIES = 30


@dataclass(frozen=True)
class PassageRow:
    book_id: int
    chapter: int
    verse_start: int
    verse_end: int
    text: str


def build_windows(verses: list[tuple[int, int, int, str]], size: int = 4, stride: int = 2) -> list[PassageRow]:
    rows: list[PassageRow] = []
    for (book_id, chapter), group in groupby(verses, key=lambda v: (v[0], v[1])):
        chapter_verses = sorted(group, key=lambda v: v[2])
        texts = {v[2]: v[3] for v in chapter_verses}
        last = chapter_verses[-1][2]
        rows.extend(PassageRow(book_id, chapter, n, n, t) for n, t in texts.items())
        for start in range(1, last + 1, stride):
            end = min(start + size - 1, last)
            if end > start:
                joined = " ".join(texts[n] for n in range(start, end + 1) if n in texts)
                rows.append(PassageRow(book_id, chapter, start, end, joined))
            if end == last:
                break
    return rows


def embedding_input(row_book: int, chapter: int, start: int, end: int, body: str) -> str:
    span = f"{start}" if start == end else f"{start}-{end}"
    return f"{BOOKS[row_book - 1].pt_name} {chapter}:{span} — {body}"


async def create_passages(session: AsyncSession, translation: str) -> int:
    result = await session.execute(
        text(
            "SELECT book_id, chapter, verse, text FROM verses WHERE translation_code = :t "
            "ORDER BY book_id, chapter, verse"
        ),
        {"t": translation},
    )
    rows = build_windows([tuple(r) for r in result.all()])  # type: ignore[misc]
    await session.execute(text("DELETE FROM passages WHERE translation_code = :t"), {"t": translation})
    for start in range(0, len(rows), _INSERT_BATCH):
        batch = rows[start : start + _INSERT_BATCH]
        await session.execute(
            text(
                "INSERT INTO passages (translation_code, book_id, chapter, verse_start, verse_end, "
                "text, tsv) "
                "SELECT :t, u.b, u.c, u.s, u.e, u.x, to_tsvector('portuguese', unaccent(u.x)) "
                "FROM unnest(CAST(:b AS int[]), CAST(:c AS int[]), CAST(:s AS int[]), CAST(:e AS int[]), "
                "CAST(:x AS text[])) AS u(b, c, s, e, x)"
            ),
            {
                "t": translation,
                "b": [r.book_id for r in batch],
                "c": [r.chapter for r in batch],
                "s": [r.verse_start for r in batch],
                "e": [r.verse_end for r in batch],
                "x": [r.text for r in batch],
            },
        )
    return len(rows)


def estimate_tokens(value: str) -> int:
    return max(1, len(value) // 3)


def token_batches(texts: list[str], max_tokens: int, max_items: int) -> list[list[int]]:
    batches: list[list[int]] = []
    current: list[int] = []
    used = 0
    for index, value in enumerate(texts):
        cost = estimate_tokens(value)
        if current and (used + cost > max_tokens or len(current) >= max_items):
            batches.append(current)
            current, used = [], 0
        current.append(index)
        used += cost
    if current:
        batches.append(current)
    return batches


async def _embed_with_retry(
    embedder: Embedder, texts: list[str], sleep: Callable[[float], Awaitable[None]]
) -> list[list[float]]:
    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            return await embedder.embed(texts, "document")
        except EmbeddingUnavailable as exc:
            if "RateLimit" not in str(exc) or attempt == MAX_RATE_LIMIT_RETRIES - 1:
                raise
            logger.info("limite da Voyage; aguardando %.0fs", RATE_LIMIT_WAIT)
            await sleep(RATE_LIMIT_WAIT)
    raise EmbeddingUnavailable("RateLimitError")


async def embed_passages(
    session: AsyncSession,
    embedder: Embedder,
    translation: str,
    batch_size: int = 128,
    tpm: int = 10_000,
    rpm: int = 3,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> int:
    """Gera embeddings pendentes respeitando tokens/min e requisições/min (retomável)."""
    max_tokens = min(100_000, int(tpm * 0.9))
    interval = 60.0 / rpm
    total = 0
    last_call = 0.0
    while True:
        pending = await session.execute(
            text(
                "SELECT id, book_id, chapter, verse_start, verse_end, text FROM passages "
                "WHERE translation_code = :t AND embedding IS NULL ORDER BY id LIMIT :n"
            ),
            {"t": translation, "n": batch_size * 8},
        )
        rows = pending.all()
        if not rows:
            return total
        inputs = [embedding_input(*row[1:]) for row in rows]
        for batch in token_batches(inputs, max_tokens, batch_size):
            wait = interval - (time.monotonic() - last_call)
            if wait > 0 and last_call:
                await sleep(wait)
            last_call = time.monotonic()
            vectors = await _embed_with_retry(embedder, [inputs[i] for i in batch], sleep)
            await session.execute(
                text(
                    "UPDATE passages p SET embedding = CAST(u.e AS vector) "
                    "FROM unnest(CAST(:ids AS bigint[]), CAST(:embs AS text[])) AS u(id, e) WHERE p.id = u.id"
                ),
                {"ids": [rows[i][0] for i in batch], "embs": [json.dumps(v) for v in vectors]},
            )
            await session.commit()
            total += len(batch)
        logger.info("%s: %s embeddings gerados nesta execução", translation, total)
