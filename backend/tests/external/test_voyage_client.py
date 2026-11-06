from dataclasses import dataclass, field

import pytest
import voyageai.error

from app.application.chat.ports import EmbeddingUnavailable, RerankUnavailable
from app.infrastructure.external.voyage.client import VoyageClient


@dataclass
class _Result:
    index: int
    relevance_score: float


@dataclass
class FakeVoyage:
    calls: list[dict[str, object]] = field(default_factory=list)
    fail_with: Exception | None = None

    async def embed(self, texts: list[str], **kwargs: object) -> object:
        self.calls.append({"texts": texts, **kwargs})
        if self.fail_with:
            raise self.fail_with
        return type("E", (), {"embeddings": [[0.1] * 4 for _ in texts]})()

    async def rerank(self, query: str, documents: list[str], **kwargs: object) -> object:
        self.calls.append({"query": query, "documents": documents, **kwargs})
        if self.fail_with:
            raise self.fail_with
        return type("R", (), {"results": [_Result(1, 0.9), _Result(0, 0.2)]})()


async def test_voyage_embed_sends_input_type_and_dims() -> None:
    fake = FakeVoyage()
    client = VoyageClient(api_key="k", client=fake)
    vectors = await client.embed(["a", "b"], "query")
    assert len(vectors) == 2
    call = fake.calls[0]
    assert call["input_type"] == "query" and call["output_dimension"] == 1024 and call["model"] == "voyage-4-large"


async def test_voyage_rerank_parses_results_sorted() -> None:
    client = VoyageClient(api_key="k", client=FakeVoyage())
    assert await client.rerank("q", ["x", "y"], top_n=2) == [(1, 0.9), (0, 0.2)]


async def test_voyage_errors_become_unavailable() -> None:
    client = VoyageClient(api_key="k", client=FakeVoyage(fail_with=voyageai.error.ServiceUnavailableError("down")))
    with pytest.raises(EmbeddingUnavailable):
        await client.embed(["a"], "document")
    with pytest.raises(RerankUnavailable):
        await client.rerank("q", ["x"], top_n=1)


async def test_voyage_without_key_raises_unavailable() -> None:
    client = VoyageClient(api_key=None)
    with pytest.raises(EmbeddingUnavailable):
        await client.embed(["a"], "query")
    with pytest.raises(RerankUnavailable):
        await client.rerank("q", ["x"], top_n=1)


def test_interactive_client_fails_fast(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import get_settings
    from app.infrastructure.external.voyage.client import voyage_from_settings

    monkeypatch.setattr(get_settings(), "voyage_api_key", "k")
    assert voyage_from_settings(interactive=True)._client.max_retries == 1
    assert voyage_from_settings()._client.max_retries == 6
