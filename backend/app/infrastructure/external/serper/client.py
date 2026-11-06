import httpx

from app.application.chat.ports import WebResult, WebSearchUnavailable

SERPER_URL = "https://google.serper.dev/search"


class SerperClient:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._transport = transport

    async def search(self, query: str, num: int = 5) -> list[WebResult]:
        payload = {"q": query, "gl": "br", "hl": "pt-br", "num": num}
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                for attempt in range(2):
                    try:
                        response = await client.post(SERPER_URL, json=payload, headers={"X-API-KEY": self._api_key})
                        response.raise_for_status()
                        break
                    except httpx.TransportError:
                        if attempt == 1:
                            raise
        except httpx.HTTPError as exc:
            raise WebSearchUnavailable(type(exc).__name__) from exc
        organic = response.json().get("organic", [])
        return [WebResult(o.get("title", ""), o.get("link", ""), o.get("snippet", "")) for o in organic[:num]]
