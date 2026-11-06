import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.domain.bible.errors import InvalidReference
from app.infrastructure.database.bible_repository import SqlBibleRepository


@pytest.fixture
def passages(bible_db: AsyncSession) -> PassageService:
    return PassageService(SqlBibleRepository(bible_db))


async def test_resolve_valid_range(passages: PassageService) -> None:
    p = await passages.resolve("Fp 2:2-3")
    assert p.translation == "vfl" and p.fallback_label is None
    assert [v.verse for v in p.verses] == [2, 3]
    assert p.reference == "Fp 2:2-3"


async def test_resolve_whole_chapter(passages: PassageService) -> None:
    p = await passages.resolve("Sl 2")
    assert [v.verse for v in p.verses] == [1, 2, 3, 4, 5, 6]


async def test_resolve_verse_beyond_chapter_is_invalid(passages: PassageService) -> None:
    with pytest.raises(InvalidReference):
        await passages.resolve("Jo 1:99")


async def test_resolve_nonexistent_chapter_is_invalid(passages: PassageService) -> None:
    with pytest.raises(InvalidReference):
        await passages.resolve("Jo 9:1")


async def test_resolve_range_past_chapter_end_is_invalid(passages: PassageService) -> None:
    with pytest.raises(InvalidReference):
        await passages.resolve("Sl 2:1-10")


async def test_resolve_unparseable_is_invalid(passages: PassageService) -> None:
    with pytest.raises(InvalidReference):
        await passages.resolve("Livro 3:16")


async def test_resolve_falls_back_to_nvt_when_vfl_chapter_misaligned(passages: PassageService) -> None:
    p = await passages.resolve("Jo 2:3")
    assert p.translation == "nvt" and p.requested_translation == "vfl"
    assert p.fallback_label == "NVT — VFL indisponível neste trecho"
    assert p.verses[0].text == "Texto sintético Jo 2:3"


async def test_resolve_unknown_translation_uses_primary(passages: PassageService) -> None:
    p = await passages.resolve("Fp 1:1", "xyz")
    assert p.translation == "vfl" and p.requested_translation == "vfl"


async def test_resolve_explicit_translation(passages: PassageService) -> None:
    p = await passages.resolve("Fp 1:1", "ACF")
    assert p.translation == "acf"


async def test_context_expands_within_chapter(passages: PassageService) -> None:
    p = await passages.context((await passages.resolve("Sl 2:3")).range, "vfl", radius=3)
    assert [v.verse for v in p.verses] == [1, 2, 3, 4, 5, 6]
