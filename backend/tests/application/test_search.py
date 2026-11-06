from app.application.bible.search import rrf_merge
from app.application.chat.ports import EmbeddingUnavailable, RerankUnavailable
from app.domain.bible.entities import PassageHit


def hit(book: int, ch: int, vs: int, ve: int, t: str = "vfl") -> PassageHit:
    return PassageHit(t, book, ch, vs, ve, f"texto {book} {ch}:{vs}", 0.0)


def test_rrf_merge_prefers_items_in_both_lists() -> None:
    a, b, c = hit(1, 1, 1, 1), hit(2, 1, 1, 1), hit(3, 1, 1, 1)
    merged = rrf_merge([[a, b], [c, a]], k=60)
    assert merged[0] == a
    assert set(merged) == {a, b, c}


class FakeRepo:
    def __init__(self, ft: list[PassageHit], vec: list[PassageHit]) -> None:
        self.ft, self.vec = ft, vec

    async def fulltext(self, query: str, translations: list[str], limit: int) -> list[PassageHit]:
        return self.ft

    async def nearest(self, embedding: list[float], translations: list[str], limit: int) -> list[PassageHit]:
        return self.vec


class FakePassages:
    async def resolve(self, ref, translation=None):  # type: ignore[no-untyped-def]
        return ref


class Embedder:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def embed(self, texts: list[str], kind: str) -> list[list[float]]:
        if self.fail:
            raise EmbeddingUnavailable("x")
        return [[0.0]]


class Reranker:
    def __init__(self, order: list[int] | None = None) -> None:
        self.order = order

    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        if self.order is None:
            raise RerankUnavailable("x")
        return [(i, 1.0 - n / 10) for n, i in enumerate(self.order)][:top_n]


def service(ft, vec, embed_fail=False, order=None):  # type: ignore[no-untyped-def]
    from app.application.bible.search import SearchService

    return SearchService(FakeRepo(ft, vec), FakePassages(), Embedder(embed_fail), Reranker(order))


async def test_rrf_then_rerank_orders_by_reranker() -> None:
    a, b = hit(1, 1, 1, 1), hit(2, 1, 1, 1)
    results = await service([a, b], [a, b], order=[1, 0]).search("q", limit=2)
    assert [r.book_id for r in results] == [2, 1]


async def test_search_uses_rrf_order_when_reranker_unavailable() -> None:
    a, b = hit(1, 1, 1, 1), hit(2, 1, 1, 1)
    results = await service([b, a], [a], order=None).search("q", limit=2)
    assert [r.book_id for r in results] == [1, 2]


async def test_search_degrades_to_fulltext_when_embedder_unavailable() -> None:
    a = hit(5, 1, 1, 1)
    results = await service([a], [hit(9, 9, 9, 9)], embed_fail=True, order=None).search("q", limit=3)
    assert [r.book_id for r in results] == [5]


async def test_search_dedupes_by_start_verse_across_translations() -> None:
    a, a_nvt = hit(1, 1, 1, 4, "vfl"), hit(1, 1, 1, 1, "nvt")
    results = await service([a, a_nvt], [], order=None).search("q", limit=5)
    assert len(results) == 1
