import logging
from typing import Protocol

from app.application.chat.ports import Embedder, EmbeddingUnavailable, Reranker, RerankUnavailable
from app.domain.bible.entities import PassageHit, ResolvedPassage
from app.domain.bible.references import VerseRange

logger = logging.getLogger(__name__)

INDEXED = ["vfl", "nvt", "acf"]
CANDIDATES = 30


class _Repo(Protocol):
    async def fulltext(self, query: str, translations: list[str], limit: int) -> list[PassageHit]: ...
    async def nearest(self, embedding: list[float], translations: list[str], limit: int) -> list[PassageHit]: ...


class _Passages(Protocol):
    async def resolve(self, ref: VerseRange, translation: str | None = None) -> ResolvedPassage: ...


def rrf_merge(rankings: list[list[PassageHit]], k: int = 60) -> list[PassageHit]:
    scores: dict[PassageHit, float] = {}
    for ranking in rankings:
        for position, hit in enumerate(ranking):
            scores[hit] = scores.get(hit, 0.0) + 1.0 / (k + position + 1)
    return sorted(scores, key=lambda h: scores[h], reverse=True)


def _dedupe(hits: list[PassageHit]) -> list[PassageHit]:
    seen: set[tuple[int, int, int]] = set()
    unique: list[PassageHit] = []
    for hit in hits:
        key = (hit.book_id, hit.chapter, hit.verse_start)
        if key not in seen:
            seen.add(key)
            unique.append(hit)
    return unique


class SearchService:
    def __init__(self, repo: _Repo, passages: _Passages, embedder: Embedder, reranker: Reranker) -> None:
        self._repo, self._passages, self._embedder, self._reranker = repo, passages, embedder, reranker

    async def _candidates(self, query: str) -> list[PassageHit]:
        rankings = [await self._repo.fulltext(query, INDEXED, CANDIDATES)]
        try:
            (vector,) = await self._embedder.embed([query], "query")
            rankings.append(await self._repo.nearest(vector, INDEXED, CANDIDATES))
        except EmbeddingUnavailable:
            logger.warning("busca sem embeddings: usando só full-text")
        return _dedupe(rrf_merge(rankings))[:CANDIDATES]

    async def _rank(self, query: str, hits: list[PassageHit], limit: int) -> list[PassageHit]:
        if not hits:
            return []
        try:
            order = await self._reranker.rerank(query, [h.text for h in hits], top_n=limit)
            return [hits[i] for i, _ in order]
        except RerankUnavailable:
            logger.warning("busca sem reranker: usando ordem RRF")
            return hits[:limit]

    async def search(self, query: str, limit: int = 8) -> list[ResolvedPassage]:
        hits = await self._rank(query, await self._candidates(query), limit)
        return [
            await self._passages.resolve(VerseRange(h.book_id, h.chapter, h.verse_start, h.verse_end)) for h in hits
        ]
