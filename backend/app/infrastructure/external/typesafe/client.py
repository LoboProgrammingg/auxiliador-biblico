import logging
from typing import Any

from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score, TypeSafeError

from app.application.judgments.ports import ChoiceQ, JudgeAnswers, JudgeUnavailable, NoulQ, Question

logger = logging.getLogger(__name__)


def _to_sdk(question: Question) -> Any:
    if isinstance(question, NoulQ):
        return Noul(instructions=question.instructions)
    if isinstance(question, ChoiceQ):
        return Choice(instructions=question.instructions, criteria=question.criteria)
    return Score(instructions=question.instructions, criteria=question.criteria)


class JevJudge:
    """Julgamentos rápidos do Jev (TypeSafe). Só a contagem de tokens vai para o log, nunca o conteúdo."""

    def __init__(self, api_key: str | None = None, model: str = "jev-latest", client: Any | None = None) -> None:
        self._model = model
        self._client = client or AsyncTypeSafeClient(api_key=api_key, model=model, timeout=20)

    async def ask(self, state: dict[str, Any], questions: dict[str, Question]) -> JudgeAnswers:
        try:
            response = await self._client.system_one(
                state=state, questions={k: _to_sdk(q) for k, q in questions.items()}, model=self._model
            )
        except TypeSafeError as exc:
            raise JudgeUnavailable(type(exc).__name__) from exc
        usage = getattr(response, "usage", None)
        logger.info("jev: %s perguntas, %s tokens", len(questions), getattr(usage, "input_tokens", None))
        return JudgeAnswers(
            nouls={k: float(a.noul) for k, a in response.nouls.items()},
            choices={k: (a.choice, float(a.confidence)) for k, a in response.choices.items()},
            scores={k: (float(a.score), float(a.confidence)) for k, a in response.scores.items()},
        )


def jev_from_settings() -> JevJudge | None:
    from app.core.config import get_settings

    settings = get_settings()
    return JevJudge(settings.typesafe_api_key, settings.jev_model) if settings.typesafe_api_key else None
