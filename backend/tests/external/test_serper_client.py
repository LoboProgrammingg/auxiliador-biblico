import httpx
import pytest

from app.application.chat.ports import WebSearchUnavailable
from app.infrastructure.external.serper.client import SerperClient


async def test_serper_client_parses_organic() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-KEY"] == "k" and request.url.path == "/search"
        return httpx.Response(200, json={"organic": [{"title": "T", "link": "https://a.b", "snippet": "S"}]})

    client = SerperClient("k", transport=httpx.MockTransport(handler))
    results = await client.search("Filipos")
    assert [(r.title, r.link, r.snippet) for r in results] == [("T", "https://a.b", "S")]


async def test_serper_timeout_raises_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("t")

    client = SerperClient("k", transport=httpx.MockTransport(handler))
    with pytest.raises(WebSearchUnavailable):
        await client.search("x")
