import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from app.application.bible.passages import PassageService
from app.application.chat.effort import asks_opinion, effort_for
from app.application.chat.events import ChatEvent, error_event, passage_payload
from app.application.chat.ports import AgentDone, AgentRunner, AgentText, AgentTools, AgentToolStart
from app.application.chat.tools import STATUS, ToolExecutor, ToolOutcome, allowed_tool_names, build_mcp_server
from app.application.judgments.crisis import detect_crisis
from app.application.judgments.service import CRISIS_THRESHOLD, JudgmentService, sentence_after, triage_block
from app.application.verification.final_check import final_check
from app.application.verification.markers import (
    ChiasmOut,
    InvalidRefOut,
    MapOut,
    MarkerStreamProcessor,
    StreamOut,
    TextOut,
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
DEFAULT_TIMEOUT_S = 300.0
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
            payload: dict[str, Any] = {
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
        study_effort: str | None = None,
    ) -> None:
        self._conversations, self._passages, self._repo = conversations, passages, repo
        self._executor, self._runner, self._web_serper = executor, runner, web_serper
        self._judgments = judgments or JudgmentService(None)
        self._timeout_s, self._study_effort = timeout_s, study_effort

    async def _review(self, turn: "_Turn", user_text: str) -> list[dict[str, str]]:
        """Checagens após a resposta: texto (determinístico), teologia e fidelidade (Jev)."""
        issues = await final_check("".join(turn.prose), self._passages, self._repo, user_text)
        items = [{"kind": i.kind, "excerpt": i.excerpt} for i in issues]
        items += await self._judgments.guard_issues("".join(turn.prose))
        pairs: list[tuple[str, str, str]] = []
        for current, following in zip(turn.segments, turn.segments[1:], strict=False):
            if current["type"] == "verse" and following["type"] == "text":
                verse_text = " ".join(v["text"] for v in current["passage"]["verses"])
                pairs.append((current["marker"], verse_text, sentence_after(following["text"])))
        for issue in await self._judgments.fidelity(pairs[:MAX_FIDELITY_PAIRS]):
            items.append({"kind": "interpretacao_contradiz", "excerpt": issue.claim, "marker": issue.marker})
        return items

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

    async def send(self, conversation_id: uuid.UUID, user_text: str) -> AsyncIterator[ChatEvent]:
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
                async for event in self._send_locked(conversation_id, text):
                    yield event
        finally:
            if not lock.locked():
                _LOCKS.pop(conversation_id, None)

    async def _send_locked(self, conversation_id: uuid.UUID, text: str) -> AsyncIterator[ChatEvent]:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            yield error_event("conversa_inexistente")
            return
        await self._conversations.add_message(conversation_id, "user", text, None)
        await self._conversations.set_title_if_default(conversation_id, text)
        message_id = await self._conversations.start_assistant(conversation_id)
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
        if asks_opinion(text):
            prompt = f"{prompt}\n\n{OPINION_BLOCK}"
        processor = MarkerStreamProcessor(self._passages)
        done: AgentDone | None = None
        deadline = time.monotonic() + self._timeout_s
        effort = effort_for(text, self._study_effort)
        agent = aiter(self._runner.run(prompt, conversation.agent_session_id, self._tools(pending), effort))
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
        if done is not None and done.session_id and done.session_id != conversation.agent_session_id:
            await self._conversations.set_session(conversation_id, done.session_id)
        status = "erro" if any(seg["type"] == "error" for seg in turn.segments) else "ok"
        await self._conversations.update_message(message_id, turn.segments, status)
        yield ChatEvent("done", {"message_id": message_id})
