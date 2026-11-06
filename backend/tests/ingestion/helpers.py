import json
from pathlib import Path

from app.domain.bible.books import BOOKS


def synthetic_bible(verses_per_chapter: dict[tuple[int, int], int] | None = None) -> list[dict[str, object]]:
    """66 livros sintéticos (sem texto bíblico real): 2 capítulos x 3 versículos, salvo exceções."""
    overrides = verses_per_chapter or {}
    data: list[dict[str, object]] = []
    for book in BOOKS:
        chapters = []
        for ch in (1, 2):
            n = overrides.get((book.id, ch), 3)
            chapters.append([f"Texto sintético {book.abbrev} {ch}:{v}" for v in range(1, n + 1)])
        data.append({"abbrev": book.source_abbrev, "name": book.pt_name, "chapters": chapters})
    return data


def write_json(path: Path, data: object) -> Path:
    path.write_text("﻿" + json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path
