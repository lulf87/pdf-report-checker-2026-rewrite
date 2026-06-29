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
  CODEX_AUDIT_MAX_PARALLEL_JOBS=1
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
codex_audit_max_parallel_jobs: ${CODEX_AUDIT_MAX_PARALLEL_JOBS:-1}
codex_audit_included_check_ids: ${CODEX_AUDIT_INCLUDED_CHECK_IDS:-}
codex_audit_included_finding_codes: ${CODEX_AUDIT_INCLUDED_FINDING_CODES:-}
codex_audit_excluded_check_ids: ${CODEX_AUDIT_EXCLUDED_CHECK_IDS:-}
codex_audit_priority_check_ids: ${CODEX_AUDIT_PRIORITY_CHECK_IDS:-C02,C03,C07,C04,C05,C06}
codex_audit_timeout_seconds: ${CODEX_AUDIT_TIMEOUT_SECONDS:-300}
expect_codex_reviews: $EXPECT_CODEX_REVIEWS
EOF
  if [[ "${CODEX_AUDIT_MAX_TARGETS_PER_BATCH:-5}" == "1" \
    && -z "${CODEX_AUDIT_INCLUDED_CHECK_IDS:-}" \
    && -z "${CODEX_AUDIT_INCLUDED_FINDING_CODES:-}" \
    && -z "${CODEX_AUDIT_EXCLUDED_CHECK_IDS:-}" ]]; then
    printf '%s\n' "batch_size_warning: full audit batch=1 is debug/slow mode"
  fi
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
  export CODEX_AUDIT_MAX_PARALLEL_JOBS="${CODEX_AUDIT_MAX_PARALLEL_JOBS:-1}"
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

write_error_summary() {
  local status_file="$1"
  local task_id_hint="$2"
  "$PYTHON" - "$status_file" "$task_id_hint" "$OUTPUT_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path


status_path = Path(sys.argv[1])
task_id_hint = sys.argv[2]
output_dir = Path(sys.argv[3])


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def walk(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk(nested)


def clean(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return None
    text = str(value).strip()
    return text or None


def first_field(data, keys):
    for node in walk(data):
        if not isinstance(node, dict):
            continue
        for key in keys:
            value = clean(node.get(key))
            if value is not None:
                return value
    return None


def collect_text(data):
    chunks = []
    for node in walk(data):
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, str):
                    chunks.append(value)
    try:
        chunks.append(json.dumps(data, ensure_ascii=False))
    except TypeError:
        pass
    return "\n".join(chunks)


def find_workspace_dir(text):
    match = re.search(
        r"(?:workspace_dir=|workspace_dir:\s*)?(?P<workspace>[^\s'\"<>]*runtime/codex_audit/[0-9a-fA-F-]{36}/[^\s'\"<>]+/input)",
        text,
    )
    return match.group("workspace") if match else None


def parse_workspace(workspace_text):
    if not workspace_text:
        return None, None
    parts = Path(workspace_text).parts
    if "codex_audit" not in parts:
        return None, None
    index = parts.index("codex_audit")
    task_id = parts[index + 1] if len(parts) > index + 1 else None
    package_id = parts[index + 2] if len(parts) > index + 2 else None
    return task_id, package_id


def parse_package(package_id):
    if not package_id:
        return None, None, None
    match = re.search(
        r"codex-[^-]+-(?P<task_id>[0-9a-fA-F-]{36})-(?P<check_id>[A-Za-z0-9_]+)-(?P<batch_id>batch-\d+)",
        package_id,
    )
    if not match:
        return None, None, None
    return match.group("task_id"), match.group("check_id"), match.group("batch_id")


def read_workspace_diagnostics(workspace_text):
    if not workspace_text:
        return {}, ""
    workspace = Path(workspace_text)
    diagnostics = {}
    text_chunks = []
    runner_error_path = workspace / "codex_runner_error.json"
    if runner_error_path.is_file():
        diagnostics = read_json(runner_error_path)
        if diagnostics:
            text_chunks.append(json.dumps(diagnostics, ensure_ascii=False))
    for name in ("codex_stderr.txt", "stderr.txt"):
        path = workspace / name
        if path.is_file():
            try:
                text_chunks.append(path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return diagnostics if isinstance(diagnostics, dict) else {}, "\n".join(text_chunks)


def error_code_from(data, diagnostics, text):
    error = data.get("error") if isinstance(data, dict) else None
    code = clean(data.get("error_code")) if isinstance(data, dict) else None
    if code is None and isinstance(error, dict):
        code = clean(error.get("code"))
    if code is None:
        code = clean(diagnostics.get("code"))
    if code is None:
        match = re.search(r"\b(CODEX_[A-Z0-9_]+)\b", text)
        code = match.group(1) if match else None
    lowered = text.lower()
    if "you've hit your usage limit" in lowered or ("usage limit" in lowered and "try again at" in lowered):
        return "CODEX_USAGE_LIMIT_EXCEEDED"
    return code


def retry_after_from(diagnostics, text):
    retry = clean(diagnostics.get("retry_after_text"))
    if retry:
        return retry.rstrip(".")
    match = re.search(r"try again at\s+(.+?)(?:\.|\n|$)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().rstrip(".")


data = read_json(status_path)
status_text = collect_text(data)
workspace_dir = first_field(data, ("workspace_dir", "failed_workspace", "failed_workspace_dir"))
if workspace_dir is None:
    workspace_dir = find_workspace_dir(status_text)

workspace_task_id, workspace_package_id = parse_workspace(workspace_dir)
diagnostics, diagnostics_text = read_workspace_diagnostics(workspace_dir)
combined_text = "\n".join(chunk for chunk in (status_text, diagnostics_text) if chunk)

package_id = (
    clean(diagnostics.get("package_id"))
    or first_field(data, ("package_id", "failed_package_id"))
    or workspace_package_id
)
package_task_id, check_id, batch_id = parse_package(package_id)
task_id = (
    first_field(data, ("task_id",))
    or clean(diagnostics.get("task_id"))
    or workspace_task_id
    or package_task_id
    or clean(task_id_hint)
)
if check_id is None:
    check_id = first_field(data, ("check_id", "failed_check_id"))
if batch_id is None:
    batch_id = first_field(data, ("batch_id", "batch"))

summary = {
    "task_id": task_id,
    "task_status": first_field(data, ("task_status", "status")),
    "progress": first_field(data, ("progress",)),
    "current_step": first_field(data, ("current_step",)),
    "error_code": error_code_from(data, diagnostics, combined_text),
    "retry_after_text": retry_after_from(diagnostics, combined_text),
    "workspace_dir": workspace_dir,
    "package_id": package_id,
    "check_id": check_id,
    "batch_id": batch_id,
}

output_dir.mkdir(parents=True, exist_ok=True)
latest_path = output_dir / "error_summary.json"
latest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
if task_id:
    task_path = output_dir / f"{task_id}.error_summary.json"
    task_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(latest_path)
PY
}

print_error_summary() {
  local summary_file="$1"
  "$PYTHON" - "$summary_file" <<'PY' | while IFS= read -r line; do log "$line"; done
import json
import sys

summary_path = sys.argv[1]
summary = json.loads(open(summary_path, encoding="utf-8").read())
error_code = summary.get("error_code")
if error_code == "CODEX_USAGE_LIMIT_EXCEEDED":
    print("Codex usage limit reached.")
    retry_after = summary.get("retry_after_text")
    if retry_after:
        print(f"Retry after: {retry_after}")
else:
    print(f"Task failed with error_code: {error_code or ''}")
workspace_dir = summary.get("workspace_dir")
if workspace_dir:
    print(f"Failed workspace: {workspace_dir}")
print("Result JSON was not produced.")
print(f"Error summary JSON: {summary_path}")
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
        local summary_file
        summary_file="$(write_error_summary "$status_file" "$task_id")"
        print_error_summary "$summary_file"
        fail "Task failed. Result JSON was not produced."
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

print_final_audit_summary() {
  "$PYTHON" - "$1" <<'PY' | while IFS= read -r line; do log "$line"; done
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())
summary = data.get("summary")
metadata = data.get("metadata")
if not isinstance(summary, dict):
    summary = {}
if not isinstance(metadata, dict):
    metadata = {}
codex_audit = metadata.get("codex_audit")
if not isinstance(codex_audit, dict):
    codex_audit = {}

if not summary and not codex_audit:
    raise SystemExit(0)


def value_for(key):
    value = summary.get(key)
    if value is None:
        value = codex_audit.get(key)
    return value


def format_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


for key in [
    "audit_scope",
    "full_audit",
    "final_audit_status",
    "candidate_findings_count",
    "candidate_errors_count",
    "confirmed_findings_count",
    "confirmed_errors_count",
    "refuted_findings_count",
    "manual_review_required_count",
    "suggested_additional_findings_count",
    "out_of_scope_findings_count",
    "unreviewed_required_findings_count",
    "codex_reviews_count",
    "codex_runtime_failure_count",
]:
    value = value_for(key)
    if value is not None:
        print(f"{key}: {format_value(value)}")

legacy_keys = ["fail_count", "error_count", "warn_count"]
if any(key in summary for key in legacy_keys):
    print(
        "legacy deterministic counts: "
        f"fail_count={format_value(summary.get('fail_count', 0))} "
        f"error_count={format_value(summary.get('error_count', 0))} "
        f"warn_count={format_value(summary.get('warn_count', 0))}"
    )
PY
}

print_performance_summary() {
  "$PYTHON" - "$1" <<'PY' | while IFS= read -r line; do log "$line"; done
import json
import sys

data = json.loads(open(sys.argv[1], encoding="utf-8").read())
metadata = data.get("metadata")
if not isinstance(metadata, dict):
    metadata = {}
profile = metadata.get("performance_profile")
if not isinstance(profile, dict):
    profile = {}
codex_audit = metadata.get("codex_audit")
if not isinstance(codex_audit, dict):
    codex_audit = {}
codex_profile = codex_audit.get("performance_profile")
if not isinstance(codex_profile, dict):
    codex_profile = {}

total = profile.get("total_seconds")
if total is not None:
    print(f"performance total seconds: {total}")

stages = profile.get("stages")
if isinstance(stages, list):
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        name = stage.get("name")
        duration = stage.get("duration_seconds")
        if name and duration is not None:
            print(f"performance stage {name}: {duration}s")

package_totals = profile.get("package_totals")
if not isinstance(package_totals, dict):
    package_totals = codex_profile.get("package_totals")
if isinstance(package_totals, dict) and package_totals:
    print(
        "performance packages: "
        f"package_count={package_totals.get('package_count', 0)} "
        f"target_count={package_totals.get('target_count', 0)} "
        f"codex_exec_seconds={package_totals.get('codex_exec_seconds', 0)} "
        f"image_count={package_totals.get('image_count', 0)} "
        f"image_bytes={package_totals.get('image_bytes', 0)}"
    )
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
  print_final_audit_summary "$result_file"
  print_performance_summary "$result_file"
  log "effective batch size: ${CODEX_AUDIT_MAX_TARGETS_PER_BATCH:-5}"
  log "unique findings count: $(count_unique_findings "$result_file")"
  log "Result JSON: $result_file"
  log "Local business E2E validation finished."
}

main "$@"
