import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StartedPlan:
    id: uuid.UUID
    code: str
    started_on: date
    done_days: frozenset[int]


class PlanRepository(ABC):
    @abstractmethod
    async def create(self, code: str, started_on: date) -> uuid.UUID: ...

    @abstractmethod
    async def list_all(self) -> list[StartedPlan]: ...

    @abstractmethod
    async def get(self, plan_id: uuid.UUID) -> StartedPlan | None: ...

    @abstractmethod
    async def set_done(self, plan_id: uuid.UUID, day: int, done: bool) -> None: ...

    @abstractmethod
    async def delete(self, plan_id: uuid.UUID) -> bool: ...
