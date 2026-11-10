from app.application.chat.events import ChatEvent
from evals.scoring import ItemResult, JudgeVerdict, gate, parse_judge, score_events


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
    assert parse_judge('Segue: {"nota": 4, "justificativa": "bom"}') == JudgeVerdict(4, "bom", None, None)
    assert parse_judge('{"nota": 9, "justificativa": "x"}') is None
    assert parse_judge("sem json") is None


def test_parse_judge_reads_connections_and_clarity() -> None:
    v = parse_judge('{"nota": 4, "conexoes": 3, "clareza": 5, "justificativa": "ok"}')
    assert v == JudgeVerdict(4, "ok", 3, 5)
    assert parse_judge('{"nota": 4, "conexoes": 7, "clareza": 5, "justificativa": "ok"}') == JudgeVerdict(
        4, "ok", None, 5
    )


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


def test_conversations_of_splits_multiturn_items() -> None:
    from evals.scoring import conversations_of

    assert conversations_of({"pergunta": "oi"}) == [["oi"]]
    assert conversations_of({"turnos": ["a", "b", "---nova---", "c"]}) == [["a", "b"], ["c"]]


def test_history_entry_keeps_only_metrics() -> None:
    from evals.scoring import history_entry

    results = [
        {
            **item(categoria="financas", nota=5, conexoes=4, clareza=5).__dict__,
            "justificativa": "boa",
            "referencias": ["Fp 4:6"],
            "segundos": 3.0,
        },
        {**item(categoria="injecao", nota=4).__dict__, "justificativa": "ok", "referencias": [], "segundos": 5.0},
    ]
    entry = history_entry(results, gate([item(), item(nota=4)]), "medium", ["financas", "injecao"], "2026-11-06T13:00")
    assert entry["esforco"] == "medium" and entry["n"] == 2 and entry["gate"]["passou"]
    assert entry["por_categoria"]["financas"] == {
        "n": 1,
        "media": 5.0,
        "conexoes": 4.0,
        "clareza": 5.0,
        "falhas": 0,
        "segundos": 3.0,
    }
    assert entry["por_categoria"]["injecao"]["conexoes"] is None
    flat = str(entry)
    assert "boa" not in flat and "Fp 4:6" not in flat


def test_golden_set_is_wide_and_well_formed() -> None:
    import json
    from collections import Counter
    from pathlib import Path

    from evals.scoring import conversations_of

    lines = (Path(__file__).parents[2] / "evals" / "golden.jsonl").read_text(encoding="utf-8").splitlines()
    items = [json.loads(line) for line in lines if line.strip()]
    ids = [i["id"] for i in items]
    assert len(items) >= 150 and len(set(ids)) == len(ids)
    cats = Counter(i["categoria"] for i in items)
    for cat in ("estudo_capitulo", "palavra", "multiturno", "injecao", "armadilha_teologica"):
        assert cats[cat] >= 10, cat
    for i in items:
        assert conversations_of(i) and all(conversations_of(i))
        assert isinstance(i["armadilha"], bool)
    assert sum(1 for i in items if i.get("fluxo") == "palavra") >= 6


def test_judge_prompt_shows_memory_and_whole_long_answers() -> None:
    from evals.scoring import judge_prompt

    item = {
        "categoria": "estudo_capitulo",
        "armadilha": False,
        "deve_conter_ref": None,
        "pergunta": "Interprete Rute 1",
    }
    answer = "a" * 30000 + " FIM"
    prompt = judge_prompt(item, answer, [("situacao-financeira", "Aperto no peito com as contas.")])
    assert "Aperto no peito com as contas." in prompt and prompt.endswith("FIM")
    assert "não é invenção" in prompt
    assert "nenhuma" in judge_prompt(item, "ok", [])
