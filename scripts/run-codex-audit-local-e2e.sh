#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
TASK_TYPE="${TASK_TYPE:-ptr-compare}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
START_BACKEND="${START_BACKEND:-0}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/runtime/codex_audit_local_e2e}"
EXPECT_CODEX_REVIEWS="${EXPECT_CODEX_REVIEWS:-auto}"
BACKEND_PID=""

log() {
  printf '[codex-audit-local-e2e] %s\n' "$*" >&2
}

fail() {
  printf '[codex-audit-local-e2e] ERROR: %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  ENABLE_CODEX_AUDIT_LOCAL_E2E=1 TASK_TYPE=ptr-compare PTR_FILE=/path/to/ptr.pdf REPORT_FILE=/path/to/report.pdf bash scripts/run-codex-audit-local-e2e.sh
  ENABLE_CODEX_AUDIT_LOCAL_E2E=1 TASK_TYPE=report-check REPORT_FILE=/path/to/report.pdf bash scripts/run-codex-audit-local-e2e.sh

Options:
  --help          Show this help without starting services or calling Codex.
  --print-config  Print resolved mandatory Codex CLI configuration without starting services or calling Codex.

Common variables:
  TASK_TYPE=ptr-compare|report-check
  BASE_URL=http://127.0.0.1:8000
  START_BACKEND=1
  PYTHON_BIN=/path/to/python
  PTR_FILE=/path/to/ptr.pdf REPORT_FILE=/path/to/report.pdf
  EXPECT_CODEX_REVIEWS=auto|empty|nonempty|any
  CODEX_CLI_PATH=codex
  CODEX_AUDIT_MAX_TARGETS_PER_BATCH=5
  CODEX_AUDIT_INCLUDED_CHECK_IDS=C07
  CODEX_AUDIT_INCLUDED_FINDING_CODES=CONCLUSION_MISMATCH_001
  CODEX_AUDIT_EXCLUDED_CHECK_IDS=C04
  CODEX_AUDIT_PRIORITY_CHECK_IDS=C02,C03,C07,C04,C05,C06
  CODEX_AUDIT_TIMEOUT_SECONDS=300

Codex CLI safety:
  Running this script against a backend may call the local Codex CLI. It requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1.
  The backend still uses runtime/codex_audit evidence workspaces, read-only sandbox, output schema, and timeout.
EOF
}

resolve_python() {
  if [[ "$PYTHON_BIN" == */* ]]; then
    [[ -x "$PYTHON_BIN" ]] || fail "Python was not found or is not executable: $PYTHON_BIN"
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  command -v "$PYTHON_BIN" || fail "Python was not found. Set PYTHON_BIN=/path/to/python."
}

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

validate_mode() {
  case "$TASK_TYPE" in
    ptr-compare|report-check) ;;
    *) fail "TASK_TYPE must be one of: ptr-compare, report-check" ;;
  esac
}

will_call_real_codex_cli() {
  if [[ "${ENABLE_CODEX_AUDIT_LOCAL_E2E:-}" == "1" ]]; then
    printf 'yes\n'
  else
    printf 'no\n'
  fi
}

print_config() {
  validate_mode
  cat <<EOF
audit_runtime: mandatory_codex_cli
task_type: $TASK_TYPE
base_url: $BASE_URL
start_backend: $START_BACKEND
will_call_real_codex_cli: $(will_call_real_codex_cli)
codex_cli_gate: requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1 before starting or contacting a backend
codex_cli_path: ${CODEX_CLI_PATH:-codex}
runtime_dir: ${CODEX_AUDIT_RUNTIME_DIR:-runtime/codex_audit}
codex_audit_max_targets_per_batch: ${CODEX_AUDIT_MAX_TARGETS_PER_BATCH:-5}
codex_audit_included_check_ids: ${CODEX_AUDIT_INCLUDED_CHECK_IDS:-}
codex_audit_included_finding_codes: ${CODEX_AUDIT_INCLUDED_FINDING_CODES:-}
codex_audit_excluded_check_ids: ${CODEX_AUDIT_EXCLUDED_CHECK_IDS:-}
codex_audit_priority_check_ids: ${CODEX_AUDIT_PRIORITY_CHECK_IDS:-C02,C03,C07,C04,C05,C06}
codex_audit_timeout_seconds: ${CODEX_AUDIT_TIMEOUT_SECONDS:-300}
expect_codex_reviews: $EXPECT_CODEX_REVIEWS
EOF
}

configure_codex_env() {
  [[ "${ENABLE_CODEX_AUDIT_LOCAL_E2E:-}" == "1" ]] || fail "Mandatory Codex CLI local E2E requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1."
  unset CODEX_AUDIT_ENABLED
  unset CODEX_AUDIT_BACKEND
  unset CODEX_AUDIT_ALLOW_REAL_EXECUTION
  export CODEX_CLI_PATH="${CODEX_CLI_PATH:-codex}"
  export CODEX_AUDIT_RUNTIME_DIR="${CODEX_AUDIT_RUNTIME_DIR:-runtime/codex_audit}"
  export CODEX_AUDIT_TIMEOUT_SECONDS="${CODEX_AUDIT_TIMEOUT_SECONDS:-300}"
  export CODEX_AUDIT_MAX_TARGETS_PER_BATCH="${CODEX_AUDIT_MAX_TARGETS_PER_BATCH:-5}"
  export CODEX_AUDIT_INCLUDED_CHECK_IDS="${CODEX_AUDIT_INCLUDED_CHECK_IDS:-}"
  export CODEX_AUDIT_INCLUDED_FINDING_CODES="${CODEX_AUDIT_INCLUDED_FINDING_CODES:-}"
  export CODEX_AUDIT_EXCLUDED_CHECK_IDS="${CODEX_AUDIT_EXCLUDED_CHECK_IDS:-}"
  export CODEX_AUDIT_PRIORITY_CHECK_IDS="${CODEX_AUDIT_PRIORITY_CHECK_IDS:-C02,C03,C07,C04,C05,C06}"
  export CODEX_AUDIT_SANDBOX="read-only"
  export CODEX_AUDIT_EPHEMERAL="${CODEX_AUDIT_EPHEMERAL:-true}"
}

wait_for_backend() {
  local deadline=$((SECONDS + 30))
  until curl -fsS "$BASE_URL/api/health" >/dev/null 2>&1; do
    if ((SECONDS >= deadline)); then
      fail "Backend did not become healthy at $BASE_URL/api/health"
    fi
    sleep 1
  done
}

start_backend() {
  configure_codex_env
  log "Starting backend at http://${BACKEND_HOST}:${BACKEND_PORT} with mandatory Codex CLI audit"
  (
    cd "$ROOT_DIR/backend"
    "$PYTHON" -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) &
  BACKEND_PID=$!
  trap cleanup EXIT INT TERM
  wait_for_backend
}

require_inputs() {
  [[ -n "${REPORT_FILE:-}" ]] || fail "REPORT_FILE is required."
  [[ -f "$REPORT_FILE" ]] || fail "REPORT_FILE does not exist: $REPORT_FILE"
  if [[ "$TASK_TYPE" == "ptr-compare" ]]; then
    [[ -n "${PTR_FILE:-}" ]] || fail "PTR_FILE is required for TASK_TYPE=ptr-compare."
    [[ -f "$PTR_FILE" ]] || fail "PTR_FILE does not exist: $PTR_FILE"
  fi
}

create_task() {
  if [[ "$TASK_TYPE" == "ptr-compare" ]]; then
    curl -fsS -X POST "$BASE_URL/api/tasks/ptr-compare" \
      -F "ptr_file=@${PTR_FILE};type=application/pdf" \
      -F "report_file=@${REPORT_FILE};type=application/pdf"
    return
  fi

  curl -fsS -X POST "$BASE_URL/api/tasks/report-check" \
    -F "report_file=@${REPORT_FILE};type=application/pdf"
}

json_field() {
  "$PYTHON" - "$1" "$2" <<'PY'
import json
import sys

path, field = sys.argv[1], sys.argv[2]
data = json.loads(open(path, encoding="utf-8").read())
value = data
for part in field.split("."):
    value = value[part]
print(value)
PY
}

poll_result() {
  local task_id="$1"
  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  local status_file="$OUTPUT_DIR/${task_id}.status.json"

  while true; do
    curl -fsS "$BASE_URL/api/tasks/$task_id" -o "$status_file"
    local status
    status="$(json_field "$status_file" "status")"
    log "Task $task_id status: $status"
    case "$status" in
      completed)
        curl -fsS "$BASE_URL/api/tasks/$task_id/result" -o "$OUTPUT_DIR/${task_id}.result.json"
        printf '%s\n' "$OUTPUT_DIR/${task_id}.result.json"
        return
        ;;
      error)
        cat "$status_file" >&2
        fail "Task failed."
        ;;
    esac
    if ((SECONDS >= deadline)); then
      fail "Timed out waiting for task $task_id."
    fi
    sleep "$POLL_INTERVAL_SECONDS"
  done
}

count_codex_reviews() {
  "$PYTHON" - "$1" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

seen = set()
for node in walk(data):
    reviews = node.get("codex_reviews") if isinstance(node, dict) else None
    if not isinstance(reviews, list):
        continue
    for review in reviews:
        if not isinstance(review, dict):
            continue
        key = review.get("review_id") or json.dumps(review, ensure_ascii=False, sort_keys=True)
        seen.add(str(key))
print(len(seen))
PY
}

count_unique_findings() {
  "$PYTHON" - "$1" <<'PY'
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

seen = set()
for node in walk(data):
    findings = node.get("findings") if isinstance(node, dict) else None
    if not isinstance(findings, list):
        continue
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        key = finding.get("id") or json.dumps(finding, ensure_ascii=False, sort_keys=True)
        seen.add(str(key))
print(len(seen))
PY
}

expected_review_mode() {
  if [[ "$EXPECT_CODEX_REVIEWS" != "auto" ]]; then
    printf '%s\n' "$EXPECT_CODEX_REVIEWS"
    return
  fi
  printf 'nonempty\n'
}

assert_codex_reviews() {
  local result_file="$1"
  local count
  local expected
  count="$(count_codex_reviews "$result_file")"
  expected="$(expected_review_mode)"
  log "codex_reviews count: $count"

  case "$expected" in
    any) return ;;
    empty)
      [[ "$count" == "0" ]] || fail "Expected no codex_reviews, got $count."
      ;;
    nonempty)
      [[ "$count" != "0" ]] || fail "Expected codex_reviews. Ensure the backend used mandatory Codex audit and the sample produced audit targets."
      ;;
    *) fail "EXPECT_CODEX_REVIEWS must be one of: auto, empty, nonempty, any" ;;
  esac
}

validate_result_path() {
  local result_file="$1"
  [[ -n "$result_file" ]] || fail "Result JSON path is empty."
  [[ "$result_file" != *$'\n'* ]] || fail "Result JSON path must be a single line."
  [[ "$result_file" == *.json ]] || fail "Result JSON path must end with .json: $result_file"
  [[ -f "$result_file" ]] || fail "Result JSON file does not exist: $result_file"
}

main() {
  if [[ "${1:-}" == "--help" ]]; then
    usage
    return
  fi
  if [[ "${1:-}" == "--print-config" ]]; then
    print_config
    return
  fi

  validate_mode
  [[ "${ENABLE_CODEX_AUDIT_LOCAL_E2E:-}" == "1" ]] || fail "Mandatory Codex CLI local E2E requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1."
  PYTHON="$(resolve_python)"
  command -v curl >/dev/null 2>&1 || fail "curl was not found."
  "$PYTHON" - <<'PY' >/dev/null 2>&1 || fail "Python json module is unavailable."
import json
PY

  mkdir -p "$OUTPUT_DIR"
  require_inputs
  if [[ "$START_BACKEND" == "1" ]]; then
    start_backend
  else
    wait_for_backend
  fi

  local create_file="$OUTPUT_DIR/create-task.json"
  create_task > "$create_file"
  local task_id
  task_id="$(json_field "$create_file" "task_id")"
  log "Created task: $task_id"
  local result_file
  result_file="$(poll_result "$task_id")"
  validate_result_path "$result_file"
  assert_codex_reviews "$result_file"
  log "unique findings count: $(count_unique_findings "$result_file")"
  log "Result JSON: $result_file"
  log "Local business E2E validation finished."
}

main "$@"
