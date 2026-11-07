from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.daily.service import DailyWordError, DailyWordService
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.daily_word_repository import SqlDailyWordRepository
from tests.application.test_chat_service import make_service
from tests.chat_fakes import FakeAgentRunner


def daily(session: AsyncSession, runner: FakeAgentRunner, day: date) -> DailyWordService:
    return DailyWordService(
        SqlConversationRepository(session),
        SqlDailyWordRepository(session),
        make_service(session, runner),
        today=lambda: day,
    )


async def test_same_word_all_day_and_new_word_next_day(bible_db: AsyncSession) -> None:
    runner = FakeAgentRunner(["Para hoje:\n", "[[Sl 2:1]]", "\nDeus cuida de você."])
    first = await daily(bible_db, runner, date(2026, 11, 6)).today()
    again = await daily(bible_db, runner, date(2026, 11, 6)).today()
    assert len(runner.calls) == 1
    assert first.reference == "Sl 2:1" and again.segments == first.segments
    assert [s["type"] for s in first.segments][:2] == ["text", "verse"]
    await daily(bible_db, runner, date(2026, 11, 7)).today()
    assert len(runner.calls) == 2
    assert "Sl 2:1" in runner.calls[1]["prompt"]


async def test_daily_conversations_hidden_from_chat_list(bible_db: AsyncSession) -> None:
    await daily(bible_db, FakeAgentRunner(["[[Sl 2:1]]"]), date(2026, 11, 6)).today()
    assert await SqlConversationRepository(bible_db).recent() == []
    kinds = await bible_db.execute(text("SELECT kind FROM conversations"))
    assert [k for (k,) in kinds] == ["palavra"]


async def test_failed_generation_is_not_saved(bible_db: AsyncSession) -> None:
    import pytest

    service = daily(bible_db, FakeAgentRunner([("done", True, "claude_code_indisponivel")]), date(2026, 11, 6))
    with pytest.raises(DailyWordError) as exc:
        await service.today()
    assert "Claude Code" in str(exc.value)
    assert await SqlDailyWordRepository(bible_db).get(date(2026, 11, 6)) is None


class SequenceRunner:
    """Primeira resposta sem passagem, segunda com passagem."""

    def __init__(self, scripts: list[list[object]]) -> None:
        self.runners = [FakeAgentRunner(s) for s in scripts]
        self.calls: list[dict[str, object]] = []

    def run(self, prompt, session_id, tools, effort=None, model=None):  # type: ignore[no-untyped-def]
        runner = self.runners[min(len(self.calls), len(self.runners) - 1)]
        self.calls.append({"prompt": prompt})
        return runner.run(prompt, session_id, tools)


async def test_retries_once_when_answer_has_no_passage(bible_db: AsyncSession) -> None:
    runner = SequenceRunner([["Registrei a passagem de hoje na sua memória."], ["[[Sl 2:1]]\nDeus cuida de você."]])
    word = await daily(bible_db, runner, date(2026, 11, 8)).today()  # type: ignore[arg-type]
    assert word.reference == "Sl 2:1" and len(runner.calls) == 2
    assert await SqlConversationRepository(bible_db).recent() == []


def test_daily_prompt_asks_for_word_first_and_no_memory_note() -> None:
    from app.application.daily.service import DAILY_PROMPT

    assert "não anote" in DAILY_PROMPT.lower() and "primeiro" in DAILY_PROMPT.lower()
