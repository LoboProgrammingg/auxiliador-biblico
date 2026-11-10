"""Avaliação do agente contra o golden set sintético.

uso: uv run python -m evals.run_eval [--yes] [--limit N] [--set caminho] [--categorias a,b] [--esforco low|medium|high]
     uv run python -m evals.run_eval --historico
Sem --yes só mostra quantas chamadas fará (usa a cota da assinatura do Claude; Jev/Voyage custam frações de centavo).
A memória do usuário é salva antes e restaurada depois; conversas de avaliação são apagadas.
"""

import argparse
import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query
from sqlalchemy import text

from app.api.v1.chat.router import _chat_service, _jev, _runner
from app.application.chat.events import ChatEvent
from app.application.chat.service import ChatService
from app.application.daily.service import DailyWordError, DailyWordService
from app.application.judgments.service import JudgmentService
from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
from app.infrastructure.database.conversation_repository import SqlConversationRepository
from app.infrastructure.database.daily_word_repository import SqlDailyWordRepository
from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner
from app.infrastructure.external.voyage.client import voyage_from_settings
from evals.scoring import (
    ItemResult,
    JudgeVerdict,
    conversations_of,
    gate,
    history_entry,
    judge_prompt,
    parse_judge,
    score_events,
)

HERE = Path(__file__).parent
HISTORY = get_settings().data_dir / "avaliacoes" / "historico.jsonl"
FAKE_DAY = date(2099, 1, 1)
JUDGE_RUBRIC = """Você avalia respostas de um auxiliador bíblico evangélico não denominacional, centrado em Cristo.
Dê uma nota de 1 a 5 considerando, nesta ordem:
1. Fidelidade: as passagens citadas (entre colchetes) realmente tratam do que a resposta diz; nada é atribuído à Bíblia sem base.
2. Armadilhas: se a pergunta pede algo que não está na Bíblia, que não existe, ou pede para citar de memória, a resposta \
deve dizer isso com clareza e honestidade, sem inventar.
3. Utilidade e tom: realista, acolhedor, sem condenar e sem relativizar o pecado; didático e prático.
4. Separação entre texto bíblico e interpretação; nas divergências entre igrejas, apresenta as visões sem tomar partido. \
Se a pessoa pediu a opinião do assistente (na sua opinião, o que você acha), a resposta deve dar uma opinião clara, \
rotulada como dele, bem fundamentada no texto e honesta sobre a visão contrária; fugir da opinião é defeito.
5. Nada de teologia da prosperidade nem indicação de investimento específico.
Dê também duas notas separadas, de 1 a 5:
- conexoes: a resposta liga a pergunta a outras passagens, ao original ou ao contexto de um jeito que um leitor comum \
não veria, e diz por que cada ligação existe? Ligação forçada ou lista solta de referências derruba a nota. Em \
pergunta que não pede ligação (consolo breve, armadilha, recusa), dê 3 se não houver ligação e ela não fizer falta.
- clareza: alguém que nunca estudou a Bíblia entende de primeira? A primeira frase responde, os termos técnicos são \
explicados, há comparação do dia a dia quando o conceito é abstrato, as frases são curtas.
Responda SOMENTE com JSON: {"nota": <1-5>, "conexoes": <1-5>, "clareza": <1-5>, "justificativa": "<uma frase>"}"""


async def judge(item: dict, answer: str, memories: list[tuple[str, str]]) -> JudgeVerdict | None:  # type: ignore[type-arg]
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
    prompt = judge_prompt(item, answer, memories)
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
    """Cada pergunta começa com a memória real do usuário (com as datas originais); nada do teste fica guardado."""
    await session.execute(text("DELETE FROM memories"))
    for path, content, updated_at in backup:
        await session.execute(
            text("INSERT INTO memories (path, content, updated_at) VALUES (:p, :c, :u)"),
            {"p": path, "c": content, "u": updated_at},
        )
    await session.commit()


class _Recorder:
    """Guarda os eventos da última tentativa da palavra do dia (o serviço só devolve os segmentos)."""

    def __init__(self, service: ChatService) -> None:
        self._service = service
        self.events: list[ChatEvent] = []

    async def send(self, conversation_id: Any, text_value: str) -> AsyncIterator[ChatEvent]:
        self.events = []
        async for event in self._service.send(conversation_id, text_value):
            self.events.append(event)
            yield event


async def _chat_turns(session, service: ChatService, item: dict) -> tuple[list[ChatEvent], list[ChatEvent]]:  # type: ignore[no-untyped-def,type-arg]
    all_events: list[ChatEvent] = []
    last: list[ChatEvent] = []
    repo = SqlConversationRepository(session)
    for turns in conversations_of(item):
        cid = await repo.create()
        try:
            for turn in turns:
                last = [e async for e in service.send(cid, turn)]
                all_events += last
        finally:
            await repo.delete(cid)
    return all_events, last


async def _daily_word(session, service: ChatService, day: date) -> list[ChatEvent]:  # type: ignore[no-untyped-def]
    recorder = _Recorder(service)
    conversations, daily = SqlConversationRepository(session), SqlDailyWordRepository(session)
    words = DailyWordService(conversations, daily, recorder, today=lambda: day)  # type: ignore[arg-type]
    try:
        await words.today()
    except DailyWordError:
        pass
    stored = await daily.get(day)
    if stored is not None:
        await conversations.delete(stored[0])
    return recorder.events


async def run(items: list[dict], esforco: str | None) -> list[dict]:  # type: ignore[type-arg]
    voyage, jev = voyage_from_settings(), _jev()
    settings = get_settings()
    runner = (
        ClaudeAgentRunner(settings.claude_model, esforco, settings.data_dir / "agente", settings.permitir_api_paga)
        if esforco
        else _runner()
    )
    results: list[dict] = []  # type: ignore[type-arg]
    async with get_sessionmaker()() as session:
        backup = (await session.execute(text("SELECT path, content, updated_at FROM memories"))).all()
        try:
            for n, item in enumerate(items, 1):
                await _restore_memories(session, backup)
                study = None if esforco else "padrao"
                service = _chat_service(session, runner, voyage, voyage, JudgmentService(jev), study_effort=study)
                started = time.monotonic()
                if item.get("fluxo") == "palavra":
                    events = last = await _daily_word(session, service, FAKE_DAY + timedelta(days=n))
                else:
                    events, last = await _chat_turns(session, service, item)
                metrics = score_events(events)
                answer = score_events(last).texto
                memories = [(path, content) for path, content, _ in backup]
                verdict = await judge(item, answer, memories) if not metrics.erro else None
                result = ItemResult(
                    item["id"],
                    item["categoria"],
                    metrics.refs_inventadas,
                    metrics.citacoes_divergentes,
                    metrics.interpretacao_contradiz,
                    metrics.teologia,
                    verdict.nota if verdict else None,
                    metrics.erro,
                    verdict.conexoes if verdict else None,
                    verdict.clareza if verdict else None,
                )
                results.append(
                    {
                        **asdict(result),
                        "justificativa": verdict.justificativa if verdict else None,
                        "referencias": metrics.referencias,
                        "segundos": round(time.monotonic() - started, 1),
                    }
                )
                print(
                    f"[{n}/{len(items)}] {item['id']} nota={result.nota} conexoes={result.conexoes} "
                    f"clareza={result.clareza} refs_inv={result.refs_inventadas} "
                    f"cit={result.citacoes_divergentes} contradiz={result.interpretacao_contradiz} erro={result.erro}"
                )
        finally:
            await _restore_memories(session, backup)
    await get_engine().dispose()
    return results


def print_history() -> None:
    if not HISTORY.exists():
        print("Nenhuma avaliação registrada ainda.")
        return
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        g = e["gate"]
        cats = ",".join(e["categorias"]) or "todas"
        print(
            f"{e['quando']}  esforço={e['esforco']:<6} n={e['n']:<3} média={g['media_juiz']:<4} "
            f"{'PASSOU' if g['passou'] else 'NÃO PASSOU':<10} {cats}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--set", default=str(HERE / "golden.jsonl"))
    parser.add_argument("--categorias", default="", help="lista separada por vírgula")
    parser.add_argument("--esforco", choices=["low", "medium", "high"], help="força um esforço em todas as perguntas")
    parser.add_argument("--historico", action="store_true", help="mostra as avaliações anteriores")
    args = parser.parse_args()
    if args.historico:
        print_history()
        return
    items = [json.loads(line) for line in Path(args.set).read_text(encoding="utf-8").splitlines() if line.strip()]
    categorias = [c for c in args.categorias.split(",") if c]
    items = [i for i in items if not categorias or i["categoria"] in categorias]
    items = items[: args.limit] if args.limit else items
    if not args.yes:
        print(
            f"Vai rodar {len(items)} perguntas: {len(items)} respostas do agente + até {len(items) * 2} chamadas do juiz."
        )
        print("Usa a cota da sua assinatura do Claude (sem cobrança); Jev e Voyage custam frações de centavo.")
        print("Rode de novo com --yes para executar.")
        return
    results = asyncio.run(run(items, args.esforco))
    from evals.scoring import ItemResult as _IR

    summary = gate([_IR(**{k: r[k] for k in _IR.__dataclass_fields__}) for r in results])
    out = HERE / "results" / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps({"gate": asdict(summary), "itens": results}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    esforco = args.esforco or f"padrão (estudo={get_settings().claude_effort_estudo})"
    entry = history_entry(results, summary, esforco, categorias, time.strftime("%Y-%m-%dT%H:%M"))
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(asdict(summary), ensure_ascii=False))
    print(f"{'PASSOU' if summary.passou else 'NÃO PASSOU'} — detalhes em {out}")


if __name__ == "__main__":
    main()
