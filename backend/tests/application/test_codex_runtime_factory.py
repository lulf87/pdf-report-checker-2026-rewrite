from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pytest import MonkeyPatch

from app.application.codex_runtime_factory import (
    build_codex_audit_service,
    build_ptr_compare_usecase,
    build_report_check_usecase,
)
from app.application.task_service import TaskService
from app.core.config import Settings
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
from app.infrastructure.codex import CodexCliRunner, FakeCodexRunner


CREATED_AT = datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)


def test_codex_audit_settings_default_to_disabled(monkeypatch: MonkeyPatch) -> None:
    for name in (
        "CODEX_AUDIT_ENABLED",
        "CODEX_AUDIT_BACKEND",
        "CODEX_AUDIT_ALLOW_REAL_EXECUTION",
        "CODEX_AUDIT_TIMEOUT_SECONDS",
        "CODEX_AUDIT_RUNTIME_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.codex_audit_enabled is False
    assert settings.codex_audit_backend == "disabled"
    assert settings.codex_audit_allow_real_execution is False
    assert settings.codex_audit_timeout_seconds == 120
    assert settings.codex_audit_runtime_dir == "runtime/codex_audit"
    assert build_codex_audit_service(settings) is None


def test_codex_audit_settings_read_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_AUDIT_ENABLED", "1")
    monkeypatch.setenv("CODEX_AUDIT_BACKEND", "fake")
    monkeypatch.setenv("CODEX_AUDIT_ALLOW_REAL_EXECUTION", "1")
    monkeypatch.setenv("CODEX_AUDIT_TIMEOUT_SECONDS", "77")
    monkeypatch.setenv("CODEX_AUDIT_RUNTIME_DIR", "runtime/custom-codex-audit")

    settings = Settings(_env_file=None)

    assert settings.codex_audit_enabled is True
    assert settings.codex_audit_backend == "fake"
    assert settings.codex_audit_allow_real_execution is True
    assert settings.codex_audit_timeout_seconds == 77
    assert settings.codex_audit_runtime_dir == "runtime/custom-codex-audit"


def test_fake_backend_builds_service_and_usecases_that_enable_codex_reviews(tmp_path: Path) -> None:
    settings = Settings(
        codex_audit_enabled=True,
        codex_audit_backend="fake",
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        _env_file=None,
    )

    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, FakeCodexRunner)

    request, package = _review_contract()
    reviews = service.review(request, package)

    assert reviews[0].status is CodexReviewStatus.SUCCEEDED
    assert reviews[0].verdict is CodexReviewVerdict.CONFIRM
    assert list((tmp_path / "runtime" / "codex_audit" / "task-1").glob("*/input/prompt.md"))

    ptr_usecase = build_ptr_compare_usecase(settings, task_service=TaskService())
    report_usecase = build_report_check_usecase(settings, task_service=TaskService())
    assert ptr_usecase.codex_audit_enabled is True
    assert report_usecase.codex_audit_enabled is True
    assert ptr_usecase.codex_audit_service is not None
    assert report_usecase.codex_audit_service is not None


def test_codex_cli_backend_without_real_execution_returns_skipped_without_subprocess(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("subprocess.run must not be called when real execution is not allowed")

    monkeypatch.setattr("app.infrastructure.codex.codex_cli_runner.subprocess.run", fail_run)
    settings = Settings(
        codex_audit_enabled=True,
        codex_audit_backend="codex-cli",
        codex_audit_allow_real_execution=False,
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        _env_file=None,
    )

    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, CodexCliRunner)
    assert service.runner.config.enabled is True
    assert service.runner.config.allow_real_execution is False
    assert service.runner.config.sandbox == "read-only"

    request, package = _review_contract()
    reviews = service.review(request, package)

    assert reviews[0].status is CodexReviewStatus.SKIPPED
    assert reviews[0].metadata["reason"] == "real_execution_not_allowed"


def test_codex_cli_backend_with_real_execution_can_be_monkeypatched(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(command, *, cwd, capture_output, text, timeout, check):  # noqa: ANN001
        calls.append(command)
        assert cwd.endswith("/input")
        assert capture_output is True
        assert text is True
        assert timeout == 33
        assert check is False
        assert command[0:2] == ["codex", "exec"]
        assert command[command.index("--sandbox") + 1] == "read-only"
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "schema_version": "codex-review-output-v1",
                    "reviews": [
                        {
                            "target_id": "target-1",
                            "status": "succeeded",
                            "verdict": "confirm",
                            "confidence": "high",
                            "reasoning_summary": "Monkeypatched Codex CLI output.",
                            "evidence_refs": ["ev-1"],
                            "suggested_severity": None,
                            "suggested_finding": None,
                            "metadata": {"runner": "monkeypatched"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("app.infrastructure.codex.codex_cli_runner.subprocess.run", fake_run)
    settings = Settings(
        codex_audit_enabled=True,
        codex_audit_backend="codex-cli",
        codex_audit_allow_real_execution=True,
        codex_audit_timeout_seconds=33,
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        _env_file=None,
    )

    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, CodexCliRunner)
    assert service.runner.config.allow_real_execution is True

    request, package = _review_contract()
    reviews = service.review(request, package)

    assert calls
    assert reviews[0].status is CodexReviewStatus.SUCCEEDED
    assert reviews[0].verdict is CodexReviewVerdict.CONFIRM
    assert reviews[0].metadata["runner"] == "monkeypatched"


def _review_contract() -> tuple[CodexReviewRequest, EvidencePackage]:
    target = EvidenceTarget(
        target_id="target-1",
        target_type=CodexReviewTargetType.PTR_PARAMETER.value,
        check_id="PTR_TABLE",
        finding_id="finding-1",
        finding_code="PTR_TABLE_VALUE_MISMATCH",
        summary="Review a deterministic PTR value mismatch candidate.",
        evidence_refs=["ev-1"],
    )
    item = EvidenceItem(
        ref_id="ev-1",
        source_type=EvidenceSourceType.FINDING,
        title="Candidate finding",
        structured={
            "id": "finding-1",
            "code": "PTR_TABLE_VALUE_MISMATCH",
            "expected": ">= 100 MΩ",
            "actual": ">= 10 MΩ",
        },
    )
    package = EvidencePackage(
        package_id="pkg-1",
        task_id="task-1",
        task_type="ptr_compare",
        kind=EvidencePackageKind.PTR_PARAMETER_REVIEW,
        schema_version="evidence-package-v1",
        created_at=CREATED_AT,
        targets=[target],
        items=[item],
    )
    request = CodexReviewRequest(
        request_id="request-1",
        task_id="task-1",
        task_type="ptr_compare",
        targets=[
            CodexReviewTarget(
                target_id="target-1",
                target_type=CodexReviewTargetType.PTR_PARAMETER,
                check_id="PTR_TABLE",
                finding_id="finding-1",
                finding_code="PTR_TABLE_VALUE_MISMATCH",
                summary="Review a deterministic PTR value mismatch candidate.",
                evidence_refs=[
                    CodexEvidenceRef(ref_id="ev-1", source_type=EvidenceSourceType.FINDING.value),
                ],
            )
        ],
        schema_version="codex-review-output-v1",
        created_at=CREATED_AT,
    )
    return request, package
