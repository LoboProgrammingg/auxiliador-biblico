import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.infrastructure.external.voyage.client import voyage_from_settings

pytestmark = pytest.mark.live


async def _verse(book: int, chapter: int, verse: int) -> str:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            text(
                "SELECT text FROM verses WHERE translation_code = 'vfl' "
                "AND book_id = :b AND chapter = :c AND verse = :v"
            ),
            {"b": book, "c": chapter, "v": verse},
        )
        return str(result.scalar_one())


@pytest.mark.skipif(not get_settings().voyage_api_key, reason="sem VOYAGE_API_KEY")
async def test_query_prefers_anxiety_passage() -> None:
    fp, gn = await _verse(50, 4, 6), await _verse(1, 5, 3)
    client = voyage_from_settings()
    (q,) = await client.embed(["estou ansioso com dívidas"], "query")
    fp_vec, gn_vec = await client.embed([fp, gn], "document")

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert dot(q, fp_vec) > dot(q, gn_vec)
    ranked = await client.rerank("estou ansioso com dívidas", [gn, fp], top_n=2)
    assert ranked[0][0] == 1
