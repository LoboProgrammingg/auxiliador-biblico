import uuid
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlDailyWordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, day: date) -> tuple[uuid.UUID, str | None] | None:
        result = await self._session.execute(
            text("SELECT conversation_id, reference FROM daily_words WHERE day = :d"), {"d": day}
        )
        row = result.first()
        return (row[0], row[1]) if row else None

    async def save(self, day: date, conversation_id: uuid.UUID, reference: str | None) -> None:
        await self._session.execute(
            text("INSERT INTO daily_words (day, conversation_id, reference) VALUES (:d, :c, :r)"),
            {"d": day, "c": conversation_id, "r": reference},
        )
        await self._session.commit()

    async def recent_references(self, day: date, days: int = 90) -> list[str]:
        result = await self._session.execute(
            text(
                "SELECT reference FROM daily_words WHERE day >= :since AND day < :d AND reference IS NOT NULL "
                "ORDER BY day DESC"
            ),
            {"since": day - timedelta(days=days), "d": day},
        )
        return [r for (r,) in result.all()]
