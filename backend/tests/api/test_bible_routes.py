from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_embedder, get_reranker
from app.core.db import get_session
from app.main import create_app
from tests.fakes import FakeEmbedder


class NoRerank:
    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        from app.application.chat.ports import RerankUnavailable

        raise RerankUnavailable("off")


@pytest.fixture
async def api(bible_db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield bible_db

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_reranker] = lambda: NoRerank()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


async def test_passage_route_returns_verses(api: httpx.AsyncClient) -> None:
    r = await api.get("/api/v1/bible/passage", params={"ref": "Fp 2:2-3"})
    assert r.status_code == 200
    body = r.json()
    assert body["reference"] == "Fp 2:2-3" and body["translation"] == "vfl"
    assert [v["n"] for v in body["verses"]] == [2, 3]


async def test_passage_route_with_context_marks_cited_range(api: httpx.AsyncClient) -> None:
    r = await api.get("/api/v1/bible/passage", params={"ref": "Sl 2:3", "context": 2})
    body = r.json()
    assert [v["n"] for v in body["verses"]] == [1, 2, 3, 4, 5]
    assert [v["n"] for v in body["verses"] if v["cited"]] == [3]


async def test_passage_route_404_for_invalid_ref(api: httpx.AsyncClient) -> None:
    r = await api.get("/api/v1/bible/passage", params={"ref": "Jo 1:99"})
    assert r.status_code == 404
    assert r.json()["detail"] == "referência não encontrada"


async def test_passage_route_422_for_bad_context(api: httpx.AsyncClient) -> None:
    r = await api.get("/api/v1/bible/passage", params={"ref": "Fp 1:1", "context": 9})
    assert r.status_code == 422


async def test_compare_route_marks_unavailable_translation(api: httpx.AsyncClient) -> None:
    r = await api.get("/api/v1/bible/compare", params={"ref": "Jo 2:1", "translations": "acf,vfl"})
    items = {i["translation"]: i for i in r.json()["items"]}
    assert items["acf"]["verses"] and items["vfl"]["verses"] is None and items["vfl"]["note"]


async def test_original_route_returns_words_with_gloss(api: httpx.AsyncClient, bible_db: AsyncSession) -> None:
    await bible_db.execute(
        text(
            "INSERT INTO original_words (book_id, chapter, verse, position, surface, transliteration, gloss_en, "
            "strong, morphology, language) VALUES (50, 2, 3, 1, 'μεριμνᾶτε', 'merimnate', 'be anxious', "
            "'G3309', 'V-PAM-2P', 'grc')"
        )
    )
    await bible_db.execute(text("INSERT INTO lexicon VALUES ('G3309', 'μεριμνάω', 'merimnaō', 'to worry', 'd')"))
    r = await api.get("/api/v1/bible/original", params={"ref": "Fp 2:3"})
    word = r.json()["words"][0]
    assert word["strong"] == "G3309" and word["lexicon_gloss"] == "to worry" and word["lemma"] == "μεριμνάω"


async def test_cross_references_route_limit_validated(api: httpx.AsyncClient) -> None:
    assert (await api.get("/api/v1/bible/cross-references", params={"ref": "Fp 2:3", "limit": 51})).status_code == 422
    r = await api.get("/api/v1/bible/cross-references", params={"ref": "Fp 2:3"})
    assert r.status_code == 200 and r.json()["items"] == []


async def test_search_route_validates_and_returns(api: httpx.AsyncClient) -> None:
    assert (await api.get("/api/v1/bible/search", params={"q": "a"})).status_code == 422
    r = await api.get("/api/v1/bible/search", params={"q": "sintético Filipenses"})
    assert r.status_code == 200 and isinstance(r.json()["items"], list)
