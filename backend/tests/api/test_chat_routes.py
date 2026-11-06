import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_embedder, get_reranker
from app.api.v1.chat.router import get_agent_runner, get_judgments, get_session_factory
from app.application.judgments.service import JudgmentService
from app.core.db import get_session
from app.main import create_app
from tests.api.test_bible_routes import NoRerank
from tests.chat_fakes import FakeAgentRunner
from tests.fakes import FakeEmbedder


@pytest.fixture
async def api(bible_db: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def session_override() -> AsyncIterator[AsyncSession]:
        yield bible_db

    @asynccontextmanager
    async def factory() -> AsyncIterator[AsyncSession]:
        yield bible_db

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_agent_runner] = lambda: FakeAgentRunner(["Paz! ", "[[Fp 2:3]]"])
    app.dependency_overrides[get_judgments] = lambda: JudgmentService(None)
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_reranker] = lambda: NoRerank()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


def parse_sse(body: str) -> list[tuple[str, dict]]:  # type: ignore[type-arg]
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def test_conversation_lifecycle_and_sse(api: httpx.AsyncClient) -> None:
    cid = (await api.post("/api/v1/conversations")).json()["id"]
    r = await api.post(f"/api/v1/conversations/{cid}/messages", json={"text": "Estou ansioso com as contas"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    names = [name for name, _ in parse_sse(r.text)]
    assert names == ["text", "verse", "issues", "done"]
    convs = (await api.get("/api/v1/conversations")).json()["items"]
    assert convs[0]["id"] == cid and convs[0]["title"] == "Estou ansioso com as contas"
    msgs = (await api.get(f"/api/v1/conversations/{cid}/messages")).json()["items"]
    assert msgs[0] == {
        "role": "user",
        "text": "Estou ansioso com as contas",
        "segments": None,
        "created_at": msgs[0]["created_at"],
    }
    assert [s["type"] for s in msgs[1]["segments"]] == ["text", "verse"]
    assert (await api.delete(f"/api/v1/conversations/{cid}")).status_code == 204
    assert (await api.get(f"/api/v1/conversations/{cid}/messages")).status_code == 404


async def test_message_text_validation(api: httpx.AsyncClient) -> None:
    cid = (await api.post("/api/v1/conversations")).json()["id"]
    assert (await api.post(f"/api/v1/conversations/{cid}/messages", json={"text": ""})).status_code == 422
    assert (await api.post(f"/api/v1/conversations/{cid}/messages", json={"text": "x" * 8001})).status_code == 422


async def test_health_reports_agent_mode(api: httpx.AsyncClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    body = (await api.get("/api/v1/health")).json()
    assert body["status"] == "ok" and body["agente"] == "assinatura_local"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert (await api.get("/api/v1/health")).json()["agente"] == "chave_paga_bloqueada"
