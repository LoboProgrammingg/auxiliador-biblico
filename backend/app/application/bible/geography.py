"""Recorte da geografia física para o quadro de um mapa (os lugares bíblicos vêm de outra base)."""

from dataclasses import dataclass
from typing import Any

from app.domain.bible.geometry import clamp, simplify
from app.domain.bible.repositories import BibleRepository

MARGIN = 1.0
DETAIL = 700
SOURCE = "Natural Earth (domínio público)"


@dataclass(frozen=True)
class BBox:
    west: float
    south: float
    east: float
    north: float


async def geography_for(repo: BibleRepository, box: BBox) -> dict[str, Any]:
    wide = (box.west - MARGIN, box.south - MARGIN, box.east + MARGIN, box.north + MARGIN)
    tolerance = max(box.east - box.west, box.north - box.south) / DETAIL
    features = []
    for kind, name, points in await repo.geo_features(*wide):
        clipped = simplify(clamp([(float(x), float(y)) for x, y in points], wide), tolerance)
        if len(clipped) >= 2:
            features.append({"kind": kind, "name": name, "points": clipped})
    return {"bbox": [box.west, box.south, box.east, box.north], "features": features, "source": SOURCE}
