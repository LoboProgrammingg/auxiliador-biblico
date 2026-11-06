import re

from app.domain.bible.books import strip_accents


def normalize_for_match(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", strip_accents(value.lower()))
    return " ".join(cleaned.split())
