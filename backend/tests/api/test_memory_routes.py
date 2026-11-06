from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.main import create_app


@pytest.fixture
async def api(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = session_override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


async def test_routes_list_edit_delete(api: httpx.AsyncClient) -> None:
    assert (await api.get("/api/v1/memories")).json() == {"items": []}
    r = await api.put("/api/v1/memories/Familia", json={"content": "Casado, dois filhos."})
    assert r.status_code == 200 and r.json()["topic"] == "familia"
    items = (await api.get("/api/v1/memories")).json()["items"]
    assert [i["topic"] for i in items] == ["familia"] and items[0]["updated_at"]
    assert (await api.delete("/api/v1/memories/familia")).status_code == 204
    assert (await api.delete("/api/v1/memories/familia")).status_code == 404


async def test_invalid_payloads(api: httpx.AsyncClient) -> None:
    assert (await api.put("/api/v1/memories/x", json={"content": ""})).status_code == 422
    assert (await api.put("/api/v1/memories/%2E%2E", json={"content": "y"})).status_code == 422
