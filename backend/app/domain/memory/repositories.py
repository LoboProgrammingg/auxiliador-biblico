import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.domain.bible.books import strip_accents
from app.domain.memory.errors import InvalidMemoryTopic

MAX_TOPIC = 60


@dataclass(frozen=True)
class MemoryItem:
    topic: str
    content: str
    updated_at: datetime


def normalize_topic(topic: str) -> str:
    if any(token in topic for token in ("/", "\\", "..")):
        raise InvalidMemoryTopic(topic)
    slug = re.sub(r"[^a-z0-9]+", "-", strip_accents(topic.strip().lower())).strip("-")
    if not slug or len(slug) > MAX_TOPIC or len(topic.strip()) > MAX_TOPIC:
        raise InvalidMemoryTopic(topic)
    return slug


class MemoryRepository(ABC):
    @abstractmethod
    async def list(self) -> list[MemoryItem]: ...

    @abstractmethod
    async def get(self, topic: str) -> str | None: ...

    @abstractmethod
    async def put(self, topic: str, content: str) -> None: ...

    @abstractmethod
    async def delete(self, topic: str) -> bool: ...
