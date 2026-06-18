#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

info() {
  printf '[codex-cli-smoke] %s\n' "$1"
}

fail() {
  printf '[codex-cli-smoke] ERROR: %s\n' "$1" >&2
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

if [[ "${ENABLE_CODEX_CLI_INTEGRATION:-}" != "1" ]]; then
  fail "Refusing to call 真实 codex exec. Re-run with ENABLE_CODEX_CLI_INTEGRATION=1 only for manual validation."
fi

info "This will call real codex exec."
info "Sandbox: read-only."
info "Workspace: controlled tmp evidence workspace created by pytest tmp_path."
info "Evidence: minimal synthetic evidence package; project source is not provided as evidence."
info "This script does not start API/frontend services and does not modify the old project directory."

PYTHON="$(find_python)"

(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m pytest tests/integration/test_codex_cli_manual.py -v
)
