import re
from collections.abc import Awaitable, Callable
from datetime import date

from app.domain.memory.errors import InvalidMemoryContent
from app.domain.memory.repositories import MemoryItem, MemoryRepository, normalize_topic

MAX_CONTENT = 4000
_LEADING_DATE = re.compile(r"^\s*-?\s*\d{4}-\d{2}-\d{2}\s*[:\-–]\s*")


def _check(content: str) -> str:
    cleaned = content.strip()
    if not cleaned or len(cleaned) > MAX_CONTENT:
        raise InvalidMemoryContent(f"conteúdo deve ter 1..{MAX_CONTENT} caracteres")
    return cleaned


class MemoryService:
    def __init__(self, repo: MemoryRepository, sensitive_check: Callable[[str], Awaitable[bool]] | None = None) -> None:
        self._repo = repo
        self._sensitive_check = sensitive_check

    async def _guard(self, content: str) -> None:
        if self._sensitive_check is not None and await self._sensitive_check(content):
            raise InvalidMemoryContent("não guardo dados sensíveis (CPF, senhas, cartões, contas)")

    async def list_all(self) -> list[MemoryItem]:
        return await self._repo.list()

    async def save(self, topic: str, content: str) -> str:
        slug = normalize_topic(topic)
        await self._guard(content)
        await self._repo.put(slug, _check(content))
        return slug

    async def append(self, topic: str, note: str) -> str:
        slug = normalize_topic(topic)
        await self._guard(note)
        current = await self._repo.get(slug)
        line = f"- {date.today().isoformat()}: {_LEADING_DATE.sub('', note.strip())}"
        await self._repo.put(slug, _check(f"{current}\n{line}" if current else line))
        return slug

    async def forget(self, topic: str) -> bool:
        return await self._repo.delete(normalize_topic(topic))
