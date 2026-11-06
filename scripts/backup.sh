#!/usr/bin/env bash
# Cria agora o backup de hoje dos seus dados (a API já faz isso sozinha todo dia).
set -euo pipefail
cd "$(dirname "$0")/../backend"
exec uv run python -m app.infrastructure.backup criar "$@"
