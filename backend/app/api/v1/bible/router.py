from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_bible_repository, get_passage_service, get_search_service
from app.api.v1.bible.schemas import (
    CompareItem,
    CompareOut,
    CrossRefItem,
    CrossRefOut,
    OriginalOut,
    PassageOut,
    SearchOut,
    VerseOut,
    WordOut,
)
from app.application.bible.illustrations import genealogy, route, word_profile
from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.domain.bible.errors import InvalidReference
from app.domain.bible.references import format_reference
from app.domain.bible.repositories import BibleRepository

router = APIRouter(prefix="/bible", tags=["bible"])
Ref = Annotated[str, Query(min_length=2, max_length=60)]


def _not_found(ref: str) -> HTTPException:
    return HTTPException(status_code=404, detail="referência não encontrada", headers={"X-Ref": ref[:60]})


@router.get("/passage", response_model=PassageOut)
async def passage(
    ref: Ref,
    passages: Annotated[PassageService, Depends(get_passage_service)],
    translation: Annotated[str | None, Query(max_length=12)] = None,
    context: Annotated[int, Query(ge=0, le=5)] = 0,
) -> PassageOut:
    try:
        cited = await passages.resolve(ref, translation)
        if context == 0:
            return PassageOut.build(cited)
        wide = await passages.context(cited.range, cited.requested_translation, radius=context)
    except InvalidReference as exc:
        raise _not_found(ref) from exc
    return PassageOut.build(wide, (cited.verses[0].verse, cited.verses[-1].verse))


@router.get("/compare", response_model=CompareOut)
async def compare(
    ref: Ref,
    passages: Annotated[PassageService, Depends(get_passage_service)],
    repo: Annotated[BibleRepository, Depends(get_bible_repository)],
    translations: Annotated[str, Query(max_length=200)] = "vfl,acf,nvt",
) -> CompareOut:
    try:
        base = await passages.resolve(ref)
    except InvalidReference as exc:
        raise _not_found(ref) from exc
    names = await repo.translation_names()
    items: list[CompareItem] = []
    for code in [c.strip().lower() for c in translations.split(",") if c.strip()][:18]:
        if code not in names:
            continue
        if not await repo.chapter_ok(base.range.book_id, base.range.chapter, code):
            items.append(
                CompareItem(
                    translation=code,
                    name=names[code],
                    verses=None,
                    note="numeração deste capítulo não confere nesta tradução",
                )
            )
            continue
        verses = await repo.get_verses(base.range, code)
        items.append(
            CompareItem(translation=code, name=names[code], verses=[VerseOut(n=v.verse, text=v.text) for v in verses])
        )
    return CompareOut(reference=base.reference, items=items)


@router.get("/original", response_model=OriginalOut)
async def original(
    ref: Ref,
    passages: Annotated[PassageService, Depends(get_passage_service)],
    repo: Annotated[BibleRepository, Depends(get_bible_repository)],
) -> OriginalOut:
    try:
        base = await passages.resolve(ref)
    except InvalidReference as exc:
        raise _not_found(ref) from exc
    words = await repo.original_words(base.range)
    lexicon = await repo.lexicon([w.strong for w in words])
    out = [
        WordOut(
            **w.__dict__,
            lemma=lexicon[w.strong].lemma if w.strong in lexicon else None,
            lexicon_gloss=lexicon[w.strong].gloss if w.strong in lexicon else None,
        )
        for w in words
    ]
    return OriginalOut(reference=base.reference, words=out)


@router.get("/cross-references", response_model=CrossRefOut)
async def cross_references(
    ref: Ref,
    passages: Annotated[PassageService, Depends(get_passage_service)],
    repo: Annotated[BibleRepository, Depends(get_bible_repository)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> CrossRefOut:
    try:
        base = await passages.resolve(ref)
    except InvalidReference as exc:
        raise _not_found(ref) from exc
    r = base.range
    refs = await repo.cross_references(r.book_id, r.chapter, r.verse_start or 1, limit)
    return CrossRefOut(
        reference=base.reference,
        items=[CrossRefItem(reference=format_reference(c.target), votes=c.votes) for c in refs],
    )


@router.get("/search", response_model=SearchOut)
async def search(
    q: Annotated[str, Query(min_length=2, max_length=300)],
    service: Annotated[SearchService, Depends(get_search_service)],
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> SearchOut:
    return SearchOut(items=[PassageOut.build(p) for p in await service.search(q, limit)])


def _illustration(data: dict[str, Any] | None) -> dict[str, Any]:
    if data is None:
        raise HTTPException(status_code=404, detail="sem dados para esta ilustração")
    return data


End = Annotated[int | None, Query(ge=1, le=150)]


@router.get("/genealogy")
async def genealogy_route(
    ref: Ref, repo: Annotated[BibleRepository, Depends(get_bible_repository)], fim: End = None
) -> dict[str, Any]:
    try:
        return _illustration(await genealogy(repo, ref, fim))
    except InvalidReference as exc:
        raise _not_found(ref) from exc


@router.get("/route")
async def route_route(
    ref: Ref, repo: Annotated[BibleRepository, Depends(get_bible_repository)], fim: End = None
) -> dict[str, Any]:
    try:
        return _illustration(await route(repo, ref, fim))
    except InvalidReference as exc:
        raise _not_found(ref) from exc


@router.get("/word-profile")
async def word_profile_route(
    strong: Annotated[str, Query(pattern=r"^[HG]\d{1,5}[A-Za-z]?$")],
    repo: Annotated[BibleRepository, Depends(get_bible_repository)],
) -> dict[str, Any]:
    return _illustration(await word_profile(repo, strong))
