from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run-codex-audit-local-e2e.sh"
DOC_PATH = PROJECT_ROOT / "docs" / "codex-audit-local-e2e.md"


def test_local_e2e_script_help_documents_mandatory_codex_without_calling_codex() -> None:
    assert SCRIPT_PATH.is_file()

    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "mandatory Codex CLI" in completed.stdout
    assert "START_BACKEND=1" in completed.stdout
    assert "PTR_FILE=/path/to/ptr.pdf REPORT_FILE=/path/to/report.pdf" in completed.stdout
    assert "ENABLE_CODEX_AUDIT_LOCAL_E2E=1" in completed.stdout
    assert "MODE=disabled|fake|codex-cli" not in completed.stdout
    assert "danger-full-access" not in completed.stdout


def test_local_e2e_script_print_config_is_safe_for_mandatory_codex_cli() -> None:
    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--print-config"],
        cwd=PROJECT_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "CODEX_CLI_PATH": "/usr/local/bin/codex",
            "CODEX_AUDIT_MAX_TARGETS_PER_BATCH": "1",
            "CODEX_AUDIT_INCLUDED_CHECK_IDS": "C07",
            "CODEX_AUDIT_INCLUDED_FINDING_CODES": "CONCLUSION_MISMATCH_001",
            "CODEX_AUDIT_EXCLUDED_CHECK_IDS": "C04",
            "CODEX_AUDIT_PRIORITY_CHECK_IDS": "C07,C04",
            "CODEX_AUDIT_TIMEOUT_SECONDS": "300",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "audit_runtime: mandatory_codex_cli" in completed.stdout
    assert "will_call_real_codex_cli: no" in completed.stdout
    assert "requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1" in completed.stdout
    assert "codex_cli_path: /usr/local/bin/codex" in completed.stdout
    assert "codex_audit_max_targets_per_batch: 1" in completed.stdout
    assert "codex_audit_included_check_ids: C07" in completed.stdout
    assert "codex_audit_included_finding_codes: CONCLUSION_MISMATCH_001" in completed.stdout
    assert "codex_audit_excluded_check_ids: C04" in completed.stdout
    assert "codex_audit_priority_check_ids: C07,C04" in completed.stdout
    assert "codex_audit_timeout_seconds: 300" in completed.stdout


def test_local_e2e_script_exports_codex_audit_target_filter_variables() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "export CODEX_CLI_PATH" in text
    assert "export CODEX_AUDIT_MAX_TARGETS_PER_BATCH" in text
    assert "export CODEX_AUDIT_INCLUDED_CHECK_IDS" in text
    assert "export CODEX_AUDIT_INCLUDED_FINDING_CODES" in text
    assert "export CODEX_AUDIT_EXCLUDED_CHECK_IDS" in text
    assert "export CODEX_AUDIT_PRIORITY_CHECK_IDS" in text
    assert "export CODEX_AUDIT_BACKEND" not in text


def test_local_e2e_script_has_valid_bash_syntax() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_local_e2e_script_progress_logs_do_not_pollute_result_path(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_curl(fake_bin / "curl")
    report_file = tmp_path / "report.pdf"
    report_file.write_bytes(b"%PDF-1.4 fake report")
    output_dir = tmp_path / "output"

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHON_BIN": sys.executable,
        "ENABLE_CODEX_AUDIT_LOCAL_E2E": "1",
        "TASK_TYPE": "report-check",
        "REPORT_FILE": str(report_file),
        "BASE_URL": "http://local-e2e.test",
        "OUTPUT_DIR": str(output_dir),
        "EXPECT_CODEX_REVIEWS": "empty",
        "POLL_INTERVAL_SECONDS": "0",
        "TIMEOUT_SECONDS": "10",
    }

    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert "[codex-audit-local-e2e] Task task-1 status: completed" in completed.stderr
    assert "[codex-audit-local-e2e] Result JSON:" in completed.stderr
    assert (output_dir / "task-1.result.json").is_file()


def test_local_e2e_script_counts_duplicate_artifacts_once(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_curl_with_duplicate_artifacts(fake_bin / "curl")
    report_file = tmp_path / "report.pdf"
    report_file.write_bytes(b"%PDF-1.4 fake report")
    output_dir = tmp_path / "output"

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHON_BIN": sys.executable,
        "ENABLE_CODEX_AUDIT_LOCAL_E2E": "1",
        "TASK_TYPE": "report-check",
        "REPORT_FILE": str(report_file),
        "BASE_URL": "http://local-e2e.test",
        "OUTPUT_DIR": str(output_dir),
        "EXPECT_CODEX_REVIEWS": "nonempty",
        "POLL_INTERVAL_SECONDS": "0",
        "TIMEOUT_SECONDS": "10",
    }

    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "[codex-audit-local-e2e] codex_reviews count: 1" in completed.stderr
    assert "[codex-audit-local-e2e] unique findings count: 1" in completed.stderr


def test_local_e2e_document_covers_required_business_validation_paths() -> None:
    assert DOC_PATH.is_file()
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "Codex CLI 是本地业务验收的 mandatory auditor" in text
    assert "python -m uvicorn app.main:app --reload" in text
    assert "CODEX_CLI_PATH=codex" in text
    assert "CODEX_AUDIT_BACKEND=fake" not in text
    assert "CODEX_AUDIT_BACKEND=disabled" not in text
    assert "run-codex-audit-local-e2e.sh" in text
    assert "runtime/codex_audit" in text
    assert "前端只展示后端返回的 `codex_reviews`" in text
    assert "不重新计算 C01-C11 或 PTR 规则" in text


def _write_fake_curl(path: Path) -> None:
    path.write_text(
        f"""#!{sys.executable}
from __future__ import annotations

import json
import sys
from pathlib import Path


args = sys.argv[1:]
url = next((item for item in args if item.startswith("http://local-e2e.test")), "")
output_path = None
if "-o" in args:
    output_path = Path(args[args.index("-o") + 1])

if url.endswith("/api/health"):
    print(json.dumps({{"status": "ok"}}))
    raise SystemExit(0)

if url.endswith("/api/tasks/report-check"):
    print(json.dumps({{"task_id": "task-1", "status": "completed", "task_type": "report_check"}}))
    raise SystemExit(0)

if url.endswith("/api/tasks/task-1"):
    assert output_path is not None
    output_path.write_text(json.dumps({{"task_id": "task-1", "status": "completed"}}), encoding="utf-8")
    raise SystemExit(0)

if url.endswith("/api/tasks/task-1/result"):
    assert output_path is not None
    output_path.write_text(
        json.dumps({{"task_id": "task-1", "task_type": "report_check", "check_results": [{{"codex_reviews": []}}]}}),
        encoding="utf-8",
    )
    raise SystemExit(0)

print(f"unexpected curl args: {{args}}", file=sys.stderr)
raise SystemExit(22)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_curl_with_duplicate_artifacts(path: Path) -> None:
    path.write_text(
        f"""#!{sys.executable}
from __future__ import annotations

import json
import sys
from pathlib import Path


args = sys.argv[1:]
url = next((item for item in args if item.startswith("http://local-e2e.test")), "")
output_path = None
if "-o" in args:
    output_path = Path(args[args.index("-o") + 1])

if url.endswith("/api/health"):
    print(json.dumps({{"status": "ok"}}))
    raise SystemExit(0)

if url.endswith("/api/tasks/report-check"):
    print(json.dumps({{"task_id": "task-1", "status": "completed", "task_type": "report_check"}}))
    raise SystemExit(0)

if url.endswith("/api/tasks/task-1"):
    assert output_path is not None
    output_path.write_text(json.dumps({{"task_id": "task-1", "status": "completed"}}), encoding="utf-8")
    raise SystemExit(0)

if url.endswith("/api/tasks/task-1/result"):
    assert output_path is not None
    finding = {{"id": "duplicate-finding", "check_id": "C08", "code": "INSPECTION_FIELD_EMPTY"}}
    review = {{"review_id": "duplicate-review", "status": "succeeded"}}
    output_path.write_text(
        json.dumps(
            {{
                "task_id": "task-1",
                "task_type": "report_check",
                "findings": [finding],
                "check_results": [
                    {{"findings": [finding, finding], "codex_reviews": [review, review]}},
                    {{"codex_reviews": [review]}},
                ],
            }}
        ),
        encoding="utf-8",
    )
    raise SystemExit(0)

print(f"unexpected curl args: {{args}}", file=sys.stderr)
raise SystemExit(22)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
