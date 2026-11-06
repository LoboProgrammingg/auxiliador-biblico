import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.diary.notes import note_range
from app.core.db import get_session
from app.domain.bible.errors import InvalidReference
from app.domain.diary.entities import Prayer, VerseNote
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.database.diary_repository import SqlPrayerRepository, SqlVerseNoteRepository

router = APIRouter(tags=["diary"])
Session = Annotated[AsyncSession, Depends(get_session)]


class PrayerIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    details: str | None = Field(default=None, max_length=4000)


class PrayerUpdate(PrayerIn):
    status: Literal["aberto", "respondido"]
    answer_note: str | None = Field(default=None, max_length=4000)


class PrayerOut(BaseModel):
    id: uuid.UUID
    title: str
    details: str | None
    status: str
    answer_note: str | None
    created_at: datetime
    answered_at: datetime | None


class PrayerList(BaseModel):
    items: list[PrayerOut]


class NoteIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class NoteOut(BaseModel):
    id: int
    reference: str
    content: str
    updated_at: datetime


class NoteList(BaseModel):
    items: list[NoteOut]


def _prayer(p: Prayer) -> PrayerOut:
    return PrayerOut(**p.__dict__)


def _note(n: VerseNote) -> NoteOut:
    return NoteOut(**n.__dict__)


@router.get("/prayers", response_model=PrayerList)
async def list_prayers(session: Session) -> PrayerList:
    return PrayerList(items=[_prayer(p) for p in await SqlPrayerRepository(session).list_all()])


@router.post("/prayers", response_model=PrayerOut, status_code=201)
async def create_prayer(body: PrayerIn, session: Session) -> PrayerOut:
    return _prayer(await SqlPrayerRepository(session).create(body.title.strip(), body.details))


@router.put("/prayers/{prayer_id}", response_model=PrayerOut)
async def update_prayer(prayer_id: uuid.UUID, body: PrayerUpdate, session: Session) -> PrayerOut:
    prayer = await SqlPrayerRepository(session).update(
        prayer_id, body.title.strip(), body.details, body.status, body.answer_note
    )
    if prayer is None:
        raise HTTPException(status_code=404, detail="pedido de oração não encontrado")
    return _prayer(prayer)


@router.delete("/prayers/{prayer_id}", status_code=204)
async def delete_prayer(prayer_id: uuid.UUID, session: Session) -> Response:
    if not await SqlPrayerRepository(session).delete(prayer_id):
        raise HTTPException(status_code=404, detail="pedido de oração não encontrado")
    return Response(status_code=204)


async def _range(ref: str, session: AsyncSession):  # type: ignore[no-untyped-def]
    try:
        return await note_range(ref, SqlBibleRepository(session))
    except InvalidReference as exc:
        raise HTTPException(status_code=422, detail="referência não encontrada na Bíblia") from exc


@router.get("/verse-notes", response_model=NoteList)
async def list_notes(session: Session) -> NoteList:
    return NoteList(items=[_note(n) for n in await SqlVerseNoteRepository(session).list_all()])


@router.get("/verse-notes/by-ref", response_model=NoteOut)
async def get_note(session: Session, ref: Annotated[str, Query(max_length=60)]) -> NoteOut:
    r, _ = await _range(ref, session)
    note = await SqlVerseNoteRepository(session).get(r)
    if note is None:
        raise HTTPException(status_code=404, detail="sem anotação")
    return _note(note)


@router.put("/verse-notes", response_model=NoteOut)
async def save_note(body: NoteIn, session: Session, ref: Annotated[str, Query(max_length=60)]) -> NoteOut:
    r, reference = await _range(ref, session)
    return _note(await SqlVerseNoteRepository(session).upsert(r, reference, body.content))


@router.delete("/verse-notes/{note_id}", status_code=204)
async def delete_note(note_id: int, session: Session) -> Response:
    if not await SqlVerseNoteRepository(session).delete(note_id):
        raise HTTPException(status_code=404, detail="anotação não encontrada")
    return Response(status_code=204)
