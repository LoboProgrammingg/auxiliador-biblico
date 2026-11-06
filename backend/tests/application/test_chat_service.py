import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.events import ChatEvent
from app.application.chat.service import ChatService
from app.application.chat.tools import ToolExecutor
from app.application.memory.service import MemoryService
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.memory_repository import SqlMemoryRepository
from tests.application.test_tools import NoRerank
from tests.chat_fakes import FakeAgentRunner
from tests.fakes import FakeEmbedder


def make_service(session: AsyncSession, runner: FakeAgentRunner) -> ChatService:
    repo = SqlBibleRepository(session)
    passages = PassageService(repo)
    executor = ToolExecutor(
        passages,
        SearchService(repo, passages, FakeEmbedder(), NoRerank()),
        repo,
        MemoryService(SqlMemoryRepository(session)),
        None,
    )
    return ChatService(SqlConversationRepository(session), passages, repo, executor, runner, web_serper=False)


async def collect(svc: ChatService, cid: uuid.UUID, text: str) -> list[ChatEvent]:
    return [e async for e in svc.send(cid, text)]


async def new_conversation(session: AsyncSession) -> uuid.UUID:
    return await SqlConversationRepository(session).create()


async def test_text_with_marker_streams_card_and_persists_segments(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Leia ", "[[Fp 2", ":3|VFL]]", " e ore."])
    svc = make_service(bible_db, runner)
    cid = await new_conversation(bible_db)
    events = await collect(svc, cid, "Estou ansioso")
    names = [e.name for e in events]
    assert names[:2] == ["text", "verse"] and names[-2:] == ["issues", "done"]
    verse = next(e for e in events if e.name == "verse")
    assert verse.data["passage"]["reference"] == "Fp 2:3" and verse.data["passage"]["verses"][0]["text"]
    messages = await SqlConversationRepository(bible_db).messages(cid)
    assert [m.role for m in messages] == ["user", "assistant"]
    assert [s["type"] for s in messages[1].segments] == ["text", "verse", "text"]


async def test_first_message_stores_session_and_next_resumes(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Oi"], session_id="abc")
    svc = make_service(bible_db, runner)
    cid = await new_conversation(bible_db)
    await collect(svc, cid, "primeira")
    await collect(svc, cid, "segunda")
    assert [c["session_id"] for c in runner.calls] == [None, "abc"]


async def test_tool_start_becomes_status_and_memory_event(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner([("tool", "memoria_salvar", {"topico": "oracao", "conteudo": "pela mãe"}), "Anotei."])
    events = await collect(make_service(bible_db, runner), await new_conversation(bible_db), "ore pela minha mãe")
    names = [e.name for e in events]
    assert "status" in names and "memory_saved" in names
    assert next(e for e in events if e.name == "memory_saved").data == {"topic": "oracao"}
    assert next(e for e in events if e.name == "status").data["label"] == "Guardando na memória…"


async def test_invalid_marker_and_prose_issues(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Veja [[Jo 1:99]] e também João 1:98."])
    events = await collect(make_service(bible_db, runner), await new_conversation(bible_db), "x")
    assert any(e.name == "invalid_reference" for e in events)
    issues = next(e for e in events if e.name == "issues").data["items"]
    assert [i["kind"] for i in issues] == ["referencia_inexistente"]


async def test_agent_error_emits_error_event(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner([("done", True, "claude_code_indisponivel")])
    events = await collect(make_service(bible_db, runner), await new_conversation(bible_db), "x")
    error = next(e for e in events if e.name == "error")
    assert error.data["code"] == "claude_code_indisponivel" and "Claude Code" in error.data["message"]


async def test_unknown_conversation(bible_db: AsyncSession) -> None:
    events = await collect(make_service(bible_db, FakeAgentRunner(["x"])), uuid.uuid4(), "oi")
    assert [e.name for e in events] == ["error"] and events[0].data["code"] == "conversa_inexistente"


async def test_concurrent_send_same_conversation_rejected(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["a", "b", "c"], delay=0.05)
    svc = make_service(bible_db, runner)
    cid = await new_conversation(bible_db)
    first = asyncio.create_task(collect(svc, cid, "um"))
    await asyncio.sleep(0.02)
    second = await collect(svc, cid, "dois")
    await first
    assert [e.name for e in second] == ["error"] and second[0].data["code"] == "ocupado"


@pytest.mark.parametrize("text", ["", "   ", "x" * 8001])
async def test_text_validation(bible_db: AsyncSession, text: str) -> None:
    events = await collect(make_service(bible_db, FakeAgentRunner(["x"])), await new_conversation(bible_db), text)
    assert events[0].name == "error" and events[0].data["code"] == "texto_invalido"


def make_judged(session: AsyncSession, runner: FakeAgentRunner, judge) -> ChatService:  # type: ignore[no-untyped-def]
    from app.application.judgments.service import JudgmentService

    repo = SqlBibleRepository(session)
    passages = PassageService(repo)
    judgments = JudgmentService(judge)
    memory = MemoryService(SqlMemoryRepository(session), judgments.contains_sensitive_data)
    executor = ToolExecutor(passages, SearchService(repo, passages, FakeEmbedder(), NoRerank()), repo, memory, None)
    return ChatService(
        SqlConversationRepository(session), passages, repo, executor, runner, web_serper=False, judgments=judgments
    )


async def test_crisis_emits_event_before_agent_and_triage_block(bible_db: AsyncSession) -> None:
    from tests.judge_fakes import FakeJudge

    judge = FakeJudge(
        nouls={"crise": 0.9}, choices={"momento": ("pecado_arrependimento", 0.8)}, scores={"angustia": (2.9, 0.8)}
    )
    runner = FakeAgentRunner(["Estou aqui com você."])
    events = await collect(make_judged(bible_db, runner, judge), await new_conversation(bible_db), "quero sumir")
    names = [e.name for e in events]
    assert names[:2] == ["crisis", "triage"] and names.index("crisis") < names.index("text")
    assert events[0].data == {"numero": "188", "url": "https://cvv.org.br"}
    assert (
        "[Triagem automática: momento=pecado_arrependimento; angústia=2.9/3; risco_à_vida=alto]"
        in runner.calls[0]["prompt"]
    )


async def test_guard_and_fidelity_become_issues(bible_db: AsyncSession) -> None:
    from tests.judge_fakes import FakeJudge

    judge = FakeJudge(nouls={"prosperidade": 0.95}, choices={"relacao": ("contradiz", 0.95)})
    runner = FakeAgentRunner(
        ["Veja:\n", "[[Fp 2:3]]", "\nEste versículo promete que Deus vai pagar todas as suas dívidas."]
    )
    events = await collect(make_judged(bible_db, runner, judge), await new_conversation(bible_db), "x")
    kinds = [i["kind"] for i in next(e for e in events if e.name == "issues").data["items"]]
    assert "teologia_prosperidade" in kinds and "interpretacao_contradiz" in kinds


async def test_memory_rejects_sensitive_data(bible_db: AsyncSession) -> None:
    from tests.judge_fakes import FakeJudge

    runner = FakeAgentRunner([("tool", "memoria_salvar", {"topico": "dados", "conteudo": "CPF 123.456.789-09"})])
    events = await collect(make_judged(bible_db, runner, FakeJudge()), await new_conversation(bible_db), "x")
    assert not any(e.name == "memory_saved" for e in events)
    assert await MemoryService(SqlMemoryRepository(bible_db)).list_all() == []
