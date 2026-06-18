from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run-codex-audit-local-e2e.sh"
DOC_PATH = PROJECT_ROOT / "docs" / "codex-audit-local-e2e.md"


def test_local_e2e_script_help_documents_modes_without_calling_codex() -> None:
    assert SCRIPT_PATH.is_file()

    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "MODE=disabled|fake|codex-cli" in completed.stdout
    assert "START_BACKEND=1" in completed.stdout
    assert "PTR_FILE=/path/to/ptr.pdf REPORT_FILE=/path/to/report.pdf" in completed.stdout
    assert "ENABLE_CODEX_AUDIT_LOCAL_E2E=1" in completed.stdout
    assert "danger-full-access" not in completed.stdout


def test_local_e2e_script_print_config_is_safe_for_codex_cli_mode() -> None:
    completed = subprocess.run(
        ["bash", str(SCRIPT_PATH), "--print-config"],
        cwd=PROJECT_ROOT,
        env={"MODE": "codex-cli", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "mode: codex-cli" in completed.stdout
    assert "will_call_real_codex_cli: no" in completed.stdout
    assert "requires ENABLE_CODEX_AUDIT_LOCAL_E2E=1" in completed.stdout


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
        "MODE": "disabled",
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


def test_local_e2e_document_covers_required_business_validation_paths() -> None:
    assert DOC_PATH.is_file()
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "验证本地 Web 工具在 fake / codex-cli 模式下可以展示 Codex 审核意见" in text
    assert "python -m uvicorn app.main:app --reload" in text
    assert "CODEX_AUDIT_ENABLED=1" in text
    assert "CODEX_AUDIT_BACKEND=fake" in text
    assert "CODEX_AUDIT_BACKEND=codex-cli" in text
    assert "CODEX_AUDIT_ALLOW_REAL_EXECUTION=1" in text
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
