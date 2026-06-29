from __future__ import annotations

import json
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
            "CODEX_AUDIT_MAX_PARALLEL_JOBS": "2",
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
    assert "codex_audit_max_parallel_jobs: 2" in completed.stdout
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
    assert "[codex-audit-local-e2e] final_audit_status: needs_manual_review" in completed.stderr
    assert "[codex-audit-local-e2e] audit_scope: full" in completed.stderr
    assert "[codex-audit-local-e2e] confirmed_errors_count: 0" in completed.stderr
    assert "[codex-audit-local-e2e] manual_review_required_count: 34" in completed.stderr
    assert "[codex-audit-local-e2e] refuted_findings_count: 17" in completed.stderr
    assert "[codex-audit-local-e2e] candidate_errors_count: 44" in completed.stderr
    assert "[codex-audit-local-e2e] legacy deterministic counts: fail_count=5 error_count=44 warn_count=7" in completed.stderr
    assert "[codex-audit-local-e2e] performance total seconds: 92.5" in completed.stderr
    assert "[codex-audit-local-e2e] performance stage codex_audit_total: 82.0s" in completed.stderr
    assert "[codex-audit-local-e2e] performance packages: package_count=12 target_count=57 codex_exec_seconds=720.0 image_count=124 image_bytes=29400000" in completed.stderr
    assert "[codex-audit-local-e2e] effective batch size: 5" in completed.stderr


def test_local_e2e_script_warns_when_full_audit_batch_is_one() -> None:
    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--print-config"],
        cwd=PROJECT_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "CODEX_AUDIT_MAX_TARGETS_PER_BATCH": "1",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "codex_audit_max_targets_per_batch: 1" in completed.stdout
    assert "batch_size_warning: full audit batch=1 is debug/slow mode" in completed.stdout


def test_local_e2e_script_error_summary_recovers_task_and_usage_limit_from_workspace(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    workspace_task_id = "0ece4dd1-c2db-48b1-8cfa-efd21ea01a80"
    package_id = f"codex-report-{workspace_task_id}-C04-batch-6"
    workspace_dir = tmp_path / "runtime" / "codex_audit" / workspace_task_id / package_id / "input"
    workspace_dir.mkdir(parents=True)
    _write_fake_curl_with_usage_limit_error(fake_bin / "curl", workspace_dir=workspace_dir)
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

    assert completed.returncode != 0
    assert "Codex usage limit reached." in completed.stderr
    assert "Retry after: Jun 27th, 2026 9:59 PM" in completed.stderr
    summary_path = output_dir / "error_summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["task_id"] == workspace_task_id
    assert summary["task_status"] == "error"
    assert summary["check_id"] == "C04"
    assert summary["batch_id"] == "batch-6"
    assert summary["package_id"] == package_id
    assert summary["error_code"] == "CODEX_USAGE_LIMIT_EXCEEDED"
    assert summary["retry_after_text"] == "Jun 27th, 2026 9:59 PM"
    assert summary["workspace_dir"] == str(workspace_dir)


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


def _write_fake_curl_with_usage_limit_error(path: Path, *, workspace_dir: Path) -> None:
    status_message = (
        "CODEX_EXIT_NONZERO: Codex CLI exited with a non-zero status. "
        f"workspace_dir={workspace_dir}\n"
        "stderr=ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage "
        "to purchase more credits or try again at Jun 27th, 2026 9:59 PM."
    )
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
    print(json.dumps({{"task_id": "task-1", "status": "created", "task_type": "report_check"}}))
    raise SystemExit(0)

if url.endswith("/api/tasks/task-1"):
    assert output_path is not None
    output_path.write_text(
        json.dumps(
            {{
                "task_id": None,
                "status": "error",
                "progress": None,
                "current_step": None,
                "error": {status_message!r},
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
                "summary": {{
                    "audit_scope": "full",
                    "full_audit": True,
                    "final_audit_status": "needs_manual_review",
                    "candidate_findings_count": 51,
                    "candidate_errors_count": 44,
                    "confirmed_findings_count": 0,
                    "confirmed_errors_count": 0,
                    "refuted_findings_count": 17,
                    "manual_review_required_count": 34,
                    "suggested_additional_findings_count": 0,
                    "out_of_scope_findings_count": 0,
                    "unreviewed_required_findings_count": 0,
                    "codex_reviews_count": 57,
                    "codex_runtime_failure_count": 0,
                    "fail_count": 5,
                    "error_count": 44,
                    "warn_count": 7,
                }},
                "metadata": {{
                    "codex_audit": {{
                        "audit_scope": "full",
                        "full_audit": True,
                        "final_audit_status": "needs_manual_review",
                        "performance_profile": {{
                            "package_totals": {{
                                "package_count": 12,
                                "target_count": 57,
                                "codex_exec_seconds": 720.0,
                                "image_count": 124,
                                "image_bytes": 29400000,
                            }}
                        }},
                    }},
                    "performance_profile": {{
                        "total_seconds": 92.5,
                        "stages": [
                            {{"name": "parse_pdf", "duration_seconds": 2.5, "metadata": {{}}}},
                            {{"name": "codex_audit_total", "duration_seconds": 82.0, "metadata": {{}}}}
                        ],
                        "package_totals": {{
                            "package_count": 12,
                            "target_count": 57,
                            "codex_exec_seconds": 720.0,
                            "image_count": 124,
                            "image_bytes": 29400000,
                        }}
                    }}
                }},
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
