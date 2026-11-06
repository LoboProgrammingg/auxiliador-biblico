import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.bible.router import router as bible_router
from app.api.v1.chat.router import router as chat_router
from app.api.v1.daily.router import router as daily_router
from app.api.v1.diary.router import router as diary_router
from app.api.v1.export.router import router as export_router
from app.api.v1.health.router import router as health_router
from app.api.v1.memory.router import router as memory_router
from app.api.v1.plans.router import router as plans_router
from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.core.logging import configure_logging
from app.infrastructure.backup import daily_backup_loop
from app.infrastructure.database.conversation_repository import SqlConversationRepository


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with get_sessionmaker()() as session:
        await SqlConversationRepository(session).mark_interrupted()
    backups = asyncio.create_task(daily_backup_loop()) if get_settings().backup_enabled else None
    yield
    if backups is not None:
        backups.cancel()
        with suppress(asyncio.CancelledError):
            await backups


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Auxiliador Bíblico", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(bible_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(daily_router, prefix="/api/v1")
    app.include_router(diary_router, prefix="/api/v1")
    app.include_router(plans_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")
    return app


app = create_app()
