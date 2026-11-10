import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.application.bible.passages import PassageService
from app.application.chat.events import passage_payload
from app.application.verification.thinkers import find_thinker
from app.domain.bible.books import BOOKS
from app.domain.bible.entities import Person, Place, ResolvedPassage
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import VerseRange, format_reference

MARKER_RE = re.compile(r"\[\[([^\[\]|]{1,60})(?:\|([A-Za-z0-9]{2,10}))?\]\]")
VISUAL_RE = re.compile(r"\[\[(linha|mapa|quiasmo|rota|fio):([^\[\]]{1,900})\]\]")
SECTION_RE = re.compile(r"^\s*(\d{1,3})\s*[-–]\s*(\d{1,3})\s*=\s*(.{1,80}?)\s*$")
THINKER_RE = re.compile(r"\[\[pensador:([^\[\]]{1,1150})\]\]")
MAX_THINKER_TEXT = 900
THINKER_KINDS = {"citacao": "citação", "parafrase": "paráfrase"}
CHIASM_PART_RE = re.compile(r"^\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*=\s*(.{1,80}?)\s*$")
logger = logging.getLogger(__name__)
MAX_HELD = 80
MAX_HELD_VISUAL = 1200
VISUAL_PREFIXES = ("[[linha:", "[[mapa:", "[[quiasmo:", "[[rota:", "[[fio:", "[[pensador:")
DIRECTIONS = {"oriente", "ocidente", "norte", "sul", "leste", "oeste"}
MAX_LINKS = 6
MIN_KEY_CHARS = 40


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


@dataclass(frozen=True)
class ChiasmOut:
    marker: str
    reference: str
    book: str
    parts: list[dict[str, object]]


@dataclass(frozen=True)
class RouteOut:
    marker: str
    reference: str
    legs: list[dict[str, Any]]


@dataclass(frozen=True)
class ThreadOut:
    marker: str
    reference: str
    links: list[dict[str, Any]]
    books: list[dict[str, Any]]


@dataclass(frozen=True)
class ThinkerOut:
    """Ideia de um pensador: cartão próprio, nunca misturado ao texto bíblico nem à checagem de citações."""

    marker: str
    name: str
    period: str
    work: str
    kind: str
    text: str
    objection: bool


StreamOut = TextOut | VerseOut | InvalidRefOut | TimelineOut | MapOut | ChiasmOut | RouteOut | ThreadOut | ThinkerOut


def _places_between(places: list[Place], start: int, end: int) -> list[dict[str, object]]:
    found = [
        (min(v for v in p.verses if start <= v <= end), p) for p in places if any(start <= v <= end for v in p.verses)
    ]
    found.sort(key=lambda t: t[0])
    return [{"name": p.name, "kind": p.kind, "lon": p.lon, "lat": p.lat} for _, p in found]


def _people_between(people: list[Person], chapter: int, start: int, end: int) -> list[dict[str, object]]:
    found = [
        (min(v for c, v in p.verses if c == chapter and start <= v <= end), p)
        for p in people
        if any(c == chapter and start <= v <= end for c, v in p.verses)
    ]
    found.sort(key=lambda t: t[0])
    return [{"name": p.name, "pt": p.name_is_pt} for _, p in found]


def _key(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.lower().strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def mirrored_label(index: int, count: int) -> str:
    depth = min(index, count - 1 - index)
    return chr(ord("A") + depth) + ("'" if index > count - 1 - index else "")


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
        await self._enrich(chapter, sections)
        return TimelineOut(marker, reference, BOOKS[chapter.book_id - 1].pt_name, sections)

    async def _enrich(self, chapter: VerseRange, sections: list[dict[str, object]]) -> None:
        """Cada cena ganha quem aparece, onde acontece e um versículo dela, tudo do banco."""
        places = await self._passages.places(chapter)
        people = await self._passages.people(chapter)
        for section in sections:
            start, end = int(str(section["start"])), int(str(section["end"]))
            section["places"] = _places_between(places, start, end)
            section["people"] = _people_between(people, chapter.chapter, start, end)
            passage = await self._passages.resolve(f"{format_reference(chapter)}:{start}-{end}")
            longish = [v for v in passage.verses if len(v.text) >= MIN_KEY_CHARS] or passage.verses
            key = min(longish, key=lambda v: len(v.text))
            section["key"] = {"n": key.verse, "text": key.text, "translation": passage.translation}

    async def _chiasm(self, marker: str, body: str) -> StreamOut | None:
        """Estrutura em espelho (A B C B' A'): partes em ordem, sem sobreposição, dentro do capítulo."""
        ref, _, raw_parts = body.partition("|")
        chapter, last = await self._passages.chapter(ref.strip())
        parts: list[tuple[int, int, str]] = []
        for raw in raw_parts.split(";"):
            match = CHIASM_PART_RE.match(raw)
            if match is None:
                return InvalidRefOut(marker)
            start = int(match.group(1))
            end = int(match.group(2) or start)
            if not (start <= end <= last) or (parts and start <= parts[-1][1]) or start < 1:
                return InvalidRefOut(marker)
            parts.append((start, end, match.group(3)))
        if len(parts) < 3:
            return InvalidRefOut(marker)
        items: list[dict[str, object]] = [
            {"label": mirrored_label(i, len(parts)), "start": s, "end": e, "title": t}
            for i, (s, e, t) in enumerate(parts)
        ]
        return ChiasmOut(marker, format_reference(chapter), BOOKS[chapter.book_id - 1].pt_name, items)

    async def _route(self, marker: str, body: str) -> StreamOut | None:
        """Viagem em trechos (A>B>C=quem); toda parada precisa ser um lugar citado no capítulo."""
        ref, _, raw_legs = body.partition("|")
        chapter, _ = await self._passages.chapter(ref.strip())
        known = {_key(p.name): p for p in await self._passages.places(chapter)}
        legs: list[dict[str, Any]] = []
        for raw in raw_legs.split(";")[:6]:
            path, _, who = raw.partition("=")
            names = [n for n in (part.strip() for part in path.split(">")) if n]
            if len(names) < 2 or any(_key(n) not in known for n in names):
                continue
            stops = []
            for n in names:
                p = known[_key(n)]
                region = p.kind == "region"
                stops.append(
                    {
                        "name": p.name,
                        "kind": p.kind,
                        "lon": p.lon,
                        "lat": p.lat,
                        "verses": p.verses,
                        "region": region,
                        "direction": region and _key(p.name) in DIRECTIONS,
                    }
                )
            legs.append({"who": who.strip()[:60] or None, "stops": stops})
        if not legs:
            return InvalidRefOut(marker)
        return RouteOut(marker, format_reference(chapter), legs)

    async def _thread(self, marker: str, body: str) -> StreamOut | None:
        """Arcos do capítulo até o outro Testamento (referências cruzadas mais votadas); sem ligação, nada."""
        chapter, _ = await self._passages.chapter(body.strip())
        links: list[dict[str, Any]] = []
        for from_verse, target, votes in await self._passages.links(chapter, MAX_LINKS):
            try:
                source = await self._passages.resolve(f"{format_reference(chapter)}:{from_verse}")
                passage = await self._passages.resolve(format_reference(target))
            except InvalidReference:
                continue
            links.append(
                {
                    "from_verse": from_verse,
                    "from_text": source.verses[0].text,
                    "votes": votes,
                    "target": passage_payload(passage),
                }
            )
        if not links:
            return None
        sizes = await self._passages.book_sizes()
        books = [{"id": b.id, "abbrev": b.abbrev, "verses": sizes.get(b.id, 0)} for b in BOOKS]
        return ThreadOut(marker, format_reference(chapter), links, books)

    async def _map(self, marker: str, body: str) -> StreamOut | None:
        chapter, _ = await self._passages.chapter(body.strip())
        places = await self._passages.places(chapter)
        if not places:
            return None
        items: list[dict[str, object]] = [
            {"name": p.name, "kind": p.kind, "lon": p.lon, "lat": p.lat, "verses": p.verses} for p in places
        ]
        return MapOut(marker, format_reference(chapter), items)

    @staticmethod
    def _thinker(marker: str) -> StreamOut | None:
        """Nome|Obra|tipo|texto, ou Nome|Obra|texto (paráfrase). Se o 3º campo não for um tipo, ele é o resumo e o
        4º (frase "literal" não conferida) é descartado. Nome fora do catálogo ou texto vazio/longo: descartado."""
        match = THINKER_RE.fullmatch(marker)
        parts = [p.strip() for p in match.group(1).split("|")] if match is not None else []
        thinker = find_thinker(re.sub(r"\s*\(.*?\)\s*", " ", parts[0])) if len(parts) in (3, 4) else None
        kind = "paráfrase"
        text = parts[2] if len(parts) >= 3 else ""
        if len(parts) == 4 and (known := THINKER_KINDS.get(_key(parts[2]))) is not None:
            kind, text = known, parts[3]
        if thinker is None or not parts[1] or not text or len(text) > MAX_THINKER_TEXT or len(parts[1]) > 160:
            logger.warning("cartão de pensador descartado: %s", marker[:200])
            return None
        return ThinkerOut(marker, thinker.name, thinker.period, parts[1], kind, text, thinker.objection)

    async def _resolve(self, marker: str) -> StreamOut | None:
        if marker.startswith("[[pensador:"):
            return self._thinker(marker)
        visual = VISUAL_RE.fullmatch(marker)
        if visual is not None:
            try:
                handler = {
                    "linha": self._timeline,
                    "mapa": self._map,
                    "quiasmo": self._chiasm,
                    "rota": self._route,
                    "fio": self._thread,
                }[visual.group(1)]
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
            inner = self._buffer.find("[[", 2)
            if inner != -1 and (end == -1 or inner < end):
                out.append(TextOut(self._buffer[:inner]))
                self._buffer = self._buffer[inner:]
                continue
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
