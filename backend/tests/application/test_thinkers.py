from pathlib import Path
from typing import Any

from app.application.verification.markers import MarkerStreamProcessor, TextOut, ThinkerOut
from app.application.verification.thinkers import THINKERS, find_thinker

SKILLS = Path(__file__).resolve().parents[2] / "agente-plugin" / "skills"


def _proc() -> MarkerStreamProcessor:
    passages: Any = None  # o marcador de pensador não consulta a Bíblia
    return MarkerStreamProcessor(passages)


def test_every_catalog_thinker_is_in_the_skill_and_back() -> None:
    skill = (SKILLS / "pensadores" / "SKILL.md").read_text()
    headings = {line[4:].split(" (")[0].strip() for line in skill.splitlines() if line.startswith("### ")}
    assert {t.name for t in THINKERS} == headings
    assert len(THINKERS) >= 40


def test_find_thinker_accepts_short_names_without_accents() -> None:
    thinker = find_thinker("tomas de aquino")
    assert thinker is not None and thinker.name == "Tomás de Aquino"
    assert find_thinker("Lewis") is not None and find_thinker("Nietzsche") is not None
    assert find_thinker("Fulano de Tal") is None


async def test_thinker_marker_becomes_separate_card() -> None:
    proc = _proc()
    out = await proc.feed("Veja:\n\n[[pensador:Agostinho|Confissões|paráfrase|O coração humano vive inquieto")
    out += await proc.feed(" até descansar em Deus.]]\n\nE a Bíblia diz:")
    card = next(o for o in out if isinstance(o, ThinkerOut))
    assert card.name == "Agostinho de Hipona" and card.work == "Confissões" and card.kind == "paráfrase"
    assert card.text == "O coração humano vive inquieto até descansar em Deus."
    assert card.objection is False
    assert "".join(o.text for o in out if isinstance(o, TextOut)) == "Veja:\n\n\n\nE a Bíblia diz:"


async def test_objection_thinker_is_flagged() -> None:
    out = await _proc().feed(
        "[[pensador:Hume|Investigação sobre o entendimento humano|paráfrase|Milagres violam leis.]]"
    )
    card = out[0]
    assert isinstance(card, ThinkerOut) and card.objection is True


async def test_thinker_kind_is_forgiving_and_long_text_fits() -> None:
    proc = _proc()
    long_ok = "palavra " * 100
    for marker, kind in (
        ("[[pensador:Pascal|Pensamentos|Paráfrase|Texto.]]", "paráfrase"),
        ("[[pensador:Pascal|Pensamentos|parafrase|Texto.]]", "paráfrase"),
        ("[[pensador:Pascal|Pensamentos|CITACAO|Texto.]]", "citação"),
        (f"[[pensador: Pascal | Pensamentos | paráfrase | {long_ok}]]", "paráfrase"),
    ):
        out = await proc.feed(marker)
        assert len(out) == 1 and isinstance(out[0], ThinkerOut) and out[0].kind == kind, marker


async def test_invalid_thinker_markers_are_dropped_and_logged(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.application.verification import markers

    logged: list[str] = []
    monkeypatch.setattr(markers.logger, "warning", lambda msg, *args: logged.append(msg % args))
    proc = _proc()
    too_long = "a" * 901
    for marker in (
        "[[pensador:Fulano|Obra|paráfrase|Texto.]]",
        "[[pensador:Pascal|Só dois campos]]",
        f"[[pensador:Pascal|Pensamentos|paráfrase|{too_long}]]",
        "[[pensador:Pascal|Pensamentos|paráfrase|]]",
    ):
        assert await proc.feed(marker) == []
    assert sum("cartão de pensador descartado" in line for line in logged) == 4


async def test_long_thinker_marker_survives_streaming_in_small_chunks() -> None:
    proc = _proc()
    marker = f"[[pensador:Agostinho|A Cidade de Deus|paráfrase|{'ideia longa ' * 75}]]"
    out = []
    for i in range(0, len(marker), 7):
        out += await proc.feed(marker[i : i + 7])
    assert [type(o) for o in out] == [ThinkerOut]


async def test_thinker_marker_variants_the_model_really_writes() -> None:
    proc = _proc()
    three = await proc.feed("[[pensador:Agostinho|Enchiridion|O mal é falta de um bem.]]")
    summary_and_quote = await proc.feed(
        "[[pensador:Dostoiévski (Ivan Karamázov)|Os Irmãos Karamázov|Ivan recusa uma harmonia comprada com dor."
        "|Não é Deus que eu não aceito...]]"
    )
    for out, name, text in (
        (three, "Agostinho de Hipona", "O mal é falta de um bem."),
        (summary_and_quote, "Fiódor Dostoiévski", "Ivan recusa uma harmonia comprada com dor."),
    ):
        assert len(out) == 1 and isinstance(out[0], ThinkerOut)
        assert out[0].name == name and out[0].text == text and out[0].kind == "paráfrase"
