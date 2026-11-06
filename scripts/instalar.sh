#!/usr/bin/env bash
# Instala o Auxiliador Bíblico nesta máquina (Linux/macOS). Idempotente: pode rodar de novo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Falta instalar: $1 ($2)"; exit 1; }; }
need docker "https://docs.docker.com/get-docker/"
need uv "https://docs.astral.sh/uv/"
need claude "Claude Code: https://code.claude.com — depois rode 'claude' uma vez para entrar na conta"

if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i.bak "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 16)/" .env && rm -f .env.bak
  PW="$(sed -n 's/^POSTGRES_PASSWORD=//p' .env)"
  sed -i.bak "s#biblia:SENHA@#biblia:${PW}@#g" .env && rm -f .env.bak
  echo "Criei o .env. Preencha VOYAGE_API_KEY (obrigatória) e, se quiser, TYPESAFE_API_KEY e SERPER_API_KEY."
  echo "Depois rode este script de novo."
  exit 0
fi
grep -q '^VOYAGE_API_KEY=.\+' .env || { echo "Preencha VOYAGE_API_KEY no .env (MongoDB Atlas > AI Model APIs)."; exit 1; }

echo "1/4 Banco de dados (Postgres + pgvector)…"
docker compose up -d db
until [[ "$(docker inspect -f '{{.State.Health.Status}}' auxiliador-biblico-db-1 2>/dev/null)" == "healthy" ]]; do sleep 2; done

echo "2/4 Backend…"
(cd backend && uv sync --frozen && uv run alembic upgrade head)

echo "3/4 Baixando a Bíblia, o original e as referências; gerando embeddings (retomável)…"
(cd backend && uv run python -m app.infrastructure.ingestion all)

echo "4/4 Interface…"
docker compose up -d --build web

echo
echo "Pronto. Agora rode: scripts/api.sh   e abra http://127.0.0.1:3000"
