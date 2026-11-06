import pytest

from app.domain.bible.books import BOOKS
from app.domain.plans.catalog import CATALOG, Reading, plan_days, split_balanced
from app.domain.plans.themes import THEMES


def sizes_for(chapters_per_book: dict[int, int], verses: int = 20) -> dict[tuple[int, int], int]:
    return {(b, c): verses + (c % 7) * 5 for b, n in chapters_per_book.items() for c in range(1, n + 1)}


def test_split_balanced_is_contiguous_and_never_empty() -> None:
    chapters = [(1, c, s) for c, s in enumerate([10, 10, 10, 200, 10, 10, 10, 10, 10, 10], start=1)]
    days = split_balanced(chapters, 6)
    assert len(days) == 6 and all(days)
    flat = [ch for day in days for ch in day]
    assert flat == [(1, c) for c in range(1, 11)]


def test_split_balanced_balances_by_verse_count() -> None:
    chapters = [(1, c, 30) for c in range(1, 61)]
    days = split_balanced(chapters, 20)
    assert {len(d) for d in days} == {3}


def test_bible_in_a_year_covers_every_chapter_once_in_order() -> None:
    sizes = sizes_for({b.id: 3 + (b.id % 5) * 4 for b in BOOKS})
    days = plan_days("biblia-1-ano", sizes)
    assert len(days) == 365
    covered = [(r.book_id, c) for day in days for r in day for c in range(r.chapter_start, r.chapter_end + 1)]
    assert covered == sorted(sizes)


def test_gospels_in_30_days_only_gospels() -> None:
    sizes = sizes_for({b.id: 10 for b in BOOKS})
    days = plan_days("evangelhos-30", sizes)
    assert len(days) == 30
    assert {r.book_id for day in days for r in day} == {40, 41, 42, 43}


def test_reading_labels() -> None:
    assert Reading(1, 1, 3).label == "Gn 1–3"
    assert Reading(19, 23, 23).label == "Sl 23"
    assert Reading(40, 6, 6, 25, 34).label == "Mt 6:25-34"


def test_catalog_lists_every_plan_with_days() -> None:
    assert {"biblia-1-ano", "evangelhos-30", *THEMES} <= set(CATALOG)
    for code, theme in THEMES.items():
        assert CATALOG[code].days == len(theme.days) >= 7
        assert all(day for day in theme.days)


@pytest.mark.parametrize("code", sorted(THEMES))
def test_theme_plan_days_ignore_sizes(code: str) -> None:
    assert plan_days(code, {}) == THEMES[code].days


def test_fewer_chapters_than_days_gives_one_chapter_per_day() -> None:
    assert split_balanced([(1, 1, 5), (1, 2, 5)], 30) == [[(1, 1)], [(1, 2)]]
