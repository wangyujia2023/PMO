#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r server/requirements.txt

if [ -d "frontend" ]; then
  cd "$ROOT_DIR/frontend"
  npm install
fi

cd "$ROOT_DIR"
.venv/bin/python - <<'PY'
from server.schema import SCHEMA_SQL
from server.services.repository import ProjectRepository

ProjectRepository().init_schema(SCHEMA_SQL)
print("MySQL schema initialized")
PY

echo "Init done"
