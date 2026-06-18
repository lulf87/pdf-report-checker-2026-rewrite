from __future__ import annotations

from pathlib import Path

from app.application.codex_audit_service import CodexAuditService
from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.core.config import Settings
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex import CodexCliRunner, CodexCliRunnerConfig, FakeCodexRunner, PromptBuilder


def build_codex_audit_service(settings: Settings) -> CodexAuditService | None:
    """Build the optional runtime Codex audit service from explicit settings."""

    if not settings.codex_audit_enabled:
        return None
    if settings.codex_audit_backend == "disabled":
        return None

    runner = _build_codex_runner(settings)
    return CodexAuditService(
        evidence_writer=EvidencePackageWriter(Path(settings.codex_audit_runtime_dir)),
        prompt_builder=PromptBuilder(),
        runner=runner,
    )


def build_ptr_compare_usecase(
    settings: Settings,
    *,
    task_service: TaskService,
) -> PTRCompareUseCase:
    codex_audit_service = build_codex_audit_service(settings)
    return PTRCompareUseCase(
        task_service=task_service,
        codex_audit_service=codex_audit_service,
        codex_audit_enabled=codex_audit_service is not None,
    )


def build_report_check_usecase(
    settings: Settings,
    *,
    task_service: TaskService,
) -> ReportCheckUseCase:
    codex_audit_service = build_codex_audit_service(settings)
    return ReportCheckUseCase(
        task_service=task_service,
        codex_audit_service=codex_audit_service,
        codex_audit_enabled=codex_audit_service is not None,
    )


def _build_codex_runner(settings: Settings):
    if settings.codex_audit_backend == "fake":
        return FakeCodexRunner()

    return CodexCliRunner(
        CodexCliRunnerConfig(
            enabled=True,
            allow_real_execution=settings.codex_audit_allow_real_execution,
            sandbox="read-only",
            timeout_seconds=settings.codex_audit_timeout_seconds,
        )
    )


__all__ = [
    "build_codex_audit_service",
    "build_ptr_compare_usecase",
    "build_report_check_usecase",
]
