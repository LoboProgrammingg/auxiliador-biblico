import re
from dataclasses import dataclass

from app.application.bible.passages import PassageService
from app.domain.bible.entities import ResolvedPassage
from app.domain.bible.errors import InvalidReference

MARKER_RE = re.compile(r"\[\[([^\[\]|]{1,60})(?:\|([A-Za-z0-9]{2,10}))?\]\]")
MAX_HELD = 80


@dataclass(frozen=True)
class TextOut:
    text: str


@dataclass(frozen=True)
class VerseOut:
    marker: str
    passage: ResolvedPassage


@dataclass(frozen=True)
class InvalidRefOut:
    marker: str


StreamOut = TextOut | VerseOut | InvalidRefOut


class MarkerStreamProcessor:
    """Converte o texto do modelo em prosa + cartões validados; texto bíblico nunca sai do modelo."""

    def __init__(self, passages: PassageService) -> None:
        self._passages = passages
        self._buffer = ""

    async def _resolve(self, marker: str) -> StreamOut:
        match = MARKER_RE.fullmatch(marker)
        if match is None:
            return TextOut(marker)
        try:
            return VerseOut(marker, await self._passages.resolve(match.group(1).strip(), match.group(2)))
        except InvalidReference:
            return InvalidRefOut(marker)

    async def feed(self, delta: str) -> list[StreamOut]:
        self._buffer += delta
        out: list[StreamOut] = []
        while self._buffer:
            start = self._buffer.find("[")
            if start == -1:
                out.append(TextOut(self._buffer))
                self._buffer = ""
                break
            if start > 0:
                out.append(TextOut(self._buffer[:start]))
                self._buffer = self._buffer[start:]
            if len(self._buffer) < 2:
                break
            if self._buffer[1] != "[":
                out.append(TextOut("["))
                self._buffer = self._buffer[1:]
                continue
            end = self._buffer.find("]]")
            if end == -1:
                if len(self._buffer) > MAX_HELD:
                    out.append(TextOut(self._buffer))
                    self._buffer = ""
                break
            marker, self._buffer = self._buffer[: end + 2], self._buffer[end + 2 :]
            out.append(await self._resolve(marker))
        return out

    async def flush(self) -> list[StreamOut]:
        rest, self._buffer = self._buffer, ""
        return [TextOut(rest)] if rest else []
