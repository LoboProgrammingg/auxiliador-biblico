from app.application.chat.events import ChatEvent
from evals.scoring import ItemResult, gate, parse_judge, score_events


def ev(name: str, **data: object) -> ChatEvent:
    return ChatEvent(name, dict(data))


def test_score_events_counts_failures() -> None:
    events = [
        ev("text", text="Olá "),
        ev("verse", marker="[[Fp 4:6]]", passage={"reference": "Fp 4:6"}),
        ev("invalid_reference", marker="[[Jo 3:99]]"),
        ev(
            "issues",
            items=[
                {"kind": "referencia_inexistente", "excerpt": "Jo 3:98"},
                {"kind": "citacao_nao_confere", "excerpt": "x"},
                {"kind": "interpretacao_contradiz", "excerpt": "y"},
                {"kind": "teologia_prosperidade", "excerpt": "z"},
            ],
        ),
        ev("done", message_id=1),
    ]
    m = score_events(events)
    assert (m.refs_inventadas, m.citacoes_divergentes, m.interpretacao_contradiz) == (2, 1, 1)
    assert m.teologia == 1 and m.referencias == ["Fp 4:6"] and m.erro is None and m.texto.startswith("Olá")


def test_score_events_records_error() -> None:
    assert score_events([ev("error", code="claude_code_indisponivel", message="m")]).erro == "claude_code_indisponivel"


def test_parse_judge_accepts_json_in_text() -> None:
    assert parse_judge('Segue: {"nota": 4, "justificativa": "bom"}') == (4, "bom")
    assert parse_judge('{"nota": 9, "justificativa": "x"}') is None
    assert parse_judge("sem json") is None


def item(**kw: object) -> ItemResult:
    base = dict(
        id="q",
        categoria="c",
        refs_inventadas=0,
        citacoes_divergentes=0,
        interpretacao_contradiz=0,
        teologia=0,
        nota=5,
        erro=None,
    )
    base.update(kw)
    return ItemResult(**base)  # type: ignore[arg-type]


def test_gate_passes_only_with_zero_failures_and_mean_at_least_4() -> None:
    assert gate([item(), item(nota=4)]).passou
    assert not gate([item(refs_inventadas=1)]).passou
    assert not gate([item(citacoes_divergentes=1)]).passou
    assert not gate([item(interpretacao_contradiz=1)]).passou
    assert not gate([item(nota=3), item(nota=4)]).passou
    assert not gate([item(erro="x")]).passou


def test_judge_text_includes_verse_text() -> None:
    m = score_events(
        [
            ev(
                "verse",
                marker="[[Fp 4:6]]",
                passage={"reference": "Fp 4:6", "verses": [{"n": 6, "text": "Texto sintético", "cited": True}]},
            )
        ]
    )
    assert "[Fp 4:6: Texto sintético]" in m.texto
