#!/usr/bin/env bash
# Restaura conversas, memória, diário e planos a partir de um backup.
# uso: scripts/restaurar.sh                -> lista os backups
#      scripts/restaurar.sh ARQUIVO.dump   -> restaura (antes guarda um backup do estado atual)
set -euo pipefail
cd "$(dirname "$0")/../backend"
if [[ $# -eq 0 ]]; then
  exec uv run python -m app.infrastructure.backup listar
fi
arquivo="$(realpath "$1")"
read -r -p "Isto substitui suas conversas, memória, diário e planos pelos do arquivo. Continuar? [s/N] " ok
[[ "$ok" == "s" || "$ok" == "S" ]] || { echo "Cancelado."; exit 1; }
exec uv run python -m app.infrastructure.backup restaurar "$arquivo"
