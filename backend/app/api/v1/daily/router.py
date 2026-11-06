from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_embedder, get_reranker
from app.api.v1.chat.router import SessionFactory, _chat_service, get_agent_runner, get_judgments, get_session_factory
from app.application.chat.ports import AgentRunner, Embedder, Reranker
from app.application.daily.service import DailyWordError, DailyWordService
from app.application.judgments.service import JudgmentService
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.daily_word_repository import SqlDailyWordRepository

router = APIRouter(tags=["daily"])


class DailyWordOut(BaseModel):
    day: date
    reference: str | None
    segments: list[dict[str, Any]]


@router.post("/daily-word", response_model=DailyWordOut)
async def daily_word(
    factory: Annotated[SessionFactory, Depends(get_session_factory)],
    runner: Annotated[AgentRunner, Depends(get_agent_runner)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
    judgments: Annotated[JudgmentService, Depends(get_judgments)],
) -> DailyWordOut:
    async with factory() as session:
        chat = _chat_service(session, runner, embedder, reranker, judgments)
        service = DailyWordService(SqlConversationRepository(session), SqlDailyWordRepository(session), chat)
        try:
            word = await service.today()
        except DailyWordError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DailyWordOut(day=word.day, reference=word.reference, segments=word.segments)
