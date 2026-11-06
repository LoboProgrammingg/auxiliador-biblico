import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.plans.service import DayOutOfRange, PlanService, PlanView, UnknownPlan
from app.core.db import get_session
from app.domain.plans.catalog import CATALOG
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.plan_repository import SqlPlanRepository

router = APIRouter(prefix="/plans", tags=["plans"])


def get_plan_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PlanService:
    return PlanService(SqlPlanRepository(session), SqlBibleRepository(session))


Service = Annotated[PlanService, Depends(get_plan_service)]


class CatalogItem(BaseModel):
    code: str
    name: str
    description: str
    days: int


class Catalog(BaseModel):
    items: list[CatalogItem]


class StartIn(BaseModel):
    code: str
    started_on: date | None = None


class CreatedOut(BaseModel):
    id: uuid.UUID


class DayOut(BaseModel):
    day: int
    readings: list[str]
    done: bool


class PlanSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    started_on: date
    today_day: int
    total: int
    done: int


class PlanDetail(PlanSummary):
    days: list[DayOut]


class PlanList(BaseModel):
    items: list[PlanSummary]


class DoneIn(BaseModel):
    done: bool


def _summary(v: PlanView) -> dict[str, object]:
    return {k: getattr(v, k) for k in PlanSummary.model_fields}


@router.get("/catalog", response_model=Catalog)
async def catalog() -> Catalog:
    return Catalog(items=[CatalogItem(**info.__dict__) for info in CATALOG.values()])


@router.post("", response_model=CreatedOut, status_code=201)
async def start_plan(body: StartIn, service: Service) -> CreatedOut:
    try:
        return CreatedOut(id=await service.start(body.code, body.started_on))
    except UnknownPlan as exc:
        raise HTTPException(status_code=422, detail="plano desconhecido") from exc


@router.get("", response_model=PlanList)
async def list_plans(service: Service) -> PlanList:
    return PlanList(items=[PlanSummary(**_summary(v)) for v in await service.all()])  # type: ignore[arg-type]


@router.get("/{plan_id}", response_model=PlanDetail)
async def get_plan(plan_id: uuid.UUID, service: Service) -> PlanDetail:
    view = await service.get(plan_id)
    if view is None:
        raise HTTPException(status_code=404, detail="plano não encontrado")
    days = [DayOut(day=n, readings=[r.label for r in readings], done=done) for n, readings, done in view.days]
    return PlanDetail(**_summary(view), days=days)  # type: ignore[arg-type]


@router.put("/{plan_id}/days/{day}", status_code=204)
async def mark_day(plan_id: uuid.UUID, day: int, body: DoneIn, service: Service) -> Response:
    try:
        found = await service.mark(plan_id, day, body.done)
    except DayOutOfRange as exc:
        raise HTTPException(status_code=422, detail="dia fora do plano") from exc
    if not found:
        raise HTTPException(status_code=404, detail="plano não encontrado")
    return Response(status_code=204)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: uuid.UUID, session: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    if not await SqlPlanRepository(session).delete(plan_id):
        raise HTTPException(status_code=404, detail="plano não encontrado")
    return Response(status_code=204)
