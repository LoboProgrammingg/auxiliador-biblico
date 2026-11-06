"""Dados para as ilustrações (genealogia, rota, perfil da palavra): tudo vem do banco, nada é inventado."""

from typing import Any

from app.domain.bible.books import BOOKS
from app.domain.bible.entities import Person, PersonRelation
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import VerseRange, parse_reference
from app.domain.bible.repositories import BibleRepository

MAX_PEOPLE = 40


def _chapters(ref: str, end: int | None) -> tuple[VerseRange, int, str]:
    r = parse_reference(ref.strip())
    if r is None:
        raise InvalidReference(ref)
    last = max(r.chapter, end or r.chapter)
    abbrev = BOOKS[r.book_id - 1].abbrev
    label = f"{abbrev} {r.chapter}" if last == r.chapter else f"{abbrev} {r.chapter}–{last}"
    return r, last, label


def _links(relations: list[PersonRelation]) -> list[dict[str, str]]:
    links: dict[tuple[str, str, str], None] = {}
    for rel in relations:
        if rel.kind == "pai_mae":
            links[(rel.other_id, rel.person_id, "pai")] = None
        elif rel.kind == "filho":
            links[(rel.person_id, rel.other_id, "pai")] = None
        elif rel.kind == "conjuge":
            pair = sorted((rel.person_id, rel.other_id))
            links[(pair[0], pair[1], "conjuge")] = None
    return [{"from": a, "to": b, "kind": k} for a, b, k in links]


def _node(person_id: str, name: str, is_pt: bool, brief: str | None, in_text: bool) -> dict[str, Any]:
    return {"id": person_id, "name": name, "name_is_pt": is_pt, "brief": brief, "in_text": in_text}


async def genealogy(repo: BibleRepository, ref: str, end: int | None = None) -> dict[str, Any] | None:
    r, last, label = _chapters(ref, end)
    people: list[Person] = await repo.people_in_range(r.book_id, r.chapter, last)
    relations = [rel for rel in await repo.relations([p.id for p in people]) if rel.kind != "irmao"]
    linked = {rel.person_id for rel in relations}
    focus = [p for p in people if p.id in linked][:MAX_PEOPLE]
    nodes = {p.id: _node(p.id, p.name, p.name_is_pt, p.brief, True) for p in focus}
    for rel in relations:
        if rel.person_id in nodes and rel.other_id not in nodes and rel.other_name and len(nodes) < MAX_PEOPLE:
            nodes[rel.other_id] = _node(rel.other_id, rel.other_name, rel.other_is_pt, None, False)
    links = [link for link in _links(relations) if link["from"] in nodes and link["to"] in nodes]
    if not links:
        return None
    return {"reference": label, "people": list(nodes.values()), "links": links}


async def route(repo: BibleRepository, ref: str, end: int | None = None) -> dict[str, Any] | None:
    r, last, label = _chapters(ref, end)
    stops: dict[str, dict[str, Any]] = {}
    for chapter in range(r.chapter, last + 1):
        for place in await repo.places_in_chapter(r.book_id, chapter):
            if place.name not in stops:
                stops[place.name] = {
                    "name": place.name,
                    "lon": place.lon,
                    "lat": place.lat,
                    "first": f"{chapter}:{place.verses[0]}",
                    "order": (chapter, place.verses[0]),
                }
    ordered = sorted(stops.values(), key=lambda s: s["order"])
    if len(ordered) < 2:
        return None
    return {"reference": label, "stops": [{k: v for k, v in s.items() if k != "order"} for s in ordered]}


async def word_profile(repo: BibleRepository, strong: str) -> dict[str, Any] | None:
    entry = (await repo.lexicon([strong])).get(strong)
    counts = await repo.strong_by_book(strong)
    if entry is None or not counts:
        return None
    return {
        "strong": strong,
        "lemma": entry.lemma,
        "transliteration": entry.transliteration,
        "gloss": entry.gloss,
        "total": sum(n for _, n in counts),
        "by_book": [{"book": BOOKS[b - 1].pt_name, "count": n} for b, n in counts],
    }
