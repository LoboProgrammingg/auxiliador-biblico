import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.external.voyage.client import voyage_from_settings
from app.infrastructure.ingestion.alignment import semantic_alignment
from app.infrastructure.ingestion.checks import check_original_coverage
from app.infrastructure.ingestion.crossrefs import load_crossrefs, read_crossref_zip
from app.infrastructure.ingestion.passages import create_passages, embed_passages
from app.infrastructure.ingestion.sources import CROSSREF_URL, STEPBIBLE_BASE, TRANSLATION_URL, download
from app.infrastructure.ingestion.stepbible import (
    LEXICON_FILES,
    WORD_FILES,
    folder_for,
    load_lexicon_file,
    load_word_file,
    parse_tagnt_line,
    parse_tahot_line,
)
from app.infrastructure.ingestion.translations import (
    INDEXED,
    REFERENCE_TRANSLATION,
    TRANSLATIONS,
    count_alignment,
    load_translation,
    parse_translation_json,
    seed_books,
)

logger = logging.getLogger(__name__)

Step = Callable[[AsyncSession], Awaitable[dict[str, Any]]]


def translation_path(code: str) -> Any:
    return get_settings().data_dir / "sources" / "translations" / f"pt_{code}.json"


async def step_download(session: AsyncSession) -> dict[str, Any]:
    for code in TRANSLATIONS:
        await download(TRANSLATION_URL.format(code=code), translation_path(code))
    return {"translations": len(TRANSLATIONS)}


async def step_translations(session: AsyncSession) -> dict[str, Any]:
    reference = parse_translation_json(translation_path(REFERENCE_TRANSLATION))
    chapters: dict[int, int] = {}
    for book_id, chapter, _, _ in reference:
        chapters[book_id] = max(chapters.get(book_id, 0), chapter)
    await seed_books(session, chapters)
    loaded: dict[str, int] = {}
    order = [REFERENCE_TRANSLATION, *[c for c in TRANSLATIONS if c != REFERENCE_TRANSLATION]]
    for code in order:
        rows = reference if code == REFERENCE_TRANSLATION else parse_translation_json(translation_path(code))
        loaded[code] = await load_translation(session, code, rows)
        logger.info("tradução %s: %s versículos", code, loaded[code])
    failed = {code: await count_alignment(session, code) for code in order}
    logger.info("capítulos reprovados por contagem: %s", failed)
    return {"verses": loaded, "count_failures": failed}


async def step_originals(session: AsyncSession) -> dict[str, Any]:
    folder = get_settings().data_dir / "sources" / "stepbible"
    for name in (*WORD_FILES, *LEXICON_FILES):
        await download(f"{STEPBIBLE_BASE}/{quote(folder_for(name))}/{quote(name)}", folder / name)
    await session.execute(text("DELETE FROM original_words"))
    await session.execute(text("DELETE FROM lexicon"))
    words = 0
    for name in WORD_FILES:
        parser = parse_tagnt_line if name.startswith("TAGNT") else parse_tahot_line
        words += await load_word_file(session, folder / name, parser)
    entries = sum([await load_lexicon_file(session, folder / name) for name in LEXICON_FILES])
    coverage = await check_original_coverage(session)
    logger.info("cobertura do original: %s", {k: len(v) for k, v in coverage.items()})
    return {
        "words": words,
        "lexicon": entries,
        **{k: v[:200] for k, v in coverage.items()},
        "totais": {k: len(v) for k, v in coverage.items()},
    }


async def step_crossrefs(session: AsyncSession) -> dict[str, Any]:
    path = await download(CROSSREF_URL, get_settings().data_dir / "sources" / "cross-references.zip")
    return await load_crossrefs(session, read_crossref_zip(path))


async def step_passages(session: AsyncSession) -> dict[str, Any]:
    embedder = voyage_from_settings()
    created: dict[str, int] = {}
    for code in INDEXED:
        existing = await session.execute(text("SELECT count(*) FROM passages WHERE translation_code = :t"), {"t": code})
        if existing.scalar_one() == 0:
            created[code] = await create_passages(session, code)
            await session.commit()
    settings = get_settings()
    embedded = {
        code: await embed_passages(session, embedder, code, tpm=settings.voyage_tpm, rpm=settings.voyage_rpm)
        for code in INDEXED
    }
    logger.info("passagens criadas %s, embeddings novos %s", created, embedded)
    return {"criadas": created, "embeddings": embedded}


async def step_alignment(session: AsyncSession) -> dict[str, Any]:
    result = {code: await semantic_alignment(session, code) for code in ("vfl", "nvt")}
    totals = await session.execute(
        text(
            "SELECT translation_code, count(*) FILTER (WHERE NOT ok) FROM chapter_alignment "
            "WHERE translation_code IN ('vfl', 'nvt') GROUP BY 1"
        )
    )
    return {"reprovados_semantico": result, "reprovados_total": dict(totals.all())}


STEPS: dict[str, Step] = {
    "download": step_download,
    "translations": step_translations,
    "originals": step_originals,
    "crossrefs": step_crossrefs,
    "passages": step_passages,
    "alignment": step_alignment,
}


async def run_step(session: AsyncSession, name: str, force: bool = False) -> dict[str, Any] | None:
    if not force:
        done = await session.execute(text("SELECT 1 FROM ingestion_checkpoints WHERE step = :s"), {"s": name})
        if done.first():
            logger.info("etapa %s já concluída (use --force para refazer)", name)
            return None
    detail = await STEPS[name](session)
    await session.execute(
        text(
            "INSERT INTO ingestion_checkpoints (step, detail) VALUES (:s, CAST(:d AS jsonb)) "
            "ON CONFLICT (step) DO UPDATE SET detail = EXCLUDED.detail, done_at = now()"
        ),
        {"s": name, "d": json.dumps(detail, ensure_ascii=False)},
    )
    await session.commit()
    return detail
