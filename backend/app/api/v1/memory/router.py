from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.memory.service import MemoryService
from app.core.db import get_session
from app.domain.memory.errors import InvalidMemoryContent, InvalidMemoryTopic
from app.infrastructure.database.memory_repository import SqlMemoryRepository

router = APIRouter(prefix="/memories", tags=["memory"])


def get_memory_service(session: Annotated[AsyncSession, Depends(get_session)]) -> MemoryService:
    return MemoryService(SqlMemoryRepository(session))


class MemoryOut(BaseModel):
    topic: str
    content: str
    updated_at: datetime


class MemoryList(BaseModel):
    items: list[MemoryOut]


class MemoryIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class SavedOut(BaseModel):
    topic: str


Service = Annotated[MemoryService, Depends(get_memory_service)]


@router.get("", response_model=MemoryList)
async def list_memories(service: Service) -> MemoryList:
    return MemoryList(items=[MemoryOut(**item.__dict__) for item in await service.list_all()])


@router.put("/{topic}", response_model=SavedOut)
async def save_memory(topic: str, body: MemoryIn, service: Service) -> SavedOut:
    try:
        return SavedOut(topic=await service.save(topic, body.content))
    except (InvalidMemoryTopic, InvalidMemoryContent) as exc:
        raise HTTPException(status_code=422, detail="tópico ou conteúdo inválido") from exc


@router.delete("/{topic}", status_code=204)
async def delete_memory(topic: str, service: Service) -> Response:
    try:
        deleted = await service.forget(topic)
    except InvalidMemoryTopic as exc:
        raise HTTPException(status_code=422, detail="tópico inválido") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="memória não encontrada")
    return Response(status_code=204)
