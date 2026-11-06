import argparse
import asyncio
import json

from app.core.db import get_engine, get_sessionmaker
from app.core.logging import configure_logging
from app.infrastructure.ingestion.steps import STEPS, run_step


async def main(steps: list[str], force: bool) -> None:
    async with get_sessionmaker()() as session:
        for name in steps:
            detail = await run_step(session, name, force=force)
            if detail is not None:
                print(f"[ok] {name}: {json.dumps(detail, ensure_ascii=False)}")
    await get_engine().dispose()


if __name__ == "__main__":
    configure_logging()
    parser = argparse.ArgumentParser(description="Ingestão do Auxiliador Bíblico")
    parser.add_argument("steps", nargs="*", default=["all"], help=f"etapas: all, {', '.join(STEPS)}")
    parser.add_argument("--force", action="store_true", help="refaz etapas já concluídas")
    args = parser.parse_args()
    chosen = list(STEPS) if args.steps == ["all"] else args.steps
    unknown = [s for s in chosen if s not in STEPS]
    if unknown:
        parser.error(f"etapa desconhecida: {', '.join(unknown)}")
    asyncio.run(main(chosen, args.force))
