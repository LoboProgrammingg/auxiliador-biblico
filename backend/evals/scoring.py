import json
import re
from dataclasses import dataclass, field
from typing import Any

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


NEW_CONVERSATION = "---nova---"


def conversations_of(item: dict[str, Any]) -> list[list[str]]:
    """Uma pergunta simples vira uma conversa; `turnos` pode abrir conversas novas com ---nova---."""
    if "turnos" not in item:
        return [[item["pergunta"]]]
    groups: list[list[str]] = [[]]
    for turn in item["turnos"]:
        if turn == NEW_CONVERSATION:
            groups.append([])
        else:
            groups[-1].append(turn)
    return [g for g in groups if g]


def _failures(r: dict[str, Any]) -> int:
    return r["refs_inventadas"] + r["citacoes_divergentes"] + r["interpretacao_contradiz"] + (1 if r["erro"] else 0)


def history_entry(
    results: list[dict[str, Any]], summary: GateResult, esforco: str, categorias: list[str], quando: str
) -> dict[str, Any]:
    """Linha do histórico: só números (nada de texto da resposta, nem referências)."""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_cat.setdefault(r["categoria"], []).append(r)
    per_category = {}
    for cat, rows in sorted(by_cat.items()):
        notas = [r["nota"] for r in rows if r["nota"] is not None]
        per_category[cat] = {
            "n": len(rows),
            "media": round(sum(notas) / len(notas), 2) if notas else 0.0,
            "falhas": sum(_failures(r) for r in rows),
            "segundos": round(sum(r["segundos"] for r in rows) / len(rows), 1),
        }
    return {
        "quando": quando,
        "esforco": esforco,
        "categorias": categorias,
        "n": len(results),
        "gate": {"passou": summary.passou, "totais": summary.totais, "media_juiz": summary.media_juiz},
        "por_categoria": per_category,
    }


MAX_JUDGED_CHARS = 60000


def judge_prompt(item: dict[str, Any], answer: str, memories: list[tuple[str, str]]) -> str:
    """O juiz vê a resposta inteira e a memória que o assistente tinha (lembrar dela não é invenção)."""
    memory = "\n".join(f"- {topic}: {content}" for topic, content in memories) or "nenhuma"
    return (
        f"Pergunta ({item['categoria']}, armadilha={item['armadilha']}, referências esperadas="
        f"{item['deve_conter_ref']}):\n{item['pergunta']}\n\n"
        f"Memória do usuário disponível ao assistente (citar o que está aqui não é invenção):\n{memory}\n\n"
        f"Resposta avaliada:\n{answer[:MAX_JUDGED_CHARS]}"
    )
