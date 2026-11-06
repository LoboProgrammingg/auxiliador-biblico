import pytest

from app.api.v1.chat.router import _chat_service, _runner
from app.core.db import get_sessionmaker
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.external.voyage.client import voyage_from_settings

pytestmark = pytest.mark.live


async def test_agent_answers_with_verified_card() -> None:
    voyage = voyage_from_settings()
    async with get_sessionmaker()() as session:
        cid = await SqlConversationRepository(session).create()
        events = [
            e async for e in _chat_service(session, _runner(), voyage, voyage).send(cid, "Me fale de Filipenses 4:6")
        ]
        await SqlConversationRepository(session).delete(cid)
    names = [e.name for e in events]
    print(names)
    assert "error" not in names, [e.data for e in events if e.name == "error"]
    verses = [e.data["passage"]["reference"] for e in events if e.name == "verse"]
    assert any(ref.startswith("Fp 4:6") for ref in verses), verses
    assert not any(e.name == "invalid_reference" for e in events)
    issues = next(e for e in events if e.name == "issues").data["items"]
    print("ISSUES", issues)
    prose = "".join(e.data["text"] for e in events if e.name == "text")
    for item in issues:
        i = prose.find(item["excerpt"][:30])
        print("CTX", prose[max(0, i - 200) : i + 250])
    assert issues == []
