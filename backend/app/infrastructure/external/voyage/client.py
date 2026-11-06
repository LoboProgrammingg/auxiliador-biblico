import logging
from typing import Any, Literal

import voyageai
import voyageai.error

from app.application.chat.ports import EmbeddingUnavailable, RerankUnavailable

logger = logging.getLogger(__name__)


class VoyageClient:
    """Embeddings e rerank da Voyage AI (recomendada pela Anthropic; chave do MongoDB Atlas)."""

    def __init__(
        self,
        api_key: str | None,
        embed_model: str = "voyage-4-large",
        rerank_model: str = "rerank-3",
        dims: int = 1024,
        client: Any | None = None,
        max_retries: int = 6,
        timeout: float = 60,
    ) -> None:
        self._embed_model = embed_model
        self._rerank_model = rerank_model
        self._dims = dims
        self._client = client or (
            voyageai.AsyncClient(api_key=api_key, max_retries=max_retries, timeout=timeout) if api_key else None
        )

    async def embed(self, texts: list[str], kind: Literal["query", "document"]) -> list[list[float]]:
        if self._client is None:
            raise EmbeddingUnavailable("VOYAGE_API_KEY não configurada")
        try:
            result = await self._client.embed(
                texts, model=self._embed_model, input_type=kind, output_dimension=self._dims
            )
        except voyageai.error.VoyageError as exc:
            logger.warning("voyage embed indisponível: %s", type(exc).__name__)
            raise EmbeddingUnavailable(type(exc).__name__) from exc
        return [list(v) for v in result.embeddings]

    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        if self._client is None:
            raise RerankUnavailable("VOYAGE_API_KEY não configurada")
        try:
            result = await self._client.rerank(query, documents, model=self._rerank_model, top_k=top_n)
        except voyageai.error.VoyageError as exc:
            logger.warning("voyage rerank indisponível: %s", type(exc).__name__)
            raise RerankUnavailable(type(exc).__name__) from exc
        ranked = [(r.index, float(r.relevance_score)) for r in result.results]
        return sorted(ranked, key=lambda item: item[1], reverse=True)


def voyage_from_settings(interactive: bool = False) -> VoyageClient:
    """interactive=True: para a conversa (falha rápido e a busca cai para full-text); False: ingestão em lote."""
    from app.core.config import get_settings

    settings = get_settings()
    retries, timeout = (1, 15.0) if interactive else (6, 60.0)
    return VoyageClient(
        settings.voyage_api_key,
        settings.embed_model,
        settings.rerank_model,
        settings.embed_dims,
        max_retries=retries,
        timeout=timeout,
    )
