from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import pytest

from app.domain.codex_review import (
    CodexEvidenceRef,
    CodexReviewRequest,
    CodexReviewStatus,
    CodexReviewTarget,
    CodexReviewTargetType,
    CodexReviewVerdict,
)
from app.domain.evidence_package import (
    EvidenceItem,
    EvidencePackage,
    EvidencePackageKind,
    EvidenceSourceType,
    EvidenceTarget,
)
from app.infrastructure.codex.codex_cli_runner import CodexCliRunner, CodexCliRunnerConfig
from app.infrastructure.codex.runner import CodexRunnerConfigurationError


CREATED_AT = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)
OLD_PROJECT = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13")
NEW_PROJECT = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3")


def _visual_metadata() -> dict:
    return {
        "observed_label_fields": {
            "component_name": None,
            "model": None,
            "serial_number": None,
            "batch_or_serial": None,
            "production_date": None,
            "expiration_date": None,
        },
        "field_comparisons": [],
        "visual_evidence_quality": None,
    }


def _target() -> CodexReviewTarget:
    return CodexReviewTarget(
        target_id="target-1",
        target_type=CodexReviewTargetType.REPORT_RULE,
        check_id="C02",
        finding_id="finding-1",
        finding_code="C02_FIELD_MISMATCH",
        evidence_refs=[CodexEvidenceRef(ref_id="ev-1", source_type="pdf_text")],
    )


def _request() -> CodexReviewRequest:
    return CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="report_check",
        targets=[_target()],
        prompt_version="test-prompt-v1",
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )


def _package() -> EvidencePackage:
    return EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="report_check",
        kind=EvidencePackageKind.REPORT_RULE_REVIEW,
        schema_version="evidence-package-v1",
        targets=[
            EvidenceTarget(
                target_id="target-1",
                target_type="report_rule",
                check_id="C02",
                evidence_refs=["ev-1"],
            )
        ],
        items=[
            EvidenceItem(
                ref_id="ev-1",
                source_type=EvidenceSourceType.PDF_TEXT,
                text="第三页型号规格: ABC-2",
            )
        ],
    )


def _output_payload() -> dict:
    return {
        "schema_version": "codex-review-output-v1",
        "reviews": [
            {
                "target_id": "target-1",
                "status": "succeeded",
                "verdict": "confirm",
                "confidence": "medium",
                "reasoning_summary": "Codex CLI fake output confirms the finding.",
                "evidence_refs": ["ev-1"],
                "suggested_severity": None,
                "suggested_finding": None,
                "metadata": _visual_metadata(),
            }
        ],
    }


def test_cli_runner_disabled_returns_skipped_without_subprocess(tmp_path, monkeypatch) -> None:
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess.run must not be called when Codex runner is disabled")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=False))

    results = runner.run_review(_request(), _package(), tmp_path)

    assert called is False
    assert results[0].status is CodexReviewStatus.SKIPPED
    assert results[0].metadata["reason"] == "codex_cli_disabled"


def test_cli_runner_enabled_without_allow_real_execution_does_not_call_subprocess(tmp_path, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called without allow_real_execution")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=False))

    results = runner.run_review(_request(), _package(), tmp_path)

    assert results[0].status is CodexReviewStatus.SKIPPED
    assert results[0].metadata["reason"] == "real_execution_not_allowed"


def test_cli_runner_builds_safe_codex_exec_command(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)
    schema_path = workspace / "schema.json"
    prompt_path = workspace / "prompt.txt"
    schema_path.write_text('{"type": "array"}', encoding="utf-8")
    prompt_path.write_text("Review evidence_package.json", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text(json.dumps(_output_payload()), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True, timeout_seconds=7))

    results = runner.run_review(
        _request(),
        _package(),
        workspace,
        output_schema_path=schema_path,
        prompt_path=prompt_path,
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[:2] == ["codex", "exec"]
    assert cmd[cmd.index("--cd") + 1] == str(workspace.resolve())
    assert cmd[cmd.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in cmd
    assert cmd[cmd.index("--output-schema") + 1] == str(schema_path.resolve())
    assert cmd[cmd.index("-o") + 1] == str((workspace / "codex_review_output.json").resolve())
    assert "danger-full-access" not in cmd
    assert "workspace-write" not in cmd
    assert captured["kwargs"]["timeout"] == 7
    assert results[0].status is CodexReviewStatus.SUCCEEDED
    assert results[0].verdict is CodexReviewVerdict.CONFIRM
    assert results[0].raw_output_path == "codex_review_output.json"
    assert results[0].metadata["parser"] == "codex_review_output"
    assert results[0].metadata["codex_exec_seconds"] >= 0
    assert results[0].metadata["exit_code"] == 0
    assert results[0].metadata["stdout_size_bytes"] == 2
    assert results[0].metadata["stderr_size_bytes"] == 0
    assert results[0].metadata["output_size_bytes"] > 0
    assert results[0].metadata["image_count"] == 0


def test_cli_runner_passes_workspace_images_as_codex_image_inputs(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)
    schema_path = workspace / "schema.json"
    prompt_path = workspace / "prompt.txt"
    image_path = workspace / "items" / "label.png"
    image_path.parent.mkdir()
    schema_path.write_text('{"type": "array"}', encoding="utf-8")
    prompt_path.write_text("Review evidence_package.json and label image", encoding="utf-8")
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text(json.dumps(_output_payload()), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(
        _request(),
        _package(),
        workspace,
        output_schema_path=schema_path,
        prompt_path=prompt_path,
        image_paths=[image_path],
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--image" in cmd
    assert cmd[cmd.index("--image") + 1] == "items/label.png"
    assert str(image_path) not in cmd
    assert results[0].status is CodexReviewStatus.SUCCEEDED


def test_cli_runner_passes_multiple_c07_images_as_codex_image_inputs(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    items_dir = workspace / "items"
    items_dir.mkdir(parents=True)
    schema_path = workspace / "schema.json"
    prompt_path = workspace / "prompt.txt"
    schema_path.write_text('{"type": "array"}', encoding="utf-8")
    prompt_path.write_text("Review C07 visual evidence", encoding="utf-8")
    image_names = [
        "finding-1-c07-page-p1.png",
        "finding-1-c07-table-p1.png",
        "finding-1-c07-item-group-p1.png",
        "finding-1-c07-result-p1.png",
        "finding-1-c07-conclusion-p1.png",
        "finding-1-c07-remark-p1.png",
    ]
    image_paths = []
    for image_name in image_names:
        image_path = items_dir / image_name
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        image_paths.append(image_path)
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text(json.dumps(_output_payload()), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(
        _request(),
        _package(),
        workspace,
        output_schema_path=schema_path,
        prompt_path=prompt_path,
        image_paths=image_paths,
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    image_args = [cmd[index + 1] for index, arg in enumerate(cmd) if arg == "--image"]
    assert image_args == [f"items/{image_name}" for image_name in image_names]
    assert all(str(path) not in cmd for path in image_paths)
    assert results[0].status is CodexReviewStatus.SUCCEEDED


def test_cli_runner_passes_multiple_complex_matrix_images_as_codex_image_inputs(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    items_dir = workspace / "items"
    items_dir.mkdir(parents=True)
    schema_path = workspace / "schema.json"
    prompt_path = workspace / "prompt.txt"
    schema_path.write_text('{"type": "array"}', encoding="utf-8")
    prompt_path.write_text("Review C07 complex matrix visual evidence", encoding="utf-8")
    image_names = [
        "finding-59-c07-matrix-page-p1.png",
        "finding-59-c07-matrix-table-p1.png",
        "finding-59-c07-matrix-header-p1.png",
        "finding-59-c07-matrix-body-p1.png",
        "finding-59-c07-matrix-result-p1.png",
        "finding-59-c07-matrix-conclusion-p1.png",
        "finding-59-c07-matrix-continuation-p2.png",
    ]
    image_paths = []
    for image_name in image_names:
        image_path = items_dir / image_name
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        image_paths.append(image_path)
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text(json.dumps(_output_payload()), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(
        _request(),
        _package(),
        workspace,
        output_schema_path=schema_path,
        prompt_path=prompt_path,
        image_paths=image_paths,
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    image_args = [cmd[index + 1] for index, arg in enumerate(cmd) if arg == "--image"]
    assert image_args == [f"items/{image_name}" for image_name in image_names]
    assert all(str(path) not in cmd for path in image_paths)
    assert results[0].status is CodexReviewStatus.SUCCEEDED


def test_cli_runner_rejects_missing_image_input_without_subprocess(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)
    missing_image = workspace / "items" / "missing-c07-page.png"

    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for missing image inputs")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace, image_paths=[missing_image])

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_IMAGE_INPUT_MISSING"


def test_cli_runner_rejects_image_inputs_outside_workspace(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)
    outside_image = tmp_path / "outside.png"
    outside_image.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for unsafe image inputs")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace, image_paths=[outside_image])

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_IMAGE_INPUT_FORBIDDEN"


def test_cli_runner_returns_failed_when_workspace_dir_is_missing(tmp_path, monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for missing workspace")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), tmp_path / "missing")

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_WORKSPACE_MISSING"


def test_cli_runner_rejects_project_root_workspace(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for project root workspace")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), NEW_PROJECT)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_WORKSPACE_FORBIDDEN"


def test_cli_runner_rejects_old_project_workspace(tmp_path, monkeypatch) -> None:
    if OLD_PROJECT.exists():
        old_project = OLD_PROJECT
        runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))
    else:
        old_project = tmp_path / "old-project"
        old_project.mkdir(parents=True)
        runner = CodexCliRunner(
            CodexCliRunnerConfig(
                enabled=True,
                allow_real_execution=True,
                forbidden_parent_roots=(old_project,),
            )
        )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called for old project workspace")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    results = runner.run_review(_request(), _package(), old_project)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_WORKSPACE_FORBIDDEN"


def test_cli_runner_converts_timeout_to_failed_review(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)

    def fake_timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_timeout)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True, timeout_seconds=3))

    results = runner.run_review(_request(), _package(), workspace)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_TIMEOUT"
    assert results[0].error.retryable is True


def test_cli_runner_converts_nonzero_exit_to_failed_review(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)

    def fake_nonzero(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 2, stdout="partial", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_nonzero)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_EXIT_NONZERO"
    assert "boom" in (results[0].error.detail or "")
    assert "stdout_size_bytes" in (results[0].error.detail or "")
    assert results[0].metadata["codex_exec_seconds"] >= 0
    assert results[0].metadata["exit_code"] == 2
    assert results[0].metadata["stdout_size_bytes"] == len("partial".encode())
    assert results[0].metadata["stderr_size_bytes"] == len("boom".encode())
    assert results[0].metadata["image_count"] == 0


def test_cli_runner_classifies_usage_limit_and_writes_diagnostics(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)
    prompt_path = workspace / "prompt.md"
    prompt_path.write_text("Review evidence package.\n" + ("prompt secret\n" * 200), encoding="utf-8")
    package_path = workspace / "evidence_package.json"
    package_path.write_text(json.dumps(_package().model_dump(mode="json")), encoding="utf-8")
    stderr = (
        "ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage "
        "to purchase more credits or try again at Jun 27th, 2026 9:59 PM."
    )

    def fake_usage_limit(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_usage_limit)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace, prompt_path=prompt_path)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_USAGE_LIMIT_EXCEEDED"
    assert results[0].metadata["retry_after_text"] == "Jun 27th, 2026 9:59 PM"
    assert "prompt secret" not in (results[0].error.detail or "")
    diagnostics_path = workspace / "codex_runner_error.json"
    assert diagnostics_path.is_file()
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    assert diagnostics["code"] == "CODEX_USAGE_LIMIT_EXCEEDED"
    assert diagnostics["exit_code"] == 1
    assert diagnostics["retry_after_text"] == "Jun 27th, 2026 9:59 PM"
    assert diagnostics["prompt_size_bytes"] == prompt_path.stat().st_size
    assert diagnostics["evidence_package_size_bytes"] == package_path.stat().st_size
    assert diagnostics["target_ids"] == ["target-1"]
    assert diagnostics["package_id"] == "pkg-1"
    assert (workspace / "codex_stdout.txt").is_file()
    assert (workspace / "codex_stderr.txt").read_text(encoding="utf-8") == stderr


def test_cli_runner_converts_command_not_found_to_failed_review(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)

    def fake_missing_command(cmd, **kwargs):
        raise FileNotFoundError("codex executable not found")

    monkeypatch.setattr(subprocess, "run", fake_missing_command)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_CLI_UNAVAILABLE"


def test_cli_runner_converts_malformed_output_to_failed_review(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)

    def fake_malformed(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text("not json", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_malformed)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_OUTPUT_INVALID_JSON"


def test_cli_runner_uses_parser_for_schema_invalid_output(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "runtime" / "codex_audit" / "task-1" / "pkg-1" / "input"
    workspace.mkdir(parents=True)

    def fake_schema_invalid(cmd, **kwargs):
        output_path = Path(cmd[cmd.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "schema_version": "codex-review-output-v1",
                    "reviews": [
                        {
                            "target_id": "target-1",
                            "status": "succeeded",
                            "verdict": "maybe",
                            "confidence": "medium",
                            "reasoning_summary": "Invalid verdict.",
                            "evidence_refs": ["ev-1"],
                            "suggested_severity": None,
                            "suggested_finding": None,
                            "metadata": {},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_schema_invalid)
    runner = CodexCliRunner(CodexCliRunnerConfig(enabled=True, allow_real_execution=True))

    results = runner.run_review(_request(), _package(), workspace)

    assert results[0].status is CodexReviewStatus.FAILED
    assert results[0].error is not None
    assert results[0].error.code == "CODEX_OUTPUT_SCHEMA_INVALID"


def test_cli_runner_rejects_unsafe_sandbox_values() -> None:
    assert CodexCliRunnerConfig().sandbox == "read-only"

    with pytest.raises(CodexRunnerConfigurationError):
        CodexCliRunnerConfig(sandbox="danger-full-access")

    with pytest.raises(CodexRunnerConfigurationError):
        CodexCliRunnerConfig(sandbox="workspace-write")
