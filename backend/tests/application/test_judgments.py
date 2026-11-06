import pytest

from app.application.judgments.service import JudgmentService, sentence_after, triage_block
from tests.judge_fakes import FakeJudge


async def test_triage_maps_answers() -> None:
    judge = FakeJudge(
        nouls={"crise": 0.86}, choices={"momento": ("pecado_arrependimento", 0.87)}, scores={"angustia": (2.98, 0.9)}
    )
    triage = await JudgmentService(judge).triage("gastei o aluguel apostando")
    assert triage is not None and triage.crisis == 0.86 and triage.moment == "pecado_arrependimento"
    assert triage.distress == 2.98 and judge.calls[0]["state"] == {"mensagem": "gastei o aluguel apostando"}


def test_triage_block_format() -> None:
    from app.application.judgments.service import Triage

    block = triage_block(Triage(0.9, "financas", 0.8, 2.4))
    assert block == "[Triagem automática: momento=financas; angústia=2.4/3; risco_à_vida=alto]"
    assert "risco_à_vida=baixo" in triage_block(Triage(0.1, "estudo", 0.9, 0.2))


async def test_guard_flags_above_threshold() -> None:
    judge = FakeJudge(nouls={"prosperidade": 0.9, "investimento": 0.2, "condenacao": 0.71})
    flags = await JudgmentService(judge).guard_issues("resposta")
    assert [f["kind"] for f in flags] == ["teologia_prosperidade", "teologia_condenacao"]


async def test_fidelity_only_flags_confident_contradictions() -> None:
    judge = FakeJudge(choices={"relacao": ("contradiz", 0.92)})
    issues = await JudgmentService(judge).fidelity([("[[Fp 4:6]]", "texto", "Deus promete pagar suas dívidas.")])
    assert [(i.marker, i.claim) for i in issues] == [("[[Fp 4:6]]", "Deus promete pagar suas dívidas.")]
    weak = FakeJudge(choices={"relacao": ("contradiz", 0.6)})
    assert await JudgmentService(weak).fidelity([("m", "t", "c" * 30)]) == []
    support = FakeJudge(choices={"relacao": ("apoia", 0.99)})
    assert await JudgmentService(support).fidelity([("m", "t", "c" * 30)]) == []


def test_sentence_after_marker() -> None:
    assert sentence_after(" Aqui Paulo pede oração. Depois outra coisa.") == "Aqui Paulo pede oração."
    assert sentence_after("\n\nNa prática, entregue tudo a Deus! E siga.") == "Na prática, entregue tudo a Deus!"
    assert sentence_after(", e") == ""


@pytest.mark.parametrize("text", ["meu CPF é 123.456.789-09", "cartão 4111 1111 1111 1111", "cpf 12345678909"])
async def test_sensitive_by_regex_without_calling_jev(text: str) -> None:
    judge = FakeJudge()
    assert await JudgmentService(judge).contains_sensitive_data(text) is True
    assert judge.calls == []


async def test_sensitive_by_jev() -> None:
    assert (
        await JudgmentService(FakeJudge(nouls={"sensivel": 0.9})).contains_sensitive_data("minha senha é peixe") is True
    )
    assert (
        await JudgmentService(FakeJudge(nouls={"sensivel": 0.1})).contains_sensitive_data("tenho dois filhos") is False
    )


async def test_everything_degrades_without_judge() -> None:
    for service in (JudgmentService(None), JudgmentService(FakeJudge(fail=True))):
        assert await service.triage("x") is None
        assert await service.guard_issues("x") == []
        assert await service.fidelity([("m", "t", "c" * 30)]) == []
        assert await service.contains_sensitive_data("tenho dois filhos") is False
        assert await service.contains_sensitive_data("cpf 123.456.789-09") is True
