import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.domain.bible.repositories import BibleRepository
from app.domain.plans.catalog import CATALOG, PlanInfo, Reading, plan_days
from app.domain.plans.repositories import PlanRepository, StartedPlan

_SIZES: dict[tuple[int, int], int] = {}


class UnknownPlan(Exception):
    pass


class DayOutOfRange(Exception):
    pass


@dataclass(frozen=True)
class PlanView:
    id: uuid.UUID
    code: str
    name: str
    description: str
    started_on: date
    today_day: int
    total: int
    done: int
    days: list[tuple[int, list[Reading], bool]]


class PlanService:
    def __init__(self, plans: PlanRepository, bible: BibleRepository, today: Callable[[], date] = date.today) -> None:
        self._plans, self._bible, self._today = plans, bible, today

    async def _sizes(self) -> dict[tuple[int, int], int]:
        sizes = _SIZES or await self._bible.chapter_sizes()
        if len(sizes) >= 1189:
            _SIZES.update(sizes)
        return sizes

    async def _view(self, plan: StartedPlan) -> PlanView:
        info: PlanInfo = CATALOG[plan.code]
        days = plan_days(plan.code, await self._sizes())
        elapsed = (self._today() - plan.started_on).days + 1
        return PlanView(
            plan.id,
            plan.code,
            info.name,
            info.description,
            plan.started_on,
            max(1, min(len(days), elapsed)),
            len(days),
            len(plan.done_days),
            [(n, readings, n in plan.done_days) for n, readings in enumerate(days, start=1)],
        )

    async def start(self, code: str, started_on: date | None) -> uuid.UUID:
        if code not in CATALOG:
            raise UnknownPlan(code)
        return await self._plans.create(code, started_on or self._today())

    async def all(self) -> list[PlanView]:
        return [await self._view(p) for p in await self._plans.list_all() if p.code in CATALOG]

    async def get(self, plan_id: uuid.UUID) -> PlanView | None:
        plan = await self._plans.get(plan_id)
        return await self._view(plan) if plan is not None and plan.code in CATALOG else None

    async def mark(self, plan_id: uuid.UUID, day: int, done: bool) -> bool:
        view = await self.get(plan_id)
        if view is None:
            return False
        if not 1 <= day <= view.total:
            raise DayOutOfRange(day)
        await self._plans.set_done(plan_id, day, done)
        return True
