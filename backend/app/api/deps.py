from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.bible.passages import PassageService
from app.application.bible.search import SearchService
from app.application.chat.ports import Embedder, Reranker
from app.core.db import get_session
from app.domain.bible.repositories import BibleRepository
from app.infrastructure.database.bible_repository import SqlBibleRepository
from app.infrastructure.external.voyage.client import VoyageClient, voyage_from_settings


@lru_cache
def _voyage() -> VoyageClient:
    return voyage_from_settings(interactive=True)


def get_embedder() -> Embedder:
    return _voyage()


def get_reranker() -> Reranker:
    return _voyage()


def get_bible_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> BibleRepository:
    return SqlBibleRepository(session)


def get_passage_service(repo: Annotated[BibleRepository, Depends(get_bible_repository)]) -> PassageService:
    return PassageService(repo)


def get_search_service(
    repo: Annotated[BibleRepository, Depends(get_bible_repository)],
    passages: Annotated[PassageService, Depends(get_passage_service)],
    embedder: Annotated[Embedder, Depends(get_embedder)],
    reranker: Annotated[Reranker, Depends(get_reranker)],
) -> SearchService:
    return SearchService(repo, passages, embedder, reranker)  # type: ignore[arg-type]
