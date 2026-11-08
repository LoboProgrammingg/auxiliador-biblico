import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from app.application.bible.passages import PassageService
from app.application.chat.effort import (
    asks_opinion,
    effort_for,
    wants_brief,
    wants_complex,
    wants_plan,
    wants_thinkers,
)
from app.application.chat.events import ChatEvent, error_event, passage_payload
from app.application.chat.ports import AgentDone, AgentRunner, AgentText, AgentTools, AgentToolStart, TokenUsage
from app.application.chat.skill_text import skill_body
from app.application.chat.tools import STATUS, ToolExecutor, ToolOutcome, allowed_tool_names, build_mcp_server
from app.application.judgments.crisis import detect_crisis
from app.application.judgments.service import CRISIS_THRESHOLD, JudgmentService, sentence_after, triage_block
from app.application.verification.facts import check_facts
from app.application.verification.final_check import final_check
from app.application.verification.markers import (
    ChiasmOut,
    InvalidRefOut,
    MapOut,
    MarkerStreamProcessor,
    RouteOut,
    StreamOut,
    TextOut,
    ThinkerOut,
    ThreadOut,
    TimelineOut,
    VerseOut,
)
from app.domain.bible.repositories import BibleRepository
from app.domain.conversation.repositories import ConversationRepository

logger = logging.getLogger(__name__)
MAX_TEXT = 8000
_LOCKS: dict[uuid.UUID, asyncio.Lock] = {}
MAX_FIDELITY_PAIRS = 6
CVV = {"numero": "188", "url": "https://cvv.org.br"}
CHECKPOINT_SECONDS = 3.0
OPINION_BLOCK = (
    "[Pedido de opinião: a pessoa quer a SUA opinião e a SUA interpretação; siga a seção Quando pedirem sua opinião.]"
)
BRIEF_BLOCK = (
    "[Pedido de resposta breve: siga a seção Quando pedirem resposta breve; só o essencial, sem pesquisa na web.]"
)
PLAN_BLOCK = (
    "[Pedido de plano de estudo: siga a seção Plano de estudo; monte o plano, não desenvolva os tópicos ainda.]"
)
VIDEO_BLOCK = (
    "[Pedido de vídeo viral para o canal Pedras Clamam (botão Vídeo TikTok): siga à risca as instruções abaixo e "
    "entregue o pacote completo no Formato de entrega.]\n\n" + skill_body("video-viral")
)
VIDEO_EFFORT = "high"
COMPLEX_BLOCK = (
    "[Pedido de estudo complexo (botão Complexo ou mensagem começando com Complexo): siga à risca as instruções "
    "abaixo; destrinche a pergunta inteira e faça todas as conexões, sem deixar nada para trás. Neste pedido valem "
    "as rodadas e as pesquisas descritas aqui, não os limites normais.]\n\n" + skill_body("estudo-complexo")
)
THINKERS_BLOCK = (
    "[Pensadores: este tema costuma envolver filósofos e objeções céticas. Carregue a skill pensadores; toda ideia "
    "atribuída a um pensador vai no cartão [[pensador:...]], nunca em tópicos ou parágrafos do texto.]"
)
COMPLEX_EFFORT = "xhigh"
BRIEF_COMBINED_BLOCK = (
    "[Resposta breve combinada com outro modo: faça a pesquisa e as etapas dos outros modos normalmente; só o texto "
    "final sai no formato mais enxuto possível.]"
)
_EFFORT_RANK = {"medium": 0, "high": 1, "xhigh": 2}


def _with_modes(
    prompt: str, effort: str | None, *, complex: bool, plan: bool, video: bool, brief: bool
) -> tuple[str, str | None]:
    """Os botões se somam: cada modo ligado põe o seu bloco; o esforço padrão é o maior entre os modos."""
    blocks = [b for on, b in ((complex, COMPLEX_BLOCK), (plan, PLAN_BLOCK), (video, VIDEO_BLOCK)) if on]
    if brief:
        blocks.append(BRIEF_COMBINED_BLOCK if blocks else BRIEF_BLOCK)
    if len(blocks) > 1:
        names = [
            n
            for on, n in (
                (complex, "estudo complexo"),
                (plan, "plano de estudo"),
                (video, "vídeo viral"),
                (brief, "resposta breve"),
            )
            if on
        ]
        blocks.append(f"[Modos combinados: {' + '.join(names)}. Cumpra todos juntos, sem descartar nenhum.]")
    defaults = [e for on, e in ((complex, COMPLEX_EFFORT), (video, VIDEO_EFFORT)) if on]
    if effort is None and defaults:
        effort = max(defaults, key=_EFFORT_RANK.__getitem__)
    return "\n\n".join([prompt, *blocks]), effort


DEFAULT_TIMEOUT_S = 300.0
DEFAULT_LONG_TIMEOUT_S = 1200.0
NATIVE_STATUS = {"WebSearch": "Pesquisando na web…"}


def _status_for(tool_name: str) -> str:
    short = tool_name.removeprefix("mcp__biblia__")
    if short == "ler_passagem":
        return "Lendo a Bíblia…"
    return STATUS.get(short) or NATIVE_STATUS.get(tool_name, "Pensando…")


async def _close(agent: AsyncIterator[Any]) -> None:
    close = getattr(agent, "aclose", None)
    if close is not None:
        try:
            await close()
        except Exception:
            logger.warning("falha ao encerrar o agente", exc_info=True)


class _Turn:
    """Acumula segmentos exibidos e a prosa para a checagem final."""

    def __init__(self) -> None:
        self.segments: list[dict[str, Any]] = []
        self.prose: list[str] = []

    def error(self, code: str) -> ChatEvent:
        event = error_event(code)
        self.segments.append({"type": "error", **event.data})
        return event

    def add(self, out: StreamOut) -> ChatEvent | None:
        payload: dict[str, Any]
        if isinstance(out, TextOut):
            if not out.text:
                return None
            self.prose.append(out.text)
            if self.segments and self.segments[-1]["type"] == "text":
                self.segments[-1]["text"] += out.text
            else:
                self.segments.append({"type": "text", "text": out.text})
            return ChatEvent("text", {"text": out.text})
        if isinstance(out, VerseOut):
            payload = {"marker": out.marker, "passage": passage_payload(out.passage)}
            self.segments.append({"type": "verse", **payload})
            return ChatEvent("verse", payload)
        if isinstance(out, TimelineOut):
            payload = {
                "marker": out.marker,
                "reference": out.reference,
                "book": out.book,
                "sections": out.sections,
            }
            self.segments.append({"type": "timeline", **payload})
            return ChatEvent("timeline", payload)
        if isinstance(out, MapOut):
            payload = {"marker": out.marker, "reference": out.reference, "places": out.places}
            self.segments.append({"type": "map", **payload})
            return ChatEvent("map", payload)
        if isinstance(out, ChiasmOut):
            payload = {"marker": out.marker, "reference": out.reference, "book": out.book, "parts": out.parts}
            self.segments.append({"type": "chiasm", **payload})
            return ChatEvent("chiasm", payload)
        if isinstance(out, RouteOut):
            payload = {"marker": out.marker, "reference": out.reference, "legs": out.legs}
            self.segments.append({"type": "route", **payload})
            return ChatEvent("route", payload)
        if isinstance(out, ThreadOut):
            payload = {"marker": out.marker, "reference": out.reference, "links": out.links, "books": out.books}
            self.segments.append({"type": "thread", **payload})
            return ChatEvent("thread", payload)
        if isinstance(out, ThinkerOut):
            payload = {
                "marker": out.marker,
                "name": out.name,
                "period": out.period,
                "work": out.work,
                "kind": out.kind,
                "text": out.text,
                "objection": out.objection,
            }
            self.segments.append({"type": "thinker", **payload})
            return ChatEvent("thinker", payload)
        assert isinstance(out, InvalidRefOut)
        self.segments.append({"type": "invalid_reference", "marker": out.marker})
        return ChatEvent("invalid_reference", {"marker": out.marker})


class ChatService:
    def __init__(
        self,
        conversations: ConversationRepository,
        passages: PassageService,
        repo: BibleRepository,
        executor: ToolExecutor,
        runner: AgentRunner,
        web_serper: bool,
        judgments: JudgmentService | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        long_timeout_s: float = DEFAULT_LONG_TIMEOUT_S,
        study_effort: str | None = None,
    ) -> None:
        self._conversations, self._passages, self._repo = conversations, passages, repo
        self._executor, self._runner, self._web_serper = executor, runner, web_serper
        self._judgments = judgments or JudgmentService(None)
        self._timeout_s, self._study_effort = timeout_s, study_effort
        self._long_timeout_s = long_timeout_s

    async def _review(self, turn: "_Turn", user_text: str) -> list[dict[str, Any]]:
        """Checagens após a resposta: texto (determinístico), teologia e fidelidade (Jev)."""
        issues = await final_check("".join(turn.prose), self._passages, self._repo, user_text)
        items: list[dict[str, Any]] = [{"kind": i.kind, "excerpt": i.excerpt} for i in issues]
        items += await self._judgments.guard_issues("".join(turn.prose))
        items += await check_facts("".join(turn.prose), self._repo, self._judgments)
        pairs: list[tuple[str, str, str]] = []
        for current, following in zip(turn.segments, turn.segments[1:], strict=False):
            if current["type"] == "verse" and following["type"] == "text":
                verse_text = " ".join(v["text"] for v in current["passage"]["verses"])
                pairs.append((current["marker"], verse_text, sentence_after(following["text"])))
        for issue in await self._judgments.fidelity(pairs[:MAX_FIDELITY_PAIRS]):
            items.append({"kind": "interpretacao_contradiz", "excerpt": issue.claim, "marker": issue.marker})
        return items

    async def _usage(self, usage: TokenUsage) -> dict[str, int]:
        """Tokens desta resposta e a média por pergunta, contando com ela."""
        count, total = await self._conversations.token_usage_totals()
        questions = count + 1
        average = round((total + usage.total) / questions)
        return {
            "total": usage.total,
            "output": usage.output,
            "cached": usage.cached,
            "average": average,
            "questions": questions,
        }

    async def _memory_block(self) -> str:
        """A memória vai no prompt da primeira mensagem para o agente não gastar uma rodada só para listá-la."""
        listed = await self._executor.run("memoria_listar", {})
        if listed.is_error or listed.content == "[]":
            return "[Memória da pessoa: nada guardado ainda]"
        return f"[Memória da pessoa (já carregada; não chame memoria_listar): {listed.content}]"

    def _tools(self, pending: list[ChatEvent]) -> AgentTools:
        async def on_outcome(outcome: ToolOutcome) -> None:
            if outcome.saved_memory:
                pending.append(ChatEvent("memory_saved", {"topic": outcome.saved_memory}))

        async def invoke(name: str, args: dict[str, Any]) -> ToolOutcome:
            outcome = await self._executor.run(name, args)
            await on_outcome(outcome)
            return outcome

        server = build_mcp_server(self._executor, on_outcome, self._web_serper)
        return AgentTools(server, allowed_tool_names(self._web_serper), invoke)

    async def send(
        self,
        conversation_id: uuid.UUID,
        user_text: str,
        model: str | None = None,
        effort: str | None = None,
        brief: bool = False,
        plan: bool = False,
        video: bool = False,
        complex: bool = False,
    ) -> AsyncIterator[ChatEvent]:
        """Escolhas da tela vencem o padrão: brief (resposta curta), plan (plano de estudo), video (vídeo viral) e
        complex (estudo exaustivo)."""
        text = user_text.strip()
        if not text or len(user_text) > MAX_TEXT:
            yield error_event("texto_invalido")
            return
        lock = _LOCKS.setdefault(conversation_id, asyncio.Lock())
        if lock.locked():
            yield error_event("ocupado")
            return
        try:
            async with lock:
                async for event in self._send_locked(conversation_id, text, model, effort, brief, plan, video, complex):
                    yield event
        finally:
            if not lock.locked():
                _LOCKS.pop(conversation_id, None)

    async def _send_locked(
        self,
        conversation_id: uuid.UUID,
        text: str,
        model: str | None,
        effort: str | None,
        brief: bool,
        plan: bool,
        video: bool = False,
        complex: bool = False,
    ) -> AsyncIterator[ChatEvent]:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            yield error_event("conversa_inexistente")
            return
        await self._conversations.add_message(conversation_id, "user", text, None)
        await self._conversations.set_title_if_default(conversation_id, text)
        message_id = await self._conversations.start_assistant(conversation_id)
        self._executor.start_turn()
        turn, pending = _Turn(), list[ChatEvent]()
        saved_at = time.monotonic()
        prompt = text
        triage = await self._judgments.triage(text)
        at_risk = detect_crisis(text) or (triage is not None and triage.crisis >= CRISIS_THRESHOLD)
        if at_risk:
            turn.segments.append({"type": "crisis", **CVV})
            yield ChatEvent("crisis", dict(CVV))
        if triage is not None:
            yield ChatEvent("triage", {"moment": triage.moment, "distress": round(triage.distress, 2)})
            prompt = f"{text}\n\n{triage_block(replace(triage, crisis=1.0) if at_risk else triage)}"
        elif at_risk:
            prompt = f"{text}\n\n[Triagem automática: risco_à_vida=alto]"
        if conversation.agent_session_id is None:
            prompt = f"{prompt}\n\n{await self._memory_block()}"
        if asks_opinion(text):
            prompt = f"{prompt}\n\n{OPINION_BLOCK}"
        if wants_thinkers(text):
            prompt = f"{prompt}\n\n{THINKERS_BLOCK}"
        complex = complex or wants_complex(text)
        prompt, effort = _with_modes(
            prompt,
            effort,
            complex=complex,
            plan=plan or wants_plan(text),
            video=video,
            brief=brief or wants_brief(text),
        )
        processor = MarkerStreamProcessor(self._passages)
        done: AgentDone | None = None
        deadline = time.monotonic() + (self._long_timeout_s if video or complex else self._timeout_s)
        effort = effort or effort_for(text, self._study_effort)
        agent = aiter(self._runner.run(prompt, conversation.agent_session_id, self._tools(pending), effort, model))
        try:
            while True:
                try:
                    event = await asyncio.wait_for(anext(agent), max(deadline - time.monotonic(), 0))
                except StopAsyncIteration:
                    break
                if isinstance(event, AgentText):
                    outs = await processor.feed(event.text)
                    for out in outs:
                        if (chat_event := turn.add(out)) is not None:
                            yield chat_event
                    card = any(not isinstance(out, TextOut) for out in outs)
                    if card or time.monotonic() - saved_at >= CHECKPOINT_SECONDS:
                        await self._conversations.update_message(message_id, turn.segments, "gerando")
                        saved_at = time.monotonic()
                elif isinstance(event, AgentToolStart):
                    yield ChatEvent("status", {"label": _status_for(event.name)})
                elif isinstance(event, AgentDone):
                    done = event
                while pending:
                    yield pending.pop(0)
        except TimeoutError:
            yield turn.error("tempo_esgotado")
        except Exception:
            logger.exception("falha no agente")
            yield turn.error("agente_erro")
        finally:
            await _close(agent)
        for out in await processor.flush():
            if (chat_event := turn.add(out)) is not None:
                yield chat_event
        if done is not None and done.is_error:
            yield turn.error(done.error or "agente_erro")
        items = await self._review(turn, text)
        turn.segments.extend({"type": "issue", **item} for item in items)
        yield ChatEvent("issues", {"items": items})
        if done is not None and done.usage is not None:
            usage = await self._usage(done.usage)
            turn.segments.append({"type": "usage", **usage})
            yield ChatEvent("usage", usage)
        if done is not None and done.session_id and done.session_id != conversation.agent_session_id:
            await self._conversations.set_session(conversation_id, done.session_id)
        status = "erro" if any(seg["type"] == "error" for seg in turn.segments) else "ok"
        await self._conversations.update_message(message_id, turn.segments, status)
        yield ChatEvent("done", {"message_id": message_id})
