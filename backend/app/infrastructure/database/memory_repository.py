from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.repositories import MemoryItem, MemoryRepository


class SqlMemoryRepository(MemoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[MemoryItem]:
        result = await self._session.execute(
            text("SELECT path, content, updated_at FROM memories ORDER BY updated_at DESC, path")
        )
        return [MemoryItem(*row) for row in result.all()]

    async def get(self, topic: str) -> str | None:
        result = await self._session.execute(text("SELECT content FROM memories WHERE path = :p"), {"p": topic})
        return result.scalar_one_or_none()

    async def put(self, topic: str, content: str) -> None:
        await self._session.execute(
            text(
                "INSERT INTO memories (path, content) VALUES (:p, :c) "
                "ON CONFLICT (path) DO UPDATE SET content = EXCLUDED.content, updated_at = now()"
            ),
            {"p": topic, "c": content},
        )
        await self._session.commit()

    async def delete(self, topic: str) -> bool:
        result = await self._session.execute(text("DELETE FROM memories WHERE path = :p"), {"p": topic})
        await self._session.commit()
        return bool(result.rowcount)
