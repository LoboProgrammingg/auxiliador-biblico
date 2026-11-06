from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.geography import BBox, geography_for
from app.domain.bible.geometry import simplify
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.ingestion.geography import load_geography, parse_features

FIXTURE = Path(__file__).parent / "fixtures" / "natural_earth_amostra.geojson"


def test_simplify_keeps_shape_and_drops_collinear_points() -> None:
    line = [(0.0, 0.0), (1.0, 0.001), (2.0, 0.0), (3.0, 1.0)]
    assert simplify(line, 0.01) == [(0.0, 0.0), (2.0, 0.0), (3.0, 1.0)]
    assert simplify([(0.0, 0.0), (1.0, 1.0)], 0.5) == [(0.0, 0.0), (1.0, 1.0)]


def test_parse_keeps_bible_lands_and_drops_modern_canals() -> None:
    items = parse_features(FIXTURE.read_text(encoding="utf-8"), "lake")
    assert [(i.name, i.kind) for i in items] == [("Sea of Galilee", "lake"), ("Jordan", "lake")]
    assert items[0].points[0] == items[0].points[-1]


async def test_geography_for_bbox_clips_and_simplifies(db_session: AsyncSession) -> None:
    await load_geography(db_session, {"lake": FIXTURE})
    geo = await geography_for(SqlBibleRepository(db_session), BBox(35.0, 31.5, 36.0, 33.0))
    names = {f["name"] for f in geo["features"]}
    assert names == {"Sea of Galilee", "Jordan"}
    for feature in geo["features"]:
        for lon, lat in feature["points"]:
            assert 33.9 <= lon <= 37.1 and 30.4 <= lat <= 34.1
    assert geo["source"].startswith("Natural Earth")
    empty = await geography_for(SqlBibleRepository(db_session), BBox(-60.0, -10.0, -59.0, -9.0))
    assert empty["features"] == []
