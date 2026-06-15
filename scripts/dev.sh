#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PID=""
FRONTEND_PID=""

info() {
  printf '[dev] %s\n' "$1"
}

fail() {
  printf '[dev] ERROR: %s\n' "$1" >&2
  exit 1
}

find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    return
  fi

  if [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
    printf '%s\n' "$ROOT_DIR/backend/.venv/bin/python"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi

  fail "Python was not found. Install Python 3.11+ or set PYTHON_BIN."
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 was not found."
}

cleanup() {
  local pids=()
  [[ -n "${BACKEND_PID:-}" ]] && pids+=("$BACKEND_PID")
  [[ -n "${FRONTEND_PID:-}" ]] && pids+=("$FRONTEND_PID")

  if ((${#pids[@]} > 0)); then
    kill "${pids[@]}" >/dev/null 2>&1 || true
    wait "${pids[@]}" >/dev/null 2>&1 || true
  fi
}

PYTHON="$(find_python)"
require_command npm

[[ -d "$ROOT_DIR/backend" ]] || fail "backend directory is missing."
[[ -d "$ROOT_DIR/frontend" ]] || fail "frontend directory is missing."
[[ -d "$ROOT_DIR/frontend/node_modules" ]] || fail "frontend/node_modules is missing. Run: cd frontend && npm install"

"$PYTHON" - <<'PY' || fail "Backend dependencies are missing. Run: cd backend && python -m pip install -e '.[dev]'"
import fastapi
import uvicorn
PY

trap cleanup EXIT INT TERM

info "Starting backend at http://${BACKEND_HOST}:${BACKEND_PORT}"
(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

info "Starting frontend at http://${FRONTEND_HOST}:${FRONTEND_PORT}"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

info "Press Ctrl+C to stop both services."

while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    wait "$BACKEND_PID"
    exit $?
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    wait "$FRONTEND_PID"
    exit $?
  fi

  sleep 1
done
