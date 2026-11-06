import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Callable

from app.application.chat.events import ChatEvent, error_event

logger = logging.getLogger(__name__)
RunTurn = Callable[[], AsyncIterator[ChatEvent]]


class ChatJob:
    """Uma resposta em andamento: roda sem depender de quem está assistindo."""

    def __init__(self, conversation_id: uuid.UUID) -> None:
        self.conversation_id = conversation_id
        self.events: list[ChatEvent] = []
        self.done = False
        self._changed = asyncio.Condition()
        self._task: asyncio.Task[None] | None = None

    async def _publish(self, event: ChatEvent | None) -> None:
        async with self._changed:
            if event is None:
                self.done = True
            else:
                self.events.append(event)
            self._changed.notify_all()

    async def _run(self, run: RunTurn) -> None:
        try:
            async for event in run():
                await self._publish(event)
        except Exception:
            logger.exception("falha na tarefa da conversa")
            await self._publish(error_event("agente_erro"))
        finally:
            await self._publish(None)

    async def subscribe(self, after: int = 0) -> AsyncIterator[ChatEvent]:
        index = after
        while True:
            async with self._changed:
                while not self.done and len(self.events) <= index:
                    await self._changed.wait()
                fresh, finished = self.events[index:], self.done
            for event in fresh:
                yield event
            index += len(fresh)
            if finished and index >= len(self.events):
                return

    async def wait(self) -> None:
        if self._task is not None:
            await asyncio.shield(self._task)


class ChatJobs:
    """Registro das respostas em andamento, uma por conversa."""

    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, ChatJob] = {}

    def get(self, conversation_id: uuid.UUID) -> ChatJob | None:
        return self._jobs.get(conversation_id)

    def start(self, conversation_id: uuid.UUID, run: RunTurn) -> ChatJob | None:
        if conversation_id in self._jobs:
            return None
        job = ChatJob(conversation_id)
        self._jobs[conversation_id] = job
        job._task = asyncio.create_task(job._run(run))
        job._task.add_done_callback(lambda _t: self._jobs.pop(conversation_id, None))
        return job
