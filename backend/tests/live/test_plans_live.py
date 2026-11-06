import pytest

from app.core.db import get_sessionmaker
from app.domain.plans.catalog import plan_days
from app.domain.plans.themes import THEMES
from app.infrastructure.database.bible_repository import SqlBibleRepository

pytestmark = pytest.mark.live


async def test_theme_references_exist_in_real_bible() -> None:
    async with get_sessionmaker()() as session:
        repo = SqlBibleRepository(session)
        for code, theme in THEMES.items():
            for day in theme.days:
                for r in day:
                    last = await repo.last_verse(r.book_id, r.chapter_start)
                    assert last is not None, (code, r.label)
                    assert (r.verse_end or 0) <= last, (code, r.label, last)


async def test_bible_in_a_year_covers_1189_chapters() -> None:
    async with get_sessionmaker()() as session:
        sizes = await SqlBibleRepository(session).chapter_sizes()
    assert len(sizes) == 1189
    days = plan_days("biblia-1-ano", sizes)
    per_day = [sum(sizes[(r.book_id, c)] for r in d for c in range(r.chapter_start, r.chapter_end + 1)) for d in days]
    print("versículos/dia min, max:", min(per_day), max(per_day))
    assert len(days) == 365 and all(days)
