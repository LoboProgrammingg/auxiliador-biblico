import uuid
from collections.abc import AsyncIterator

import httpx
import pytest

from app.api.v1.export.router import get_exists, get_pdf_renderer
from app.infrastructure.pdf.chrome import PdfUnavailable
from app.main import create_app


class FakePdf:
    def __init__(self, fail: bool = False) -> None:
        self.urls: list[str] = []
        self.fail = fail

    async def render(self, url: str) -> bytes:
        self.urls.append(url)
        if self.fail:
            raise PdfUnavailable("sem chrome")
        return b"%PDF-1.7 fake"


@pytest.fixture
def fake() -> FakePdf:
    return FakePdf()


@pytest.fixture
async def api(fake: FakePdf) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_pdf_renderer] = lambda: fake

    async def always(_kind: str, _id: str) -> bool:
        return True

    app.dependency_overrides[get_exists] = lambda: always
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        yield client


async def test_export_conversation_pdf(api: httpx.AsyncClient, fake: FakePdf) -> None:
    cid = uuid.uuid4()
    r = await api.get(f"/api/v1/export/conversa/{cid}.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert f'filename="auxiliador-conversa-{str(cid)[:8]}.pdf"' in r.headers["content-disposition"]
    assert fake.urls == [f"http://127.0.0.1:3000/imprimir/conversa/{cid}"]


async def test_export_daily_word_and_plan(api: httpx.AsyncClient, fake: FakePdf) -> None:
    assert (await api.get("/api/v1/export/palavra/2026-11-06.pdf")).status_code == 200
    pid = uuid.uuid4()
    assert (await api.get(f"/api/v1/export/plano/{pid}.pdf")).status_code == 200
    assert fake.urls[-2:] == [
        "http://127.0.0.1:3000/imprimir/palavra/2026-11-06",
        f"http://127.0.0.1:3000/imprimir/plano/{pid}",
    ]


@pytest.mark.parametrize(
    "path",
    ["/api/v1/export/conversa/nao-e-uuid.pdf", "/api/v1/export/palavra/06-11-2026.pdf", "/api/v1/export/outro/x.pdf"],
)
async def test_export_rejects_bad_ids(api: httpx.AsyncClient, fake: FakePdf, path: str) -> None:
    assert (await api.get(path)).status_code in (404, 422)
    assert fake.urls == []


async def test_export_without_chrome_is_503(api: httpx.AsyncClient, fake: FakePdf) -> None:
    fake.fail = True
    r = await api.get(f"/api/v1/export/conversa/{uuid.uuid4()}.pdf")
    assert r.status_code == 503 and "Chrome" in r.json()["detail"]


async def test_export_checks_that_the_item_exists(fake: FakePdf, bible_db) -> None:  # type: ignore[no-untyped-def]
    from contextlib import asynccontextmanager

    from app.api.v1.chat.router import get_session_factory
    from app.core.db import get_session
    from app.infrastructure.database.conversation_repository import SqlConversationRepository

    app = create_app()
    app.dependency_overrides[get_pdf_renderer] = lambda: fake

    async def session_override():  # type: ignore[no-untyped-def]
        yield bible_db

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_session_factory] = lambda: asynccontextmanager(session_override)
    cid = await SqlConversationRepository(bible_db).create()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as c:
        assert (await c.get(f"/api/v1/export/conversa/{cid}.pdf")).status_code == 200
        assert (await c.get(f"/api/v1/export/conversa/{uuid.uuid4()}.pdf")).status_code == 404
        assert (await c.get("/api/v1/export/palavra/2001-01-01.pdf")).status_code == 404
        assert (await c.get(f"/api/v1/export/plano/{uuid.uuid4()}.pdf")).status_code == 404
    assert len(fake.urls) == 1
