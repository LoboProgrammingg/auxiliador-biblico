import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from app.application.chat.events import ERROR_MESSAGES
from app.application.chat.service import ChatService
from app.domain.conversation.repositories import ConversationRepository

DAILY_PROMPT = """✨ Uma palavra pra mim — palavra de hoje ({day}).
Escolha UMA passagem que conforte o coração de verdade para o momento que eu vivo (consulte a memória antes).
Responda PRIMEIRO com a palavra completa, neste formato: o marcador da passagem sozinho numa linha \
(ex.: [[Sl 46:1]]); depois uma reflexão curta e pessoal (no máximo 6 frases) dizendo por que esta palavra é \
para hoje; termine com uma oração curta.
Não anote a palavra do dia na memória: o sistema já guarda o histórico.
Não repita nenhuma destas passagens dos últimos dias: {recent}."""
ATTEMPTS = 2
_LOCK = asyncio.Lock()


class DailyWordError(Exception):
    pass


class DailyWordRepository(Protocol):
    async def get(self, day: date) -> tuple[uuid.UUID, str | None] | None: ...
    async def save(self, day: date, conversation_id: uuid.UUID, reference: str | None) -> None: ...
    async def recent_references(self, day: date, days: int = 90) -> list[str]: ...


@dataclass(frozen=True)
class DailyWord:
    day: date
    reference: str | None
    segments: list[dict[str, Any]]


class DailyWordService:
    """Uma palavra por dia: gerada no primeiro pedido do dia e repetida nos demais."""

    def __init__(
        self,
        conversations: ConversationRepository,
        daily: DailyWordRepository,
        chat: ChatService,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._conversations, self._daily, self._chat, self._today = conversations, daily, chat, today

    async def _stored(self, conversation_id: uuid.UUID, day: date, reference: str | None) -> DailyWord:
        messages = await self._conversations.messages(conversation_id)
        segments = next((m.segments for m in reversed(messages) if m.role == "assistant" and m.segments), [])
        return DailyWord(day, reference, segments or [])

    async def _generate(self, prompt: str) -> tuple[uuid.UUID, str | None]:
        conversation_id = await self._conversations.create(kind="palavra")
        reference: str | None = None
        async for event in self._chat.send(conversation_id, prompt):
            if event.name == "verse" and reference is None:
                reference = str(event.data["passage"]["reference"])  # type: ignore[index]
            elif event.name == "error":
                await self._conversations.delete(conversation_id)
                code = str(event.data.get("code", "agente_erro"))
                raise DailyWordError(ERROR_MESSAGES.get(code, ERROR_MESSAGES["agente_erro"]))
        return conversation_id, reference

    async def today(self) -> DailyWord:
        day = self._today()
        async with _LOCK:
            existing = await self._daily.get(day)
            if existing is not None:
                return await self._stored(existing[0], day, existing[1])
            recent = await self._daily.recent_references(day)
            prompt = DAILY_PROMPT.format(day=day.strftime("%d/%m/%Y"), recent=", ".join(recent) or "nenhuma")
            for _ in range(ATTEMPTS):
                conversation_id, reference = await self._generate(prompt)
                if reference is not None:
                    break
                await self._conversations.delete(conversation_id)
            if reference is None:
                raise DailyWordError("Não consegui preparar a palavra de hoje. Tente de novo em instantes.")
            await self._daily.save(day, conversation_id, reference)
            return await self._stored(conversation_id, day, reference)
