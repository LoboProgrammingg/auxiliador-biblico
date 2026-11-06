import uuid
from abc import ABC, abstractmethod
from typing import Any

from app.domain.conversation.entities import Conversation, Message


class ConversationRepository(ABC):
    @abstractmethod
    async def create(self) -> uuid.UUID: ...

    @abstractmethod
    async def get(self, conversation_id: uuid.UUID) -> Conversation | None: ...

    @abstractmethod
    async def recent(self) -> list[Conversation]: ...

    @abstractmethod
    async def delete(self, conversation_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def messages(self, conversation_id: uuid.UUID) -> list[Message]: ...

    @abstractmethod
    async def add_message(
        self, conversation_id: uuid.UUID, role: str, text: str | None, segments: list[dict[str, Any]] | None
    ) -> int: ...

    @abstractmethod
    async def set_session(self, conversation_id: uuid.UUID, session_id: str) -> None: ...

    @abstractmethod
    async def set_title_if_default(self, conversation_id: uuid.UUID, title: str) -> None: ...
