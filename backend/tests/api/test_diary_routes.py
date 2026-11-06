import uuid
from collections.abc import AsyncIterator
from datetime import date

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.daily_word_repository import SqlDailyWordRepository
from app.main import create_app


@pytest.fixture
async def api(bible_db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield bible_db

    app.dependency_overrides[get_session] = session_override
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


async def test_prayer_lifecycle(api: httpx.AsyncClient) -> None:
    assert (await api.get("/api/v1/prayers")).json() == {"items": []}
    created = await api.post("/api/v1/prayers", json={"title": "Saúde da minha mãe", "details": "Internada"})
    assert created.status_code == 201
    prayer = created.json()
    assert prayer["status"] == "aberto" and prayer["answered_at"] is None
    r = await api.put(
        f"/api/v1/prayers/{prayer['id']}",
        json={
            "title": "Saúde da minha mãe",
            "details": "Internada",
            "status": "respondido",
            "answer_note": "Teve alta",
        },
    )
    assert r.status_code == 200 and r.json()["status"] == "respondido" and r.json()["answered_at"]
    reopened = await api.put(
        f"/api/v1/prayers/{prayer['id']}", json={"title": "Saúde da minha mãe", "status": "aberto"}
    )
    assert reopened.json()["answered_at"] is None
    assert (await api.delete(f"/api/v1/prayers/{prayer['id']}")).status_code == 204
    assert (await api.delete(f"/api/v1/prayers/{prayer['id']}")).status_code == 404
    assert (
        await api.put(f"/api/v1/prayers/{uuid.uuid4()}", json={"title": "x", "status": "aberto"})
    ).status_code == 404


async def test_prayer_validation(api: httpx.AsyncClient) -> None:
    assert (await api.post("/api/v1/prayers", json={"title": ""})).status_code == 422
    created = (await api.post("/api/v1/prayers", json={"title": "Emprego"})).json()
    bad = await api.put(f"/api/v1/prayers/{created['id']}", json={"title": "Emprego", "status": "talvez"})
    assert bad.status_code == 422


async def test_verse_note_upsert_and_lookup(api: httpx.AsyncClient) -> None:
    r = await api.put("/api/v1/verse-notes", params={"ref": "Salmos 2:3"}, json={"content": "Lembrar disto na prova."})
    assert r.status_code == 200 and r.json()["reference"] == "Sl 2:3"
    again = await api.put("/api/v1/verse-notes", params={"ref": "Sl 2:3"}, json={"content": "Atualizado."})
    assert again.json()["id"] == r.json()["id"] and again.json()["content"] == "Atualizado."
    found = (await api.get("/api/v1/verse-notes/by-ref", params={"ref": "Sl 2:3"})).json()
    assert found["content"] == "Atualizado."
    assert (await api.get("/api/v1/verse-notes/by-ref", params={"ref": "Sl 2:4"})).status_code == 404
    chapter = await api.put("/api/v1/verse-notes", params={"ref": "Sl 2"}, json={"content": "Capítulo inteiro."})
    assert chapter.status_code == 200 and chapter.json()["reference"] == "Sl 2"
    items = (await api.get("/api/v1/verse-notes")).json()["items"]
    assert {i["reference"] for i in items} == {"Sl 2:3", "Sl 2"}
    assert (await api.delete(f"/api/v1/verse-notes/{r.json()['id']}")).status_code == 204


@pytest.mark.parametrize("ref", ["Sl 2:99", "Sl 9:1", "Livro 1:1", "xx"])
async def test_verse_note_rejects_invalid_reference(api: httpx.AsyncClient, ref: str) -> None:
    r = await api.put("/api/v1/verse-notes", params={"ref": ref}, json={"content": "nota"})
    assert r.status_code == 422


async def test_daily_word_history(api: httpx.AsyncClient, bible_db: AsyncSession) -> None:
    conversations, daily = SqlConversationRepository(bible_db), SqlDailyWordRepository(bible_db)
    for day, ref in ((date(2026, 11, 1), "Sl 2:3"), (date(2026, 11, 3), "Fp 2:3")):
        await daily.save(day, await conversations.create(kind="palavra"), ref)
    items = (await api.get("/api/v1/daily-words")).json()["items"]
    assert [(i["day"], i["reference"]) for i in items] == [("2026-11-03", "Fp 2:3"), ("2026-11-01", "Sl 2:3")]
    assert items[0]["conversation_id"]
