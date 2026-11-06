from collections.abc import AsyncIterator
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.main import create_app


@pytest.fixture
async def api(bible_db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield bible_db

    app.dependency_overrides[get_session] = session_override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


async def test_catalog(api: httpx.AsyncClient) -> None:
    items = (await api.get("/api/v1/plans/catalog")).json()["items"]
    codes = {i["code"]: i for i in items}
    assert codes["biblia-1-ano"]["days"] == 365 and codes["evangelhos-30"]["days"] == 30
    assert codes["perdao-recomeco"]["name"] == "Perdão e recomeço"


async def test_start_follow_and_mark_days(api: httpx.AsyncClient) -> None:
    started = (date.today() - timedelta(days=2)).isoformat()
    created = await api.post("/api/v1/plans", json={"code": "evangelhos-30", "started_on": started})
    assert created.status_code == 201
    plan_id = created.json()["id"]
    detail = (await api.get(f"/api/v1/plans/{plan_id}")).json()
    # banco sintético: 4 evangelhos x 2 capítulos -> um capítulo por dia
    assert detail["name"] == "Evangelhos em 30 dias" and len(detail["days"]) == 8
    assert detail["today_day"] == 3
    assert detail["days"][0]["readings"][0].startswith("Mt 1")
    assert (await api.put(f"/api/v1/plans/{plan_id}/days/1", json={"done": True})).status_code == 204
    assert (await api.put(f"/api/v1/plans/{plan_id}/days/2", json={"done": True})).status_code == 204
    assert (await api.put(f"/api/v1/plans/{plan_id}/days/2", json={"done": False})).status_code == 204
    listed = (await api.get("/api/v1/plans")).json()["items"]
    assert [(p["id"], p["done"], p["total"]) for p in listed] == [(plan_id, 1, 8)]
    detail = (await api.get(f"/api/v1/plans/{plan_id}")).json()
    assert [d["done"] for d in detail["days"][:3]] == [True, False, False]
    assert (await api.put(f"/api/v1/plans/{plan_id}/days/9", json={"done": True})).status_code == 422
    assert (await api.delete(f"/api/v1/plans/{plan_id}")).status_code == 204
    assert (await api.get(f"/api/v1/plans/{plan_id}")).status_code == 404


async def test_rejects_unknown_plan(api: httpx.AsyncClient) -> None:
    assert (await api.post("/api/v1/plans", json={"code": "nao-existe"})).status_code == 422


async def test_theme_plan_today_day_is_capped(api: httpx.AsyncClient) -> None:
    started = (date.today() - timedelta(days=40)).isoformat()
    plan_id = (await api.post("/api/v1/plans", json={"code": "familia", "started_on": started})).json()["id"]
    detail = (await api.get(f"/api/v1/plans/{plan_id}")).json()
    assert detail["today_day"] == 7 and detail["days"][6]["readings"] == ["Sl 127"]
