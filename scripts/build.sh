#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info() {
  printf '[build] %s\n' "$1"
}

fail() {
  printf '[build] ERROR: %s\n' "$1" >&2
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

PYTHON="$(find_python)"
require_command npm

info "Checking backend Python syntax"
(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m compileall -q app
)

info "Building frontend"
(
  cd "$ROOT_DIR/frontend"
  npm run build
)
