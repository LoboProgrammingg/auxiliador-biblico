import pytest

from app.application.judgments.service import JudgmentService
from app.core.config import get_settings
from app.infrastructure.external.typesafe.client import jev_from_settings

pytestmark = [pytest.mark.live, pytest.mark.skipif(not get_settings().typesafe_api_key, reason="sem TYPESAFE_API_KEY")]


async def test_crisis_detected() -> None:
    triage = await JudgmentService(jev_from_settings()).triage(
        "Gastei o dinheiro do aluguel apostando e menti pra minha esposa. Às vezes penso que seria melhor sumir."
    )
    assert triage is not None and triage.crisis >= 0.5


async def test_prosperity_promise_is_not_supported_by_text() -> None:
    from app.application.judgments.questions import FIDELITY

    service = JudgmentService(jev_from_settings())
    from tests.live.test_embedding_sanity import _verse

    verse = await _verse(50, 4, 6)
    answers = await service._ask(
        {"versiculo": verse, "afirmacao": "Este versículo promete que Deus vai pagar todas as suas dívidas."},
        dict(FIDELITY),
    )
    assert answers is not None and answers.choices["relacao"][0] in ("contradiz", "nao_trata")
