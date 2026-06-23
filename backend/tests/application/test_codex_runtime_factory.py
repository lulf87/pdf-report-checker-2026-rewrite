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
from app.infrastructure.codex import CodexCliRunner


CREATED_AT = datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)


def test_codex_audit_settings_default_to_mandatory_codex_cli(monkeypatch: MonkeyPatch) -> None:
    for name in (
        "CODEX_AUDIT_ENABLED",
        "CODEX_AUDIT_BACKEND",
        "CODEX_AUDIT_ALLOW_REAL_EXECUTION",
        "CODEX_CLI_PATH",
        "CODEX_AUDIT_TIMEOUT_SECONDS",
        "CODEX_AUDIT_RUNTIME_DIR",
        "CODEX_AUDIT_MAX_TARGETS_PER_TASK",
        "CODEX_AUDIT_MAX_TARGETS_PER_BATCH",
        "CODEX_AUDIT_INCLUDED_CHECK_IDS",
        "CODEX_AUDIT_INCLUDED_FINDING_CODES",
        "CODEX_AUDIT_EXCLUDED_CHECK_IDS",
        "CODEX_AUDIT_PRIORITY_CHECK_IDS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.codex_cli_path == "codex"
    assert settings.codex_audit_timeout_seconds == 300
    assert settings.codex_audit_runtime_dir == "runtime/codex_audit"
    assert settings.codex_audit_max_targets_per_batch == 5
    assert settings.codex_audit_sandbox == "read-only"
    assert settings.codex_audit_ephemeral is True
    assert settings.codex_audit_included_check_ids is None
    assert settings.codex_audit_included_finding_codes is None
    assert settings.codex_audit_excluded_check_ids is None
    assert settings.codex_audit_priority_check_ids == "C02,C03,C07,C04,C05,C06"
    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, CodexCliRunner)
    assert service.runner.config.executable == "codex"
    assert service.runner.config.timeout_seconds == 300
    assert service.runner.config.sandbox == "read-only"
    assert service.runner.config.ephemeral is True


def test_codex_audit_settings_read_environment(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_CLI_PATH", "/usr/local/bin/codex")
    monkeypatch.setenv("CODEX_AUDIT_TIMEOUT_SECONDS", "77")
    monkeypatch.setenv("CODEX_AUDIT_RUNTIME_DIR", "runtime/custom-codex-audit")
    monkeypatch.setenv("CODEX_AUDIT_MAX_TARGETS_PER_BATCH", "1")
    monkeypatch.setenv("CODEX_AUDIT_SANDBOX", "read-only")
    monkeypatch.setenv("CODEX_AUDIT_EPHEMERAL", "false")
    monkeypatch.setenv("CODEX_AUDIT_INCLUDED_CHECK_IDS", "C07")
    monkeypatch.setenv("CODEX_AUDIT_INCLUDED_FINDING_CODES", "CONCLUSION_MISMATCH_001")
    monkeypatch.setenv("CODEX_AUDIT_EXCLUDED_CHECK_IDS", "C04")
    monkeypatch.setenv("CODEX_AUDIT_PRIORITY_CHECK_IDS", "C07,C04")

    settings = Settings(_env_file=None)

    assert settings.codex_cli_path == "/usr/local/bin/codex"
    assert settings.codex_audit_timeout_seconds == 77
    assert settings.codex_audit_runtime_dir == "runtime/custom-codex-audit"
    assert settings.codex_audit_max_targets_per_batch == 1
    assert settings.codex_audit_sandbox == "read-only"
    assert settings.codex_audit_ephemeral is False
    assert settings.codex_audit_included_check_ids == "C07"
    assert settings.codex_audit_included_finding_codes == "CONCLUSION_MISMATCH_001"
    assert settings.codex_audit_excluded_check_ids == "C04"
    assert settings.codex_audit_priority_check_ids == "C07,C04"


def test_factory_builds_mandatory_codex_cli_service_and_usecases(tmp_path: Path) -> None:
    settings = Settings(
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        _env_file=None,
    )

    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, CodexCliRunner)

    ptr_usecase = build_ptr_compare_usecase(settings, task_service=TaskService())
    report_usecase = build_report_check_usecase(settings, task_service=TaskService())
    assert ptr_usecase.codex_audit_service is not None
    assert report_usecase.codex_audit_service is not None
    assert ptr_usecase.ptr_codex_evidence_builder.target_selection.max_targets_per_batch == 5
    assert report_usecase.report_codex_evidence_builder.target_selection.max_targets_per_batch == 5


def test_factory_passes_target_selection_settings_to_usecase_builders(tmp_path: Path) -> None:
    settings = Settings(
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        codex_audit_max_targets_per_batch=1,
        codex_audit_included_check_ids="C07",
        codex_audit_included_finding_codes="CONCLUSION_MISMATCH_001",
        codex_audit_excluded_check_ids="C04",
        codex_audit_priority_check_ids="C07,C04",
        _env_file=None,
    )

    ptr_usecase = build_ptr_compare_usecase(settings, task_service=TaskService())
    report_usecase = build_report_check_usecase(settings, task_service=TaskService())

    assert report_usecase.report_codex_evidence_builder.target_selection.max_targets_per_batch == 1
    assert report_usecase.report_codex_evidence_builder.target_selection.included_check_ids == frozenset({"C07"})
    assert report_usecase.report_codex_evidence_builder.target_selection.included_finding_codes == frozenset(
        {"CONCLUSION_MISMATCH_001"}
    )
    assert report_usecase.report_codex_evidence_builder.target_selection.excluded_check_ids == frozenset({"C04"})
    assert report_usecase.report_codex_evidence_builder.target_selection.priority_check_ids == ("C07", "C04")
    assert ptr_usecase.ptr_codex_evidence_builder.target_selection.max_targets_per_batch == 1
    assert ptr_usecase.ptr_codex_evidence_builder.target_selection.included_check_ids == frozenset({"C07"})


def test_mandatory_codex_cli_execution_can_be_monkeypatched(
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
                            "metadata": {},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("app.infrastructure.codex.codex_cli_runner.subprocess.run", fake_run)
    settings = Settings(
        codex_audit_timeout_seconds=33,
        codex_audit_runtime_dir=str(tmp_path / "runtime" / "codex_audit"),
        _env_file=None,
    )

    service = build_codex_audit_service(settings)
    assert service is not None
    assert isinstance(service.runner, CodexCliRunner)

    request, package = _review_contract()
    reviews = service.review(request, package)

    assert calls
    assert reviews[0].status is CodexReviewStatus.SUCCEEDED
    assert reviews[0].verdict is CodexReviewVerdict.CONFIRM
    assert reviews[0].metadata["parser"] == "codex_review_output"


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
