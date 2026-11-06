from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol


class EmbeddingUnavailable(Exception):
    pass


class RerankUnavailable(Exception):
    pass


class Embedder(Protocol):
    async def embed(self, texts: list[str], kind: Literal["query", "document"]) -> list[list[float]]: ...


class Reranker(Protocol):
    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]: ...


class WebSearchUnavailable(Exception):
    pass


class WebResult:
    __slots__ = ("title", "link", "snippet")

    def __init__(self, title: str, link: str, snippet: str) -> None:
        self.title, self.link, self.snippet = title, link, snippet


class WebSearch(Protocol):
    async def search(self, query: str, num: int = 5) -> list[WebResult]: ...


@dataclass(frozen=True)
class AgentText:
    text: str


@dataclass(frozen=True)
class AgentToolStart:
    name: str


@dataclass(frozen=True)
class AgentDone:
    session_id: str
    is_error: bool
    error: str | None


@dataclass(frozen=True)
class AgentTools:
    server: Any
    allowed: list[str]
    invoke: Callable[[str, dict[str, Any]], Awaitable[Any]]


AgentEvent = AgentText | AgentToolStart | AgentDone


class AgentRunner(Protocol):
    def run(
        self, prompt: str, session_id: str | None, tools: AgentTools, effort: str | None = None
    ) -> AsyncIterator[AgentEvent]: ...
