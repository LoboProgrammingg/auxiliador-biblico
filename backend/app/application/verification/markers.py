import re
from dataclasses import dataclass

from app.application.bible.passages import PassageService
from app.domain.bible.books import BOOKS
from app.domain.bible.entities import ResolvedPassage
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import format_reference

MARKER_RE = re.compile(r"\[\[([^\[\]|]{1,60})(?:\|([A-Za-z0-9]{2,10}))?\]\]")
VISUAL_RE = re.compile(r"\[\[(linha|mapa):([^\[\]]{1,900})\]\]")
SECTION_RE = re.compile(r"^\s*(\d{1,3})\s*[-–]\s*(\d{1,3})\s*=\s*(.{1,80}?)\s*$")
MAX_HELD = 80
MAX_HELD_VISUAL = 950
VISUAL_PREFIXES = ("[[linha:", "[[mapa:")


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


@dataclass(frozen=True)
class TimelineOut:
    marker: str
    reference: str
    book: str
    sections: list[dict[str, object]]


@dataclass(frozen=True)
class MapOut:
    marker: str
    reference: str
    places: list[dict[str, object]]


StreamOut = TextOut | VerseOut | InvalidRefOut | TimelineOut | MapOut


def _held_limit(buffer: str) -> int:
    return MAX_HELD_VISUAL if any(p.startswith(buffer[: len(p)]) for p in VISUAL_PREFIXES) else MAX_HELD


class MarkerStreamProcessor:
    """Converte o texto do modelo em prosa + cartões validados; texto bíblico nunca sai do modelo."""

    def __init__(self, passages: PassageService) -> None:
        self._passages = passages
        self._buffer = ""

    async def _timeline(self, marker: str, body: str) -> StreamOut | None:
        ref, _, raw_sections = body.partition("|")
        chapter, last = await self._passages.chapter(ref.strip())
        sections: list[dict[str, object]] = []
        for raw in raw_sections.split(";"):
            match = SECTION_RE.match(raw)
            if match is None:
                continue
            start, end, title = int(match.group(1)), int(match.group(2)), match.group(3)
            if 1 <= start <= end <= last:
                sections.append({"start": start, "end": end, "title": title})
        if not sections:
            return InvalidRefOut(marker)
        reference = format_reference(chapter)
        return TimelineOut(marker, reference, BOOKS[chapter.book_id - 1].pt_name, sections)

    async def _map(self, marker: str, body: str) -> StreamOut | None:
        chapter, _ = await self._passages.chapter(body.strip())
        places = await self._passages.places(chapter)
        if not places:
            return None
        items: list[dict[str, object]] = [
            {"name": p.name, "kind": p.kind, "lon": p.lon, "lat": p.lat, "verses": p.verses} for p in places
        ]
        return MapOut(marker, format_reference(chapter), items)

    async def _resolve(self, marker: str) -> StreamOut | None:
        visual = VISUAL_RE.fullmatch(marker)
        if visual is not None:
            try:
                handler = self._timeline if visual.group(1) == "linha" else self._map
                return await handler(marker, visual.group(2))
            except InvalidReference:
                return InvalidRefOut(marker)
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
                if len(self._buffer) > _held_limit(self._buffer):
                    out.append(TextOut(self._buffer))
                    self._buffer = ""
                break
            marker, self._buffer = self._buffer[: end + 2], self._buffer[end + 2 :]
            if (resolved := await self._resolve(marker)) is not None:
                out.append(resolved)
        return out

    async def flush(self) -> list[StreamOut]:
        rest, self._buffer = self._buffer, ""
        return [TextOut(rest)] if rest else []
