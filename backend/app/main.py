from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.bible.router import router as bible_router
from app.api.v1.chat.router import router as chat_router
from app.api.v1.health.router import router as health_router
from app.api.v1.memory.router import router as memory_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Auxiliador Bíblico")
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
    return app


app = create_app()
