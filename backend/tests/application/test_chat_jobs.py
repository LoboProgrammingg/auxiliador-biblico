import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat.jobs import ChatJobs
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from tests.application.test_chat_service import make_service, new_conversation
from tests.chat_fakes import FakeAgentRunner


async def test_job_survives_subscriber_cancel(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner(["Paz ", "e ", "[[Fp 2:3]]"], delay=0.02))
    cid = await new_conversation(bible_db)
    jobs = ChatJobs()
    job = jobs.start(cid, lambda: svc.send(cid, "oi"))
    assert job is not None
    stream = job.subscribe()
    first = await anext(stream)
    assert first.name == "text"
    await stream.aclose()
    await job.wait()
    messages = await SqlConversationRepository(bible_db).messages(cid)
    assert messages[-1].role == "assistant" and messages[-1].status == "ok"
    assert [s["type"] for s in messages[-1].segments] == ["text", "verse"]


async def test_second_start_is_refused_until_finished(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner(["Oi"], delay=0.02))
    cid = await new_conversation(bible_db)
    jobs = ChatJobs()
    job = jobs.start(cid, lambda: svc.send(cid, "oi"))
    assert job is not None and jobs.get(cid) is job
    assert jobs.start(cid, lambda: svc.send(cid, "de novo")) is None
    await job.wait()
    await asyncio.sleep(0)
    assert jobs.get(cid) is None


async def test_reattach_replays_running_turn(bible_db: AsyncSession) -> None:
    svc = make_service(bible_db, FakeAgentRunner(["a", "b", "c"], delay=0.02))
    cid = await new_conversation(bible_db)
    jobs = ChatJobs()
    job = jobs.start(cid, lambda: svc.send(cid, "oi"))
    assert job is not None
    stream = job.subscribe()
    await anext(stream)
    await stream.aclose()
    replay = [e.name async for e in job.subscribe()]
    assert replay[0] == "text" and replay[-1] == "done"
    assert replay == [e.name for e in job.events]
