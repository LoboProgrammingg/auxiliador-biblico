"""Backup dos dados do usuário (conversas, memória, diário, planos).

uso: uv run python -m app.infrastructure.backup criar [--forcar] | listar | restaurar ARQUIVO
A base bíblica não entra: é grande e a ingestão a reconstrói.
"""

import argparse
import asyncio
import logging
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings

logger = logging.getLogger(__name__)
USER_TABLES = (
    "conversations",
    "messages",
    "memories",
    "daily_words",
    "prayer_requests",
    "verse_notes",
    "reading_plans",
    "plan_days_done",
)
_DAILY = re.compile(r"^biblia-(\d{4}-\d{2}-\d{2})\.dump$")
_TABLE_DATA = re.compile(r"TABLE DATA \S+ (\w+) ")


class BackupError(Exception):
    pass


def backup_name(day: date) -> str:
    return f"biblia-{day.isoformat()}.dump"


def to_prune(files: list[Path], today: date, keep_days: int) -> list[Path]:
    """Backups diários mais velhos que keep_days; arquivos com outro nome nunca são apagados."""
    oldest = today - timedelta(days=keep_days - 1)
    old = []
    for path in files:
        match = _DAILY.match(path.name)
        if match and date.fromisoformat(match.group(1)) < oldest:
            old.append(path)
    return old


def _conn_args(dsn: str) -> tuple[list[str], dict[str, str]]:
    url = make_url(dsn)
    args = ["-h", url.host or "127.0.0.1", "-p", str(url.port or 5432), "-U", url.username or "postgres"]
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    return args, env | {"PGDATABASE": url.database or ""}


async def _run(cmd: list[str], env: dict[str, str], stdin: bytes | None = None) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(stdin)
    if proc.returncode != 0:
        raise BackupError(f"{cmd[0]} falhou: {err.decode(errors='replace').strip()[:400]}")
    return out


async def _dump(dsn: str, dest: Path) -> None:
    args, env = _conn_args(dsn)
    tables = [arg for table in USER_TABLES for arg in ("-t", table)]
    part = dest.with_name(dest.name + ".part")
    await _run(["pg_dump", *args, "-Fc", "--data-only", *tables, "-f", str(part)], env)
    await asyncio.to_thread(part.replace, dest)


async def create_backup(dsn: str, directory: Path, today: date, force: bool = False) -> Path | None:
    """Um backup por dia; devolve None se o de hoje já existe."""
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)
    dest = directory / backup_name(today)
    if await asyncio.to_thread(dest.exists) and not force:
        return None
    await _dump(dsn, dest)
    return dest


def prune(directory: Path, today: date, keep_days: int) -> list[Path]:
    old = to_prune(list(directory.glob("*.dump")), today, keep_days)
    for path in old:
        path.unlink(missing_ok=True)
    return old


async def restore_backup(dsn: str, file: Path, directory: Path) -> list[str]:
    """Substitui os dados do usuário pelos do arquivo, numa transação só; antes guarda um backup de segurança."""
    args, env = _conn_args(dsn)
    listing = (await _run(["pg_restore", "--list", str(file)], env)).decode()
    tables = sorted({t for t in _TABLE_DATA.findall(listing) if t in USER_TABLES})
    if not tables:
        raise BackupError("o arquivo não tem dados do Auxiliador Bíblico")
    await asyncio.to_thread(directory.mkdir, parents=True, exist_ok=True)
    await _dump(dsn, directory / f"biblia-antes-restauracao-{datetime.now():%Y%m%d-%H%M%S}.dump")
    script = await _run(["pg_restore", "--data-only", "--disable-triggers", "-f", "-", str(file)], env)
    truncate = f"TRUNCATE {', '.join(tables)} CASCADE;\n".encode()
    await _run(
        ["psql", *args, "-q", "-v", "ON_ERROR_STOP=1", "--single-transaction", "-f", "-"], env, truncate + script
    )
    return tables


async def daily_backup_loop(interval_s: float = 3600) -> None:
    """Roda junto com a API: garante o backup do dia e apaga os com mais de N dias."""
    settings = get_settings()
    while True:
        try:
            created = await create_backup(settings.database_url, settings.backup_dir, date.today())
            removed = prune(settings.backup_dir, date.today(), settings.backup_keep_days)
            if created or removed:
                logger.info("backup: criado=%s removidos=%d", created.name if created else None, len(removed))
        except (BackupError, OSError) as exc:
            logger.warning("backup diário falhou: %s", exc)
        await asyncio.sleep(interval_s)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    criar = sub.add_parser("criar", help="cria o backup de hoje")
    criar.add_argument("--forcar", action="store_true", help="refaz o de hoje")
    sub.add_parser("listar", help="lista os backups")
    restaurar = sub.add_parser("restaurar", help="substitui os dados atuais pelos do arquivo")
    restaurar.add_argument("arquivo", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    if args.cmd == "criar":
        made = asyncio.run(create_backup(settings.database_url, settings.backup_dir, date.today(), args.forcar))
        prune(settings.backup_dir, date.today(), settings.backup_keep_days)
        print(f"Backup criado: {made}" if made else "O backup de hoje já existe (use --forcar para refazer).")
    elif args.cmd == "listar":
        for path in sorted(settings.backup_dir.glob("*.dump")):
            print(f"{path}  {path.stat().st_size // 1024} KB")
    else:
        tables = asyncio.run(restore_backup(settings.database_url, args.arquivo, settings.backup_dir))
        print(f"Restaurado: {', '.join(tables)}. Um backup do estado anterior foi guardado em {settings.backup_dir}.")


if __name__ == "__main__":
    main()
