import os

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


def agent_mode() -> str:
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return "assinatura_local"
    return "api_paga" if get_settings().permitir_api_paga else "chave_paga_bloqueada"


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "agente": agent_mode(),
        "embeddings": "ok" if settings.voyage_api_key else "sem_chave",
        "web_serper": "ok" if settings.serper_api_key else "desligado",
    }
