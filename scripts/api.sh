#!/usr/bin/env bash
# Sobe a API no host (o Agent SDK usa o Claude Code logado nesta máquina).
set -euo pipefail
cd "$(dirname "$0")/../backend"
if [[ -n "${ANTHROPIC_API_KEY:-}" ]] && ! grep -q '^PERMITIR_API_PAGA=true' ../.env 2>/dev/null; then
  echo "Aviso: ANTHROPIC_API_KEY está no ambiente. O chat vai recusar para não gerar cobrança."
  echo "Remova a variável (unset ANTHROPIC_API_KEY) ou defina PERMITIR_API_PAGA=true no .env."
fi
uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
