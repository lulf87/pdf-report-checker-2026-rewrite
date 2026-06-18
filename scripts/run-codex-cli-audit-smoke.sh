#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

info() {
  printf '[codex-cli-smoke] %s\n' "$1"
}

fail() {
  printf '[codex-cli-smoke] ERROR: %s\n' "$1" >&2
  exit 1
}

resolve_python() {
  if [[ "$PYTHON_BIN" == */* ]]; then
    [[ -x "$PYTHON_BIN" ]] || fail "Python was not found or is not executable: $PYTHON_BIN"
    printf '%s\n' "$PYTHON_BIN"
    return
  fi

  command -v "$PYTHON_BIN" || fail "Python was not found. Set PYTHON_BIN=/path/to/python."
}

PYTHON="$(resolve_python)"
PYTEST_AVAILABLE=0

info "Python executable: $PYTHON"
info "Python version: $("$PYTHON" --version 2>&1)"
if "$PYTHON" - <<'PY' >/dev/null 2>&1
import pytest
PY
then
  PYTEST_AVAILABLE=1
  info "pytest: available"
else
  info "pytest: not available"
fi

if [[ "${ENABLE_CODEX_CLI_INTEGRATION:-}" != "1" ]]; then
  fail "Refusing to call 真实 codex exec. Re-run with ENABLE_CODEX_CLI_INTEGRATION=1 only for manual validation."
fi

if [[ "$PYTEST_AVAILABLE" != "1" ]]; then
  fail "pytest is not available for $PYTHON. Run: cd backend && python -m pip install -e \".[dev]\"; or use: PYTHON_BIN=/path/to/python ENABLE_CODEX_CLI_INTEGRATION=1 bash scripts/run-codex-cli-audit-smoke.sh"
fi

info "This will call real codex exec."
info "Sandbox: read-only."
info "Workspace: controlled tmp evidence workspace created by pytest tmp_path."
info "Evidence: minimal synthetic evidence package; project source is not provided as evidence."
info "This script does not start API/frontend services and does not modify the old project directory."

(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m pytest tests/integration/test_codex_cli_manual.py -v
)
