import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Conversation:
    id: uuid.UUID
    title: str
    agent_session_id: str | None
    updated_at: datetime


@dataclass(frozen=True)
class Message:
    id: int
    role: str
    text: str | None
    segments: list[dict[str, Any]] | None
    created_at: datetime
