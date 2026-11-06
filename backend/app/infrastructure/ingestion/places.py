"""Lugares bíblicos com coordenadas — OpenBible.info Bible-Geocoding-Data (CC BY 4.0)."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.books import BOOKS

PLACES_URL = "https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/main/data/ancient.jsonl"
OSIS_TO_BOOK = {b.osis: b.id for b in BOOKS}
_SUFFIX = re.compile(r"\s+\d+$")
_OSIS = re.compile(r"^([1-3]?[A-Z][A-Za-z]+)\.(\d+)\.(\d+)$")

# Nomes em português (grafia das Bíblias brasileiras) para os lugares mais citados; sem entrada → nome em inglês.
PT_NAMES = {
    "Jerusalem": "Jerusalém",
    "Egypt": "Egito",
    "Babylon": "Babilônia",
    "Jordan": "Jordão",
    "Moab": "Moabe",
    "Zion": "Sião",
    "Assyria": "Assíria",
    "Samaria": "Samaria",
    "Edom": "Edom",
    "Ammon": "Amom",
    "Canaan": "Canaã",
    "Syria": "Síria",
    "Gilead": "Gileade",
    "Chaldea": "Caldeia",
    "Galilee": "Galileia",
    "Bethel": "Betel",
    "Tyre": "Tiro",
    "Jericho": "Jericó",
    "Hebron": "Hebrom",
    "Damascus": "Damasco",
    "Lebanon": "Líbano",
    "Bashan": "Basã",
    "Judea": "Judeia",
    "Bethlehem": "Belém",
    "Midian": "Midiã",
    "Sodom": "Sodoma",
    "City of David": "Cidade de Davi",
    "Shechem": "Siquém",
    "Nile": "Nilo",
    "Gibeah": "Gibeá",
    "Euphrates": "Eufrates",
    "Negeb": "Neguebe",
    "Gibeon": "Gibeom",
    "Gath": "Gate",
    "Sidon": "Sidom",
    "Shiloh": "Siló",
    "Heshbon": "Hesbom",
    "Great Sea": "Mar Grande",
    "Mount Seir": "Monte Seir",
    "Gilgal": "Gilgal",
    "Nazareth": "Nazaré",
    "Mizpah": "Mispa",
    "Ai": "Ai",
    "Nineveh": "Nínive",
    "Mount Sinai": "Monte Sinai",
    "Jezreel": "Jezreel",
    "Amalek": "Amaleque",
    "Persia": "Pérsia",
    "Arabah": "Arabá",
    "Mount Zion": "Monte Sião",
    "Dan": "Dã",
    "Macedonia": "Macedônia",
    "Kadesh-barnea": "Cades-Barneia",
    "Gomorrah": "Gomorra",
    "Beersheba": "Berseba",
    "Philistia": "Filístia",
    "Lachish": "Laquis",
    "Gaza": "Gaza",
    "Salt Sea": "Mar Salgado",
    "Red Sea": "Mar Vermelho",
    "Hamath": "Hamate",
    "Asia": "Ásia",
    "Ashdod": "Asdode",
    "Susa": "Susã",
    "Ramoth-gilead": "Ramote-Gileade",
    "Jabesh-gilead": "Jabes-Gileade",
    "Ephesus": "Éfeso",
    "Ekron": "Ecrom",
    "Cush": "Cuxe",
    "Sheba": "Sabá",
    "Mount of Olives": "Monte das Oliveiras",
    "Mount Carmel": "Monte Carmelo",
    "Capernaum": "Cafarnaum",
    "Caesarea": "Cesareia",
    "Antioch": "Antioquia",
    "Anathoth": "Anatote",
    "Rabbah": "Rabá",
    "Mount Horeb": "Monte Horebe",
    "Beth-shemesh": "Bete-Semes",
    "Tarshish": "Társis",
    "Ramah": "Ramá",
    "Mount Hermon": "Monte Hermom",
    "Mahanaim": "Maanaim",
    "Elam": "Elão",
    "Rome": "Roma",
    "Keilah": "Queila",
    "Babylonia": "Babilônia",
    "Tekoa": "Tecoa",
    "Kidron": "Cedrom",
    "Joppa": "Jope",
    "Gezer": "Gezer",
    "Ziklag": "Ziclague",
    "Wilderness of Sinai": "Deserto do Sinai",
    "Tirzah": "Tirza",
    "Eden": "Éden",
    "Valley of Hinnom": "Vale de Hinom",
    "Megiddo": "Megido",
    "Haran": "Harã",
    "Cyprus": "Chipre",
    "Bethany": "Betânia",
    "Ashkelon": "Asquelom",
    "Arnon": "Arnom",
    "Zorah": "Zorá",
    "Media": "Média",
    "Hazor": "Hazor",
    "Goshen": "Gósen",
    "Corinth": "Corinto",
    "Aram": "Arã",
    "Succoth": "Sucote",
    "Sea of Galilee": "Mar da Galileia",
    "Ophir": "Ofir",
    "Achaia": "Acaia",
    "Thessalonica": "Tessalônica",
    "Mount Tabor": "Monte Tabor",
    "Crete": "Creta",
    "Mount Gilboa": "Monte Gilboa",
    "Memphis": "Mênfis",
    "Bethsaida": "Betsaida",
    "Cana": "Caná",
    "Bethany beyond the Jordan": "Betânia além do Jordão",
    "Emmaus": "Emaús",
    "Golgotha": "Gólgota",
    "Gethsemane": "Getsêmani",
    "Philippi": "Filipos",
    "Galatia": "Galácia",
    "Athens": "Atenas",
    "Tarsus": "Tarso",
    "Patmos": "Patmos",
    "Smyrna": "Esmirna",
    "Laodicea": "Laodiceia",
    "Colossae": "Colossos",
    "Sychar": "Sicar",
    "Chorazin": "Corazim",
    "Magadan": "Magadã",
    "Nain": "Naim",
    "Decapolis": "Decápolis",
    "Caesarea Philippi": "Cesareia de Filipe",
    "Pool of Siloam": "Tanque de Siloé",
    "Mount Moriah": "Monte Moriá",
    "East": "Oriente",
    "Ur": "Ur",
    "Ararat": "Ararate",
    "Pisgah": "Pisga",
    "Mount Nebo": "Monte Nebo",
}


@dataclass(frozen=True)
class PlaceRow:
    id: str
    name_en: str
    name_pt: str | None
    kind: str
    lon: float
    lat: float
    verses: list[tuple[int, int, int]] = field(default_factory=list)


def pt_name(name_en: str) -> str | None:
    return PT_NAMES.get(name_en)


def _verse(osis: str) -> tuple[int, int, int] | None:
    match = _OSIS.match(osis)
    if not match or match.group(1) not in OSIS_TO_BOOK:
        return None
    return OSIS_TO_BOOK[match.group(1)], int(match.group(2)), int(match.group(3))


def parse_place(record: dict[str, Any]) -> PlaceRow | None:
    lonlat = next(
        (r["lonlat"] for i in record.get("identifications", []) for r in i.get("resolutions", []) if r.get("lonlat")),
        None,
    )
    if not lonlat:
        return None
    lon, lat = (float(x) for x in lonlat.split(",")[:2])
    name = _SUFFIX.sub("", record["friendly_id"]).strip()
    verses = [v for item in record.get("verses", []) if (v := _verse(item.get("osis", "")))]
    kind = (record.get("types") or ["lugar"])[0]
    return PlaceRow(record["id"], name, pt_name(name), kind, lon, lat, verses)


async def load_places(session: AsyncSession, path: Path) -> int:
    await session.execute(text("DELETE FROM places"))
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        place = parse_place(json.loads(line)) if line.strip() else None
        if place is None:
            continue
        await session.execute(
            text("INSERT INTO places (id, name_en, name_pt, kind, lon, lat) VALUES (:i, :e, :p, :k, :lon, :lat)"),
            {
                "i": place.id,
                "e": place.name_en,
                "p": place.name_pt,
                "k": place.kind,
                "lon": place.lon,
                "lat": place.lat,
            },
        )
        if place.verses:
            await session.execute(
                text(
                    "INSERT INTO place_verses (place_id, book_id, chapter, verse) SELECT :i, u.b, u.c, u.v "
                    "FROM unnest(CAST(:b AS int[]), CAST(:c AS int[]), CAST(:v AS int[])) AS u(b, c, v)"
                ),
                {
                    "i": place.id,
                    "b": [v[0] for v in place.verses],
                    "c": [v[1] for v in place.verses],
                    "v": [v[2] for v in place.verses],
                },
            )
        count += 1
    return count
