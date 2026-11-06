"""Geografia física (costas, lagos, rios) do Natural Earth, domínio público, recortada para as terras bíblicas."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bible.geometry import Point, clamp, simplify

NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
NE_FILES = {"land": "ne_10m_land", "lake": "ne_10m_lakes", "river": "ne_10m_rivers_lake_centerlines"}
WORLD = (8.0, 20.0, 52.0, 44.0)
MODERN = {"Suez Canal", "Ismailiya Canal"}
TOLERANCE = 0.004


@dataclass(frozen=True)
class GeoRow:
    kind: str
    name: str | None
    points: list[Point]


def _intersects(points: list[Point], box: tuple[float, float, float, float]) -> bool:
    w, s, e, n = box
    return any(w <= lon <= e and s <= lat <= n for lon, lat in points)


def _rings(geometry: dict[str, Any]) -> list[list[Point]]:
    kind, coords = geometry["type"], geometry["coordinates"]
    if kind == "Polygon":
        rings = coords
    elif kind == "MultiPolygon":
        rings = [ring for polygon in coords for ring in polygon]
    elif kind == "LineString":
        rings = [coords]
    elif kind == "MultiLineString":
        rings = coords
    else:
        rings = []
    return [[(float(p[0]), float(p[1])) for p in ring] for ring in rings]


def parse_features(content: str, kind: str) -> list[GeoRow]:
    rows: list[GeoRow] = []
    for feature in json.loads(content)["features"]:
        name = (feature.get("properties") or {}).get("name")
        if name in MODERN:
            continue
        for ring in _rings(feature["geometry"]):
            if not _intersects(ring, WORLD):
                continue
            points = simplify(clamp(ring, WORLD), TOLERANCE)
            if len(points) >= 2:
                rows.append(GeoRow(kind, name, points))
    return rows


async def load_geography(session: AsyncSession, paths: dict[str, Path]) -> int:
    await session.execute(text("DELETE FROM geo_features"))
    count = 0
    for kind, path in paths.items():
        for row in parse_features(path.read_text(encoding="utf-8"), kind):
            lons, lats = [p[0] for p in row.points], [p[1] for p in row.points]
            await session.execute(
                text(
                    "INSERT INTO geo_features (kind, name, points, min_lon, min_lat, max_lon, max_lat) "
                    "VALUES (:k, :n, CAST(:p AS jsonb), :w, :s, :e, :nn)"
                ),
                {
                    "k": row.kind,
                    "n": row.name,
                    "p": json.dumps(row.points),
                    "w": min(lons),
                    "s": min(lats),
                    "e": max(lons),
                    "nn": max(lats),
                },
            )
            count += 1
    return count
