import pytest

from app.application.judgments.crisis import detect_crisis

RISK = [
    "Eu quero me matar",
    "estou pensando em suicídio",
    "Penso em suicidar",
    "vou tirar a minha vida",
    "quero acabar com minha vida",
    "Não quero mais viver",
    "nao aguento mais viver assim",
    "Às vezes quero morrer",
    "queria estar morto",
    "seria melhor eu morrer",
    "tenho vontade de me cortar",
    "quero me machucar",
    "vou dar fim à minha vida",
    "quero sumir para sempre",
]
SAFE = [
    "Estou morrendo de rir com isso",
    "Jesus morreu por mim na cruz",
    "Quero matar a saudade da minha mãe",
    "Morro de medo de barata",
    "Estou morto de cansaço depois do trabalho",
    "Como vencer a vontade de pecar?",
    "O que a Bíblia diz sobre o suicídio de Judas?",
]


@pytest.mark.parametrize("text", RISK)
def test_detects_risk_expressions(text: str) -> None:
    assert detect_crisis(text)


@pytest.mark.parametrize("text", SAFE)
def test_ignores_everyday_expressions(text: str) -> None:
    assert not detect_crisis(text)
