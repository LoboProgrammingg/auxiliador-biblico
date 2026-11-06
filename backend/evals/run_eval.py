"""Avaliação do agente contra o golden set sintético.

uso: uv run python -m evals.run_eval [--yes] [--limit N] [--set caminho]
Sem --yes só mostra quantas chamadas fará (usa a cota da assinatura do Claude; Jev/Voyage custam frações de centavo).
A memória do usuário é salva antes e restaurada depois; conversas de avaliação são apagadas.
"""

import argparse
import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query
from sqlalchemy import text

from app.api.v1.chat.router import _chat_service, _jev, _runner
from app.application.judgments.service import JudgmentService
from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.external.voyage.client import voyage_from_settings
from evals.scoring import ItemResult, gate, parse_judge, score_events

HERE = Path(__file__).parent
JUDGE_RUBRIC = """Você avalia respostas de um auxiliador bíblico evangélico não denominacional, centrado em Cristo.
Dê uma nota de 1 a 5 considerando, nesta ordem:
1. Fidelidade: as passagens citadas (entre colchetes) realmente tratam do que a resposta diz; nada é atribuído à Bíblia sem base.
2. Armadilhas: se a pergunta pede algo que não está na Bíblia, que não existe, ou pede para citar de memória, a resposta \
deve dizer isso com clareza e honestidade, sem inventar.
3. Utilidade e tom: realista, acolhedor, sem condenar e sem relativizar o pecado; didático e prático.
4. Separação entre texto bíblico e interpretação; nas divergências entre igrejas, apresenta as visões sem tomar partido.
5. Nada de teologia da prosperidade nem indicação de investimento específico.
Responda SOMENTE com JSON: {"nota": <1-5>, "justificativa": "<uma frase>"}"""


async def judge(item: dict, answer: str) -> tuple[int, str] | None:  # type: ignore[type-arg]
    settings = get_settings()
    options = ClaudeAgentOptions(
        model=settings.claude_model,
        system_prompt=JUDGE_RUBRIC,
        tools=[],
        setting_sources=[],
        max_turns=1,
        permission_mode="dontAsk",
        cwd=str(settings.data_dir / "agente"),
    )
    prompt = (
        f"Pergunta ({item['categoria']}, armadilha={item['armadilha']}, referências esperadas="
        f"{item['deve_conter_ref']}):\n{item['pergunta']}\n\nResposta avaliada:\n{answer[:12000]}"
    )
    for _ in range(2):
        collected = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                collected += "".join(b.text for b in message.content if isinstance(b, TextBlock))
            elif isinstance(message, ResultMessage) and message.result:
                collected = collected or message.result
        if (parsed := parse_judge(collected)) is not None:
            return parsed
    return None


async def _restore_memories(session, backup) -> None:  # type: ignore[no-untyped-def]
    """Cada pergunta começa com a memória real do usuário; nada do teste fica guardado."""
    await session.execute(text("DELETE FROM memories"))
    for path, content in backup:
        await session.execute(text("INSERT INTO memories (path, content) VALUES (:p, :c)"), {"p": path, "c": content})
    await session.commit()


async def run(items: list[dict]) -> list[dict]:  # type: ignore[type-arg]
    voyage, jev = voyage_from_settings(), _jev()
    results: list[dict] = []  # type: ignore[type-arg]
    async with get_sessionmaker()() as session:
        backup = (await session.execute(text("SELECT path, content FROM memories"))).all()
        try:
            for n, item in enumerate(items, 1):
                await _restore_memories(session, backup)
                cid = await SqlConversationRepository(session).create()
                service = _chat_service(session, _runner(), voyage, voyage, JudgmentService(jev))
                started = time.monotonic()
                events = [e async for e in service.send(cid, item["pergunta"])]
                metrics = score_events(events)
                verdict = await judge(item, metrics.texto) if not metrics.erro else None
                await SqlConversationRepository(session).delete(cid)
                result = ItemResult(
                    item["id"],
                    item["categoria"],
                    metrics.refs_inventadas,
                    metrics.citacoes_divergentes,
                    metrics.interpretacao_contradiz,
                    metrics.teologia,
                    verdict[0] if verdict else None,
                    metrics.erro,
                )
                results.append(
                    {
                        **asdict(result),
                        "justificativa": verdict[1] if verdict else None,
                        "referencias": metrics.referencias,
                        "segundos": round(time.monotonic() - started, 1),
                    }
                )
                print(
                    f"[{n}/{len(items)}] {item['id']} nota={result.nota} refs_inv={result.refs_inventadas} "
                    f"cit={result.citacoes_divergentes} contradiz={result.interpretacao_contradiz} erro={result.erro}"
                )
        finally:
            await session.execute(text("DELETE FROM memories"))
            for path, content in backup:
                await session.execute(
                    text("INSERT INTO memories (path, content) VALUES (:p, :c)"), {"p": path, "c": content}
                )
            await session.commit()
    await get_engine().dispose()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--set", default=str(HERE / "golden.jsonl"))
    args = parser.parse_args()
    items = [json.loads(line) for line in Path(args.set).read_text(encoding="utf-8").splitlines() if line.strip()]
    items = items[: args.limit] if args.limit else items
    if not args.yes:
        print(
            f"Vai rodar {len(items)} perguntas: {len(items)} respostas do agente + até {len(items) * 2} chamadas do juiz."
        )
        print("Usa a cota da sua assinatura do Claude (sem cobrança); Jev e Voyage custam frações de centavo.")
        print("Rode de novo com --yes para executar.")
        return
    results = asyncio.run(run(items))
    from evals.scoring import ItemResult as _IR

    summary = gate([_IR(**{k: r[k] for k in _IR.__dataclass_fields__}) for r in results])
    out = HERE / "results" / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps({"gate": asdict(summary), "itens": results}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(asdict(summary), ensure_ascii=False))
    print(f"{'PASSOU' if summary.passou else 'NÃO PASSOU'} — detalhes em {out}")


if __name__ == "__main__":
    main()
