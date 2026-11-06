"""Testes das correções da revisão final."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.chat.router import _chat_service
from app.application.judgments.service import JudgmentService
from app.application.memory.service import MemoryService
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.memory_repository import SqlMemoryRepository
from tests.api.test_bible_routes import NoRerank
from tests.chat_fakes import FakeAgentRunner
from tests.fakes import FakeEmbedder
from tests.judge_fakes import FakeJudge


async def test_production_chat_service_blocks_sensitive_memory(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner([("tool", "memoria_salvar", {"topico": "dados", "conteudo": "meu CPF 123.456.789-09"})])
    service = _chat_service(bible_db, runner, FakeEmbedder(), NoRerank(), JudgmentService(FakeJudge()))
    cid: uuid.UUID = await SqlConversationRepository(bible_db).create()
    events = [e async for e in service.send(cid, "guarde isso")]
    assert not any(e.name == "memory_saved" for e in events)
    assert await MemoryService(SqlMemoryRepository(bible_db)).list_all() == []


async def test_production_chat_service_runs_jev_triage(bible_db: AsyncSession) -> None:
    judge = FakeJudge(nouls={"crise": 0.9}, choices={"momento": ("outro", 0.9)}, scores={"angustia": (3.0, 0.9)})
    service = _chat_service(
        bible_db, FakeAgentRunner(["Estou aqui."]), FakeEmbedder(), NoRerank(), JudgmentService(judge)
    )
    cid = await SqlConversationRepository(bible_db).create()
    names = [e.name async for e in service.send(cid, "quero sumir")]
    assert names[0] == "crisis"


async def test_popup_context_keeps_fallback_label(bible_db: AsyncSession) -> None:
    from app.application.bible.passages import PassageService
    from app.infrastructure.database.bible_repository import SqlBibleRepository

    passages = PassageService(SqlBibleRepository(bible_db))
    cited = await passages.resolve("Jo 2:2", "vfl")
    wide = await passages.context(cited.range, cited.requested_translation, radius=2)
    assert wide.translation == "nvt" and wide.fallback_label == "NVT — VFL indisponível neste trecho"


async def test_every_translation_substitution_is_labeled(bible_db: AsyncSession) -> None:
    from app.application.bible.passages import PassageService
    from app.infrastructure.database.bible_repository import SqlBibleRepository

    passages = PassageService(SqlBibleRepository(bible_db))
    ara = await passages.resolve("Fp 1:1", "ara")
    assert ara.translation == "vfl" and ara.fallback_label == "VFL — ARA indisponível neste trecho"
    unknown = await passages.resolve("Fp 1:1", "xyz")
    assert unknown.translation == "vfl" and unknown.fallback_label == "VFL — tradução XYZ não encontrada"


async def test_rejects_foreign_host_header() -> None:
    import httpx

    from app.main import create_app

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        assert (await client.get("/api/v1/health")).status_code == 200
        assert (await client.get("/api/v1/health", headers={"Host": "evil.example"})).status_code == 400
