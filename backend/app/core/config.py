from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://biblia:biblia@127.0.0.1:5433/biblia"
    database_url_test: str = "postgresql+asyncpg://biblia:biblia@127.0.0.1:5433/biblia_test"
    serper_api_key: str | None = None
    typesafe_api_key: str | None = None
    jev_model: str = "jev-latest"
    permitir_api_paga: bool = False
    claude_model: str = "claude-sonnet-5-5"
    claude_effort: str = "medium"
    claude_effort_estudo: str = "high"
    agent_timeout_s: float = 300.0
    voyage_api_key: str | None = None
    embed_model: str = "voyage-4-large"
    rerank_model: str = "rerank-3"
    embed_dims: int = 1024
    voyage_tpm: int = 10_000
    voyage_rpm: int = 3
    data_dir: Path = REPO_ROOT / "data"
    backup_dir: Path = REPO_ROOT / "data" / "backups"
    backup_keep_days: int = 30
    backup_enabled: bool = True
    frontend_url: str = "http://127.0.0.1:3000"
    chrome_bin: str | None = None
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
