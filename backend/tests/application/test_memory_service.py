import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.memory.service import MemoryService
from app.domain.memory.errors import InvalidMemoryContent, InvalidMemoryTopic
from app.domain.memory.repositories import normalize_topic
from app.infrastructure.database.memory_repository import SqlMemoryRepository


@pytest.fixture
def memory(db_session: AsyncSession) -> MemoryService:
    return MemoryService(SqlMemoryRepository(db_session))


def test_normalize_topic() -> None:
    assert normalize_topic("Situação Financeira") == "situacao-financeira"
    assert normalize_topic("  plano-ansiedade  ") == "plano-ansiedade"


@pytest.mark.parametrize("topic", ["", "   ", "../x", "a" * 61, "///"])
def test_invalid_topic_rejected(topic: str) -> None:
    with pytest.raises(InvalidMemoryTopic):
        normalize_topic(topic)


async def test_save_and_list(memory: MemoryService) -> None:
    assert await memory.save("Situação Financeira", "Dívida no cartão; quer sair do vermelho.") == "situacao-financeira"
    items = await memory.list_all()
    assert [(i.topic, i.content) for i in items] == [
        ("situacao-financeira", "Dívida no cartão; quer sair do vermelho.")
    ]


async def test_append_adds_dated_line(memory: MemoryService) -> None:
    await memory.save("oracao", "Pedidos de oração:")
    await memory.append("oracao", "pela saúde da mãe")
    content = next(i.content for i in await memory.list_all() if i.topic == "oracao")
    lines = content.splitlines()
    assert lines[0] == "Pedidos de oração:" and lines[1].startswith("- 20") and lines[1].endswith(": pela saúde da mãe")


async def test_append_creates_topic_when_missing(memory: MemoryService) -> None:
    await memory.append("novo", "primeira nota")
    assert len(await memory.list_all()) == 1


async def test_content_limit(memory: MemoryService) -> None:
    with pytest.raises(InvalidMemoryContent):
        await memory.save("x", "a" * 4001)
    with pytest.raises(InvalidMemoryContent):
        await memory.save("x", "   ")


async def test_forget(memory: MemoryService) -> None:
    await memory.save("x", "y")
    assert await memory.forget("x") is True
    assert await memory.forget("x") is False
    assert await memory.list_all() == []


async def test_append_does_not_duplicate_date_written_by_model(memory: MemoryService) -> None:
    await memory.append("estudos", "2026-11-06: Pediu estudo de Filipenses")
    content = next(i.content for i in await memory.list_all() if i.topic == "estudos")
    assert content.count("2026-11-06") <= 1 and content.endswith(": Pediu estudo de Filipenses")
