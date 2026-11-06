import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from functools import lru_cache
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.daily_word_repository import SqlDailyWordRepository
from app.infrastructure.database.plan_repository import SqlPlanRepository
from app.infrastructure.pdf.chrome import ChromePdf, PageMissing, PdfUnavailable

router = APIRouter(prefix="/export", tags=["export"])
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PdfRenderer(Protocol):
    async def render(self, url: str) -> bytes: ...


@lru_cache
def _chrome() -> ChromePdf:
    return ChromePdf(get_settings().chrome_bin)


def get_pdf_renderer() -> PdfRenderer:
    return _chrome()


Exists = Callable[[str, str], Awaitable[bool]]


def get_exists(session: Annotated[AsyncSession, Depends(get_session)]) -> Exists:
    async def exists(kind: str, item_id: str) -> bool:
        if kind == "conversa":
            return await SqlConversationRepository(session).get(uuid.UUID(item_id)) is not None
        if kind == "palavra":
            return await SqlDailyWordRepository(session).get(date.fromisoformat(item_id)) is not None
        return await SqlPlanRepository(session).get(uuid.UUID(item_id)) is not None

    return exists


def _valid_id(kind: str, item_id: str) -> str:
    try:
        if kind == "palavra":
            if not _DAY.match(item_id):
                raise ValueError(item_id)
            return date.fromisoformat(item_id).isoformat()
        return str(uuid.UUID(item_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="identificador inválido") from exc


@router.get("/{kind}/{item_id}.pdf")
async def export_pdf(
    kind: Literal["conversa", "palavra", "plano"],
    item_id: str,
    renderer: Annotated[PdfRenderer, Depends(get_pdf_renderer)],
    exists: Annotated[Exists, Depends(get_exists)],
) -> Response:
    valid = _valid_id(kind, item_id)
    if not await exists(kind, valid):
        raise HTTPException(status_code=404, detail="nada encontrado para exportar")
    url = f"{get_settings().frontend_url.rstrip('/')}/imprimir/{kind}/{valid}"
    try:
        pdf = await renderer.render(url)
    except PageMissing as exc:
        raise HTTPException(status_code=404, detail="nada encontrado para exportar") from exc
    except PdfUnavailable as exc:
        detail = (
            f"Não consegui gerar o PDF: {exc}. Confira se o Google Chrome está instalado e a interface está aberta."
        )
        raise HTTPException(status_code=503, detail=detail) from exc
    name = f"auxiliador-{kind}-{valid[:10] if kind == 'palavra' else valid[:8]}.pdf"
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'}
    )
