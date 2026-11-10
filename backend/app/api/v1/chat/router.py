import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_embedder, get_reranker
from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.events import ChatEvent, error_event
from app.application.chat.jobs import ChatJob, ChatJobs
from app.application.chat.ports import AgentRunner, Embedder, Reranker
from app.application.chat.service import ChatService
from app.application.chat.tools import ToolExecutor
from app.application.judgments.service import JudgmentService
from app.application.memory.service import MemoryService
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.memory_repository import SqlMemoryRepository
from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner
from app.infrastructure.external.serper.client import SerperClient
from app.infrastructure.external.typesafe.client import JevJudge, jev_from_settings

router = APIRouter(prefix="/conversations", tags=["chat"])
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def get_session_factory() -> SessionFactory:
    return get_sessionmaker()


@lru_cache
def _runner() -> ClaudeAgentRunner:
    settings = get_settings()
    return ClaudeAgentRunner(
        settings.claude_model, settings.claude_effort, settings.data_dir / "agente", settings.permitir_api_paga
    )


_JOBS = ChatJobs()


def get_chat_jobs() -> ChatJobs:
    return _JOBS


def get_agent_runner() -> AgentRunner:
    return _runner()


@lru_cache
def _jev() -> JevJudge | None:
    return jev_from_settings()


def get_judgments() -> JudgmentService:
    return JudgmentService(_jev())


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    model: Literal["claude-sonnet-5-5", "claude-opus-5-5"] | None = None
    effort: Literal["medium", "high", "xhigh"] | None = None
    brief: bool = False
    plan: bool = False
    video: bool = False
    complex: bool = False


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime


class ConversationList(BaseModel):
    items: list[ConversationOut]


class MessageOut(BaseModel):
    role: str
    text: str | None
    segments: list[dict[str, Any]] | None
    status: str
    created_at: datetime


class MessageList(BaseModel):
    items: list[MessageOut]


class CreatedOut(BaseModel):
    id: uuid.UUID


def _chat_service(
    session: AsyncSession,
    runner: AgentRunner,
    embedder: Embedder,
    reranker: Reranker,
    judgments: JudgmentService | None = None,
    study_effort: str | None = "padrao",
) -> ChatService:
    settings = get_settings()
    judgments = judgments or JudgmentService(None)
    study_effort = settings.claude_effort_estudo if study_effort == "padrao" else study_effort
    repo = SqlBibleRepository(session)
    passages = PassageService(repo)
    web = SerperClient(settings.serper_api_key) if settings.serper_api_key else None
    executor = ToolExecutor(
        passages,
        SearchService(repo, passages, embedder, reranker),
        repo,
        MemoryService(SqlMemoryRepository(session), judgments.contains_sensitive_data),
        web,
    )
    return ChatService(
        SqlConversationRepository(session),
        passages,
        repo,
        executor,
        runner,
        web is not None,
        judgments=judgments,
        timeout_s=settings.agent_timeout_s,
        long_timeout_s=settings.agent_timeout_longo_s,
        study_effort=study_effort,
    )


@router.post("", response_model=CreatedOut, status_code=201)
async def create_conversation(factory: Annotated[SessionFactory, Depends(get_session_factory)]) -> CreatedOut:
    async with factory() as session:
        return CreatedOut(id=await SqlConversationRepository(session).create())


@router.get("", response_model=ConversationList)
async def list_conversations(factory: Annotated[SessionFactory, Depends(get_session_factory)]) -> ConversationList:
    async with factory() as session:
        items = await SqlConversationRepository(session).recent()
    return ConversationList(items=[ConversationOut(id=c.id, title=c.title, updated_at=c.updated_at) for c in items])


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID, factory: Annotated[SessionFactory, Depends(get_session_factory)]
) -> ConversationOut:
    async with factory() as session:
        conversation = await SqlConversationRepository(session).get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversa não encontrada")
    return ConversationOut(id=conversation.id, title=conversation.title, updated_at=conversation.updated_at)


@router.get("/{conversation_id}/messages", response_model=MessageList)
async def list_messages(
    conversation_id: uuid.UUID, factory: Annotated[SessionFactory, Depends(get_session_factory)]
) -> MessageList:
    async with factory() as session:
        repo = SqlConversationRepository(session)
        if await repo.get(conversation_id) is None:
            raise HTTPException(status_code=404, detail="conversa não encontrada")
        messages = await repo.messages(conversation_id)
    return MessageList(
        items=[
            MessageOut(role=m.role, text=m.text, segments=m.segments, status=m.status, created_at=m.created_at)
            for m in messages
        ]
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID, factory: Annotated[SessionFactory, Depends(get_session_factory)]
) -> Response:
    async with factory() as session:
        if not await SqlConversationRepository(session).delete(conversation_id):
            raise HTTPException(status_code=404, detail="conversa não encontrada")
    return Response(status_code=204)


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _sse(events: AsyncIterator[ChatEvent]) -> StreamingResponse:
    async def body() -> AsyncIterator[str]:
        async for event in events:
            yield event.encode()

    return StreamingResponse(body(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _single(event: ChatEvent) -> AsyncIterator[ChatEvent]:
    yield event


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageIn,
    factory: Annotated[SessionFactory, Depends(get_session_factory)],
    runner: Annotated[AgentRunner, Depends(get_agent_runner)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
    judgments: Annotated[JudgmentService, Depends(get_judgments)],
    jobs: Annotated[ChatJobs, Depends(get_chat_jobs)],
) -> StreamingResponse:
    async def turn() -> AsyncIterator[ChatEvent]:
        async with factory() as session:
            service = _chat_service(session, runner, embedder, reranker, judgments)
            async for event in service.send(
                conversation_id, body.text, body.model, body.effort, body.brief, body.plan, body.video, body.complex
            ):
                yield event

    job: ChatJob | None = jobs.start(conversation_id, turn)
    if job is None:
        return _sse(_single(error_event("ocupado")))
    return _sse(job.subscribe())


@router.get("/{conversation_id}/stream")
async def resume_stream(conversation_id: uuid.UUID, jobs: Annotated[ChatJobs, Depends(get_chat_jobs)]) -> Response:
    job = jobs.get(conversation_id)
    if job is None:
        return Response(status_code=204)
    return _sse(job.subscribe())
