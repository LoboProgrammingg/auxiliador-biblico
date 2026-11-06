import re
from dataclasses import dataclass
from typing import Literal

from app.application.bible.passages import PassageService
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import find_references
from app.domain.bible.repositories import BibleRepository
from app.domain.bible.text import normalize_for_match

QUOTE_CHARS = re.compile(r"[\"“”]")
MAX_QUOTE = 600
MIN_QUOTE_WORDS = 6


@dataclass(frozen=True)
class VerificationIssue:
    kind: Literal["referencia_inexistente", "citacao_nao_confere"]
    excerpt: str


async def _reference_issues(prose: str, passages: PassageService, asked: set[object]) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for raw, parsed in find_references(prose):
        if parsed is not None and parsed in asked:
            continue
        try:
            if parsed is None:
                raise InvalidReference(raw)
            await passages.resolve(parsed)
        except InvalidReference:
            issues.append(VerificationIssue("referencia_inexistente", raw))
    return issues


def quoted_spans(prose: str) -> list[str]:
    """Pareia aspas em sequência (abre, fecha); “ ” e \" contam igual. Aspas sem par são ignoradas."""
    positions = [m.start() for m in QUOTE_CHARS.finditer(prose)]
    spans: list[str] = []
    for open_at, close_at in zip(positions[0::2], positions[1::2], strict=False):
        inner = prose[open_at + 1 : close_at].strip()
        if inner and len(inner) <= MAX_QUOTE and "\n\n" not in inner:
            spans.append(inner)
    return spans


async def _quote_issues(prose: str, repo: BibleRepository) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    for quote in quoted_spans(prose):
        normalized = normalize_for_match(quote)
        if len(normalized.split()) < MIN_QUOTE_WORDS:
            continue
        if await repo.find_verse_by_norm(normalized) is None:
            issues.append(VerificationIssue("citacao_nao_confere", quote))
    return issues


async def final_check(
    prose: str, passages: PassageService, repo: BibleRepository, user_text: str = ""
) -> list[VerificationIssue]:
    """Varredura determinística da prosa já sem marcadores: referências soltas e citações entre aspas.

    Referências que o próprio usuário citou não contam (ex.: explicar que "João 3:99" não existe)."""
    asked: set[object] = {parsed for _, parsed in find_references(user_text) if parsed is not None}
    return await _reference_issues(prose, passages, asked) + await _quote_issues(prose, repo)
