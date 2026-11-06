import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversation.entities import Conversation, Message
from app.domain.conversation.repositories import ConversationRepository

DEFAULT_TITLE = "Nova conversa"


class SqlConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, kind: str = "chat") -> uuid.UUID:
        new_id = uuid.uuid4()
        await self._session.execute(
            text("INSERT INTO conversations (id, title, kind) VALUES (:id, :t, :k)"),
            {"id": new_id, "t": DEFAULT_TITLE, "k": kind},
        )
        await self._session.commit()
        return new_id

    async def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            text("SELECT id, title, agent_session_id, updated_at FROM conversations WHERE id = :id"),
            {"id": conversation_id},
        )
        row = result.first()
        return Conversation(*row) if row else None

    async def recent(self) -> list[Conversation]:
        result = await self._session.execute(
            text(
                "SELECT id, title, agent_session_id, updated_at FROM conversations WHERE kind = 'chat' "
                "ORDER BY updated_at DESC LIMIT 200"
            )
        )
        return [Conversation(*row) for row in result.all()]

    async def delete(self, conversation_id: uuid.UUID) -> bool:
        result = await self._session.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id})
        await self._session.commit()
        return bool(result.rowcount)

    async def messages(self, conversation_id: uuid.UUID) -> list[Message]:
        result = await self._session.execute(
            text(
                "SELECT id, role, text, display_segments, created_at FROM messages "
                "WHERE conversation_id = :id ORDER BY seq"
            ),
            {"id": conversation_id},
        )
        return [Message(*row) for row in result.all()]

    async def add_message(
        self, conversation_id: uuid.UUID, role: str, text_value: str | None, segments: list[dict[str, Any]] | None
    ) -> int:
        result = await self._session.execute(
            text(
                "INSERT INTO messages (conversation_id, seq, role, text, display_segments) "
                "SELECT :id, COALESCE(max(seq), 0) + 1, :role, :text, CAST(:seg AS jsonb) "
                "FROM messages WHERE conversation_id = :id RETURNING id"
            ),
            {
                "id": conversation_id,
                "role": role,
                "text": text_value,
                "seg": json.dumps(segments, ensure_ascii=False) if segments is not None else None,
            },
        )
        message_id = int(result.scalar_one())
        await self._session.execute(
            text("UPDATE conversations SET updated_at = now() WHERE id = :id"), {"id": conversation_id}
        )
        await self._session.commit()
        return message_id

    async def set_session(self, conversation_id: uuid.UUID, session_id: str) -> None:
        await self._session.execute(
            text("UPDATE conversations SET agent_session_id = :s WHERE id = :id"),
            {"s": session_id, "id": conversation_id},
        )
        await self._session.commit()

    async def set_title_if_default(self, conversation_id: uuid.UUID, title: str) -> None:
        await self._session.execute(
            text("UPDATE conversations SET title = :t WHERE id = :id AND title = :d"),
            {"t": title[:60], "id": conversation_id, "d": DEFAULT_TITLE},
        )
        await self._session.commit()
