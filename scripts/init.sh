#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/server/requirements.txt" ]; then
  ROOT_DIR="$SCRIPT_DIR"
else
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  "$PYTHON_BIN" -m venv .venv
fi

if [ ! -x ".venv/bin/python" ]; then
  echo ".venv/bin/python not found. Remove .venv and rerun init." >&2
  exit 1
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
