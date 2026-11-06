import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.plans.repositories import PlanRepository, StartedPlan

_SELECT = (
    "SELECT p.id, p.code, p.started_on, COALESCE(array_agg(d.day) FILTER (WHERE d.day IS NOT NULL), '{}') "
    "FROM reading_plans p LEFT JOIN plan_days_done d ON d.plan_id = p.id "
)


def _plan(row: tuple) -> StartedPlan:  # type: ignore[type-arg]
    return StartedPlan(row[0], row[1], row[2], frozenset(row[3]))


class SqlPlanRepository(PlanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, code: str, started_on: date) -> uuid.UUID:
        plan_id = uuid.uuid4()
        await self._session.execute(
            text("INSERT INTO reading_plans (id, code, started_on) VALUES (:id, :c, :s)"),
            {"id": plan_id, "c": code, "s": started_on},
        )
        await self._session.commit()
        return plan_id

    async def list_all(self) -> list[StartedPlan]:
        result = await self._session.execute(text(_SELECT + "GROUP BY p.id ORDER BY p.created_at DESC"))
        return [_plan(tuple(row)) for row in result.all()]

    async def get(self, plan_id: uuid.UUID) -> StartedPlan | None:
        result = await self._session.execute(text(_SELECT + "WHERE p.id = :id GROUP BY p.id"), {"id": plan_id})
        row = result.first()
        return _plan(tuple(row)) if row else None

    async def set_done(self, plan_id: uuid.UUID, day: int, done: bool) -> None:
        if done:
            sql = "INSERT INTO plan_days_done (plan_id, day) VALUES (:id, :d) ON CONFLICT DO NOTHING"
        else:
            sql = "DELETE FROM plan_days_done WHERE plan_id = :id AND day = :d"
        await self._session.execute(text(sql), {"id": plan_id, "d": day})
        await self._session.commit()

    async def delete(self, plan_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            text("DELETE FROM reading_plans WHERE id = :id RETURNING id"), {"id": plan_id}
        )
        deleted = result.first() is not None
        await self._session.commit()
        return deleted
