import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PrayerStatus = Literal["aberto", "respondido"]


@dataclass(frozen=True)
class Prayer:
    id: uuid.UUID
    title: str
    details: str | None
    status: PrayerStatus
    answer_note: str | None
    created_at: datetime
    answered_at: datetime | None


@dataclass(frozen=True)
class VerseNote:
    id: int
    reference: str
    content: str
    updated_at: datetime
