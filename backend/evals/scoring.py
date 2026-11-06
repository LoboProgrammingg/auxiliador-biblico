import json
import re
from dataclasses import dataclass, field

from app.application.chat.events import ChatEvent

_JSON = re.compile(r"\{.*\}", re.S)
GATE_MEAN = 4.0


@dataclass
class ItemMetrics:
    refs_inventadas: int = 0
    citacoes_divergentes: int = 0
    interpretacao_contradiz: int = 0
    teologia: int = 0
    referencias: list[str] = field(default_factory=list)
    texto: str = ""
    erro: str | None = None


@dataclass(frozen=True)
class ItemResult:
    id: str
    categoria: str
    refs_inventadas: int
    citacoes_divergentes: int
    interpretacao_contradiz: int
    teologia: int
    nota: int | None
    erro: str | None


@dataclass(frozen=True)
class GateResult:
    passou: bool
    totais: dict[str, int]
    media_juiz: float


def score_events(events: list[ChatEvent]) -> ItemMetrics:
    m = ItemMetrics()
    for e in events:
        if e.name == "text":
            m.texto += str(e.data["text"])
        elif e.name == "verse":
            passage = e.data["passage"]
            m.referencias.append(str(passage["reference"]))  # type: ignore[index]
            cited = " ".join(v["text"] for v in passage.get("verses", []) if v.get("cited", True))  # type: ignore[union-attr]
            m.texto += f" [{passage['reference']}: {cited}] " if cited else f" [{passage['reference']}] "  # type: ignore[index]
        elif e.name == "invalid_reference":
            m.refs_inventadas += 1
        elif e.name == "error":
            m.erro = str(e.data["code"])
        elif e.name == "issues":
            for issue in e.data["items"]:  # type: ignore[union-attr]
                kind = issue["kind"]
                if kind == "referencia_inexistente":
                    m.refs_inventadas += 1
                elif kind == "citacao_nao_confere":
                    m.citacoes_divergentes += 1
                elif kind == "interpretacao_contradiz":
                    m.interpretacao_contradiz += 1
                elif kind.startswith("teologia_"):
                    m.teologia += 1
    return m


def parse_judge(text: str) -> tuple[int, str] | None:
    match = _JSON.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        nota, justificativa = int(data["nota"]), str(data["justificativa"])
    except (ValueError, KeyError, TypeError):
        return None
    return (nota, justificativa) if 1 <= nota <= 5 else None


def gate(results: list[ItemResult]) -> GateResult:
    totais = {
        "refs_inventadas": sum(r.refs_inventadas for r in results),
        "citacoes_divergentes": sum(r.citacoes_divergentes for r in results),
        "interpretacao_contradiz": sum(r.interpretacao_contradiz for r in results),
        "teologia": sum(r.teologia for r in results),
        "erros": sum(1 for r in results if r.erro),
    }
    notas = [r.nota for r in results if r.nota is not None]
    media = sum(notas) / len(notas) if notas else 0.0
    passou = (
        totais["refs_inventadas"] == 0
        and totais["citacoes_divergentes"] == 0
        and totais["interpretacao_contradiz"] == 0
        and totais["erros"] == 0
        and media >= GATE_MEAN
    )
    return GateResult(passou, totais, round(media, 2))
