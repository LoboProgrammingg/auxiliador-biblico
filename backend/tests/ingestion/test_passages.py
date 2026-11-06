from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.ingestion.passages import build_windows, create_passages, embed_passages


def test_build_windows_stay_inside_chapter() -> None:
    verses = [(1, 1, v, f"v{v}") for v in range(1, 6)] + [(1, 2, 1, "c2v1")]
    rows = build_windows(verses)
    spans = {(r.chapter, r.verse_start, r.verse_end) for r in rows}
    assert {(1, 1, 4), (1, 3, 5)} <= spans
    assert {(1, v, v) for v in range(1, 6)} <= spans
    assert (2, 1, 1) in spans
    assert all(r.chapter in (1, 2) for r in rows)
    assert len(rows) == 2 + 5 + 1
    window = next(r for r in rows if (r.verse_start, r.verse_end) == (1, 4))
    assert window.text == "v1 v2 v3 v4"


class CountingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        self.calls += 1
        return [[1.0] + [0.0] * 1023 for _ in texts]


async def test_embed_passages_resumes(db_session: AsyncSession, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.infrastructure.ingestion.translations import load_translation, parse_translation_json, seed_books
    from tests.ingestion.helpers import synthetic_bible, write_json

    await seed_books(db_session)
    rows = parse_translation_json(write_json(tmp_path / "acf.json", synthetic_bible()))
    await load_translation(db_session, "acf", rows)
    created = await create_passages(db_session, "acf")
    embedder = CountingEmbedder()
    assert await embed_passages(db_session, embedder, "acf", batch_size=500) == created
    first_calls = embedder.calls
    assert first_calls >= 1
    assert await embed_passages(db_session, embedder, "acf", batch_size=500) == 0
    assert embedder.calls == first_calls
    missing = await db_session.execute(text("SELECT count(*) FROM passages WHERE embedding IS NULL"))
    assert missing.scalar_one() == 0


def test_token_batches_respect_budget() -> None:
    from app.infrastructure.ingestion.passages import token_batches

    texts = ["x" * 300] * 10  # ~100 tokens estimados cada (len/3)
    batches = token_batches(texts, max_tokens=250, max_items=128)
    assert [len(b) for b in batches] == [2, 2, 2, 2, 2]
    assert token_batches(["x" * 3000], max_tokens=250, max_items=128) == [[0]]


class FlakyEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        from app.application.chat.ports import EmbeddingUnavailable

        self.calls += 1
        if self.calls == 1:
            raise EmbeddingUnavailable("RateLimitError")
        return [[1.0] + [0.0] * 1023 for _ in texts]


async def test_embed_passages_waits_and_retries_on_rate_limit(db_session: AsyncSession, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.infrastructure.ingestion.translations import load_translation, parse_translation_json, seed_books
    from tests.ingestion.helpers import synthetic_bible, write_json

    await seed_books(db_session)
    await load_translation(
        db_session, "acf", parse_translation_json(write_json(tmp_path / "a.json", synthetic_bible()))
    )
    created = await create_passages(db_session, "acf")
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    embedder = FlakyEmbedder()
    done = await embed_passages(db_session, embedder, "acf", batch_size=1000, tpm=1_000_000, rpm=1000, sleep=fake_sleep)
    assert done == created and embedder.calls == 2 and waits and waits[0] >= 60
