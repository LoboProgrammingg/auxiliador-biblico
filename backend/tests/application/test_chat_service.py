import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.events import ChatEvent
from app.application.chat.ports import AgentText
from app.application.chat.service import ChatService
from app.application.chat.tools import ToolExecutor
from app.application.memory.service import MemoryService
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.memory_repository import SqlMemoryRepository
from tests.application.test_tools import NoRerank
from tests.chat_fakes import FakeAgentRunner
from tests.fakes import FakeEmbedder


def make_service(session: AsyncSession, runner: FakeAgentRunner, **kwargs: Any) -> ChatService:
    repo = SqlBibleRepository(session)
    passages = PassageService(repo)
    executor = ToolExecutor(
        passages,
        SearchService(repo, passages, FakeEmbedder(), NoRerank()),
        repo,
        MemoryService(SqlMemoryRepository(session)),
        None,
    )
    return ChatService(SqlConversationRepository(session), passages, repo, executor, runner, web_serper=False, **kwargs)


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


async def test_first_message_carries_memory_so_agent_skips_listing(bible_db: AsyncSession) -> None:
    await MemoryService(SqlMemoryRepository(bible_db)).save("oracao", "pela mãe")
    runner = FakeAgentRunner(["Oi"], session_id="abc")
    svc = make_service(bible_db, runner)
    cid = await new_conversation(bible_db)
    await collect(svc, cid, "primeira")
    await collect(svc, cid, "segunda")
    first, second = runner.calls[0]["prompt"], runner.calls[1]["prompt"]
    assert first.startswith("primeira") and "[Memória da pessoa" in first and "pela mãe" in first
    assert "[Memória da pessoa" not in second


async def test_first_message_says_memory_is_empty(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Oi"])
    await collect(make_service(bible_db, runner), await new_conversation(bible_db), "oi")
    assert "[Memória da pessoa: nada guardado ainda]" in runner.calls[0]["prompt"]


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


async def test_timeline_marker_streams_event_and_persists(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Estrutura:\n", "[[linha:Sl 2|1-3=Começo;4-6=Fim]]", "\nPronto."])
    cid = await new_conversation(bible_db)
    events = await collect(make_service(bible_db, runner), cid, "estude Sl 2")
    timeline = next(e for e in events if e.name == "timeline")
    assert timeline.data["reference"] == "Sl 2" and len(timeline.data["sections"]) == 2
    messages = await SqlConversationRepository(bible_db).messages(cid)
    assert [s["type"] for s in messages[1].segments] == ["text", "timeline", "text"]


async def test_assistant_placeholder_is_generating_until_done(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner(["Oi ", "tudo bem"]))
    cid = await new_conversation(bible_db)
    repo = SqlConversationRepository(bible_db)
    statuses = []
    async for event in svc.send(cid, "oi"):
        if event.name == "text" and not statuses:
            statuses.append((await repo.messages(cid))[-1].status)
        if event.name == "done":
            final = (await repo.messages(cid))[-1]
            assert event.data["message_id"] == final.id
    assert statuses == ["gerando"] and final.status == "ok" and final.role == "assistant"


async def test_startup_marks_generating_as_interrupted(bible_db: AsyncSession) -> None:
    repo = SqlConversationRepository(bible_db)
    cid = await new_conversation(bible_db)
    await repo.start_assistant(cid)
    assert await repo.mark_interrupted() == 1
    assert (await repo.messages(cid))[-1].status == "interrompida"


async def test_agent_timeout_records_error_segment(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner(["a", "b", "c", "d"], delay=0.05), timeout_s=0.08)
    cid = await new_conversation(bible_db)
    events = await collect(svc, cid, "oi")
    assert any(e.name == "error" and e.data["code"] == "tempo_esgotado" for e in events)
    assert events[-1].name == "done"
    stored = (await SqlConversationRepository(bible_db).messages(cid))[-1]
    assert stored.status == "erro"
    error = next(s for s in stored.segments if s["type"] == "error")
    assert error["code"] == "tempo_esgotado" and error["message"]


async def test_agent_error_is_persisted_in_segments(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner([("done", True, "limite_claude")]))
    cid = await new_conversation(bible_db)
    await collect(svc, cid, "oi")
    stored = (await SqlConversationRepository(bible_db).messages(cid))[-1]
    assert stored.status == "erro" and [s["code"] for s in stored.segments if s["type"] == "error"] == ["limite_claude"]


async def test_runner_exception_is_recorded_not_left_generating(bible_db: AsyncSession) -> None:
    class Boom(FakeAgentRunner):
        async def run(self, prompt, session_id, tools, effort=None, model=None):  # type: ignore[no-untyped-def,override]
            yield AgentText("começo ")
            raise RuntimeError("falhou")

    cid = await new_conversation(bible_db)
    events = await collect(make_service(bible_db, Boom([])), cid, "oi")
    assert any(e.name == "error" for e in events) and events[-1].name == "done"
    assert (await SqlConversationRepository(bible_db).messages(cid))[-1].status == "erro"


async def test_locks_are_released_and_removed(bible_db: AsyncSession) -> None:
    from app.application.chat import service as service_module

    cid = await new_conversation(bible_db)
    await collect(make_service(bible_db, FakeAgentRunner(["oi"])), cid, "oi")
    assert cid not in service_module._LOCKS


async def test_crisis_card_without_jev(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Estou aqui com você."])
    events = await collect(make_service(bible_db, runner), await new_conversation(bible_db), "não quero mais viver")
    assert events[0].name == "crisis" and events[0].data["numero"] == "188"
    assert "risco_à_vida=alto" in runner.calls[0]["prompt"]


async def test_crisis_regex_overrides_low_jev_score(bible_db: AsyncSession) -> None:
    from tests.judge_fakes import FakeJudge

    judge = FakeJudge(nouls={"crise": 0.1}, choices={"momento": ("outro", 0.5)}, scores={"angustia": (1.0, 0.5)})
    runner = FakeAgentRunner(["Estou aqui."])
    events = await collect(make_judged(bible_db, runner, judge), await new_conversation(bible_db), "quero me matar")
    assert events[0].name == "crisis" and "risco_à_vida=alto" in runner.calls[0]["prompt"]


async def test_no_crisis_for_everyday_text_without_jev(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Oi"])
    events = await collect(make_service(bible_db, runner), await new_conversation(bible_db), "morrendo de rir")
    assert "crisis" not in [e.name for e in events] and "Triagem" not in runner.calls[0]["prompt"]


async def test_chapter_study_requests_study_effort(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Estudo."])
    svc = make_service(bible_db, runner, study_effort="high")
    await collect(svc, await new_conversation(bible_db), "Interprete João 1")
    await collect(svc, await new_conversation(bible_db), "Estou ansioso")
    assert [c["effort"] for c in runner.calls] == ["high", None]


async def test_opinion_request_adds_opinion_block(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Minha leitura."])
    svc = make_service(bible_db, runner, study_effort="high")
    await collect(svc, await new_conversation(bible_db), "Na sua opinião, o que significa ser sal da terra?")
    await collect(svc, await new_conversation(bible_db), "O que a Bíblia diz sobre ser sal da terra?")
    assert "[Pedido de opinião" in runner.calls[0]["prompt"] and runner.calls[0]["effort"] == "high"
    assert "[Pedido de opinião" not in runner.calls[1]["prompt"]


async def test_chosen_model_effort_and_brief_reach_the_agent(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Curto."])
    svc = make_service(bible_db, runner, study_effort="high")
    cid = await new_conversation(bible_db)
    [e async for e in svc.send(cid, "Interprete João 1", model="claude-opus-5-5", effort="xhigh", brief=True)]
    call = runner.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["effort"] == "xhigh"
    assert "[Pedido de resposta breve" in call["prompt"]


async def test_without_choice_keeps_default_model_and_automatic_effort(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Estudo."])
    await collect(
        make_service(bible_db, runner, study_effort="high"), await new_conversation(bible_db), "Interprete João 1"
    )
    call = runner.calls[0]
    assert call["model"] is None and call["effort"] == "high" and "[Pedido de resposta breve" not in call["prompt"]


async def test_wrong_fact_becomes_issue_with_correction(bible_db: AsyncSession) -> None:
    from sqlalchemy import text as sql

    for pid, name in (("ruth", "Rute"), ("obed", "Obede"), ("jesse", "Jessé"), ("david", "Davi")):
        await bible_db.execute(
            sql("INSERT INTO people (id, name_en, name_pt) VALUES (:i, :n, :n)"), {"i": pid, "n": name}
        )
    for child, parent in (("obed", "ruth"), ("jesse", "obed"), ("david", "jesse")):
        await bible_db.execute(
            sql("INSERT INTO person_relations (person_id, kind, other_id) VALUES (:c, 'pai_mae', :p)"),
            {"c": child, "p": parent},
        )
    runner = FakeAgentRunner(["Rute foi avó do rei Davi. Que história linda."])
    cid = await new_conversation(bible_db)
    events = await collect(make_service(bible_db, runner), cid, "Quem era Rute?")
    items = next(e for e in events if e.name == "issues").data["items"]
    assert [(i["kind"], i["correction"]) for i in items] == [
        ("fato_nao_confere", "Pela base de famílias (STEPBible): Rute → Obede → Jessé → Davi.")
    ]
    stored = (await SqlConversationRepository(bible_db).messages(cid))[-1]
    assert any(s["type"] == "issue" and s.get("correction") for s in stored.segments)


async def test_each_answer_gets_its_own_web_search_quota(bible_db: AsyncSession) -> None:
    from tests.application.test_tools import NumberedWeb, web_executor

    web = NumberedWeb()
    executor = web_executor(bible_db, web)
    script = [("tool", "pesquisar_web_serper", {"consulta": "q"})] * 8 + ["ok"]
    repo = SqlBibleRepository(bible_db)
    svc = ChatService(
        SqlConversationRepository(bible_db), PassageService(repo), repo, executor, FakeAgentRunner(script), True
    )
    cid = await new_conversation(bible_db)
    await collect(svc, cid, "Interprete Fp 2")
    await collect(svc, cid, "E o versículo 3?")
    assert web.calls == 16


async def test_brief_request_adds_brief_block(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Curto."])
    svc = make_service(bible_db, runner, study_effort="high")
    await collect(svc, await new_conversation(bible_db), "Me envie um breve resumo de João 1")
    await collect(svc, await new_conversation(bible_db), "Jesus volta em breve?")
    assert "[Pedido de resposta breve" in runner.calls[0]["prompt"] and runner.calls[0]["effort"] is None
    assert "[Pedido de resposta breve" not in runner.calls[1]["prompt"]


async def test_token_usage_is_reported_with_running_average(bible_db: AsyncSession) -> None:
    from app.application.chat.ports import TokenUsage

    cid = await new_conversation(bible_db)
    first = FakeAgentRunner(["Um."] + [("done", False, None, TokenUsage(total=1000, output=100))])
    await collect(make_service(bible_db, first), cid, "primeira")
    second = FakeAgentRunner(["Dois."] + [("done", False, None, TokenUsage(total=3000, output=300, cached=2500))])
    events = await collect(make_service(bible_db, second), cid, "segunda")
    usage = next(e for e in events if e.name == "usage").data
    assert usage == {"total": 3000, "output": 300, "cached": 2500, "average": 2000, "questions": 2}
    assert [e.name for e in events][-2:] == ["usage", "done"]
    stored = (await SqlConversationRepository(bible_db).messages(cid))[-1].segments
    assert stored[-1] == {"type": "usage", **usage}


async def test_no_usage_event_without_usage(bible_db: AsyncSession) -> None:
    events = await collect(make_service(bible_db, FakeAgentRunner(["Oi"])), await new_conversation(bible_db), "x")
    assert "usage" not in [e.name for e in events]
