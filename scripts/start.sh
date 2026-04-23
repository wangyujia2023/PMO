#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-28823}"
FRONTEND_PORT="${FRONTEND_PORT:-28822}"

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

.venv/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

wait
