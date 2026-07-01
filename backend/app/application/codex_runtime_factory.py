from __future__ import annotations

from pathlib import Path

from app.application.codex_audit_service import CodexAuditService
from app.application.codex_audit_scheduler import CodexAuditScheduler
from app.application.codex_audit_targeting import parse_csv_values
from app.application.ptr_codex_evidence_builder import PtrCodexEvidenceBuilder
from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.report_codex_evidence_builder import ReportCodexEvidenceBuilder
from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.core.config import Settings
from app.infrastructure.audit.codex_review_cache import CodexReviewCache
from app.infrastructure.audit.evidence_package_writer import EvidencePackageWriter
from app.infrastructure.codex import CodexCliRunner, CodexCliRunnerConfig, PromptBuilder


def build_codex_audit_service(settings: Settings) -> CodexAuditService:
    """Build the mandatory local Codex CLI audit service for product runtime."""

    runner = _build_codex_runner(settings)
    return CodexAuditService(
        evidence_writer=EvidencePackageWriter(Path(settings.codex_audit_runtime_dir)),
        prompt_builder=PromptBuilder(),
        runner=runner,
        review_cache=CodexReviewCache(Path(settings.codex_audit_cache_dir)),
        missing_target_retry_batch_size=settings.codex_audit_missing_target_retry_batch_size,
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
        ptr_codex_evidence_builder=_build_ptr_codex_evidence_builder(settings),
        codex_audit_scheduler=CodexAuditScheduler(max_parallel_jobs=settings.codex_audit_max_parallel_jobs),
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
        report_codex_evidence_builder=_build_report_codex_evidence_builder(settings),
        codex_audit_scheduler=CodexAuditScheduler(max_parallel_jobs=settings.codex_audit_max_parallel_jobs),
    )


def _build_codex_runner(settings: Settings) -> CodexCliRunner:
    return CodexCliRunner(
        CodexCliRunnerConfig(
            executable=settings.codex_cli_path,
            enabled=True,
            allow_real_execution=True,
            sandbox=settings.codex_audit_sandbox,
            timeout_seconds=settings.codex_audit_timeout_seconds,
            ephemeral=settings.codex_audit_ephemeral,
        )
    )


def _build_report_codex_evidence_builder(settings: Settings) -> ReportCodexEvidenceBuilder:
    return ReportCodexEvidenceBuilder(
        max_targets_per_task=settings.codex_audit_max_targets_per_task,
        max_targets_per_batch=settings.codex_audit_max_targets_per_batch,
        included_check_ids=settings.codex_audit_included_check_ids,
        included_finding_codes=settings.codex_audit_included_finding_codes,
        excluded_check_ids=settings.codex_audit_excluded_check_ids,
        priority_check_ids=settings.codex_audit_priority_check_ids,
    )


def _build_ptr_codex_evidence_builder(settings: Settings) -> PtrCodexEvidenceBuilder:
    priority_values = parse_csv_values(settings.codex_audit_priority_check_ids)
    priority_check_ids = settings.codex_audit_priority_check_ids if any(value.startswith("PTR_") for value in priority_values) else None
    return PtrCodexEvidenceBuilder(
        max_targets_per_task=settings.codex_audit_max_targets_per_task,
        max_targets_per_batch=settings.codex_audit_max_targets_per_batch,
        included_check_ids=settings.codex_audit_included_check_ids,
        included_finding_codes=settings.codex_audit_included_finding_codes,
        excluded_check_ids=settings.codex_audit_excluded_check_ids,
        priority_check_ids=priority_check_ids,
    )


__all__ = [
    "build_codex_audit_service",
    "build_ptr_compare_usecase",
    "build_report_check_usecase",
]
