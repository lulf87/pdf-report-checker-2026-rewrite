from __future__ import annotations

from threading import Lock
from typing import Any

from app.application.codex_audit_scheduler import CodexAuditJob
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewResult
from app.domain.result import CheckResult, CheckStatus, CheckSummary
from app.domain.task import (
    CodexAuditProgressStatus,
    TaskCheckProgress,
    TaskCheckProgressStatus,
    TaskCodexAuditProgress,
    TaskProgressDetails,
    TaskProgressPhase,
)
from app.rules.report.runner import default_report_rules


PHASE_LABELS: dict[TaskProgressPhase, str] = {
    TaskProgressPhase.UPLOAD: "上传任务",
    TaskProgressPhase.PARSE: "PDF解析",
    TaskProgressPhase.EXTRACT: "结构化抽取",
    TaskProgressPhase.RULES: "规则初筛",
    TaskProgressPhase.EVIDENCE: "证据准备",
    TaskProgressPhase.CODEX_AUDIT: "LLM/Codex复核",
    TaskProgressPhase.FINALIZE: "结果整理",
    TaskProgressPhase.COMPLETED: "已完成",
    TaskProgressPhase.ERROR: "失败",
}


class ReportCheckProgressReporter:
    """Writes user-facing report-check progress details to the task state."""

    def __init__(self, task_service: TaskService, task_id: str) -> None:
        self.task_service = task_service
        self.task_id = task_id
        self._lock = Lock()
        self._checks = [
            TaskCheckProgress(check_id=rule.check_id, check_name=rule.check_name)
            for rule in default_report_rules()
        ]
        self._check_positions = {check.check_id: index for index, check in enumerate(self._checks)}
        self._codex_audit = TaskCodexAuditProgress(enabled=False)
        self._phase = TaskProgressPhase.UPLOAD
        self._current_check_id: str | None = None
        self._current_check_name: str | None = None
        self._completed_batches = 0
        self._completed_reviews = 0

    def upload(self) -> None:
        self._write(TaskProgressPhase.UPLOAD, 1, "queued report check")

    def parse(self) -> None:
        self._write(TaskProgressPhase.PARSE, 5, "parsing report pdf")

    def extract(self) -> None:
        self._write(TaskProgressPhase.EXTRACT, 15, "extracting report document")

    def rules(self) -> None:
        self._write(TaskProgressPhase.RULES, 25, "running report rules")

    def evidence(self) -> None:
        self._write(TaskProgressPhase.EVIDENCE, 45, "building Codex evidence")

    def finalize(self, results: list[CheckResult]) -> None:
        self._apply_check_results(results)
        self._write(TaskProgressPhase.FINALIZE, 95, "finalizing Codex audit")

    def completed(self, results: list[CheckResult]) -> None:
        self._apply_check_results(results)
        if self._codex_audit.enabled and self._codex_audit.status is not CodexAuditProgressStatus.FAILED:
            self._codex_audit.status = CodexAuditProgressStatus.COMPLETED
        self._write(TaskProgressPhase.COMPLETED, 100, "completed")

    def error(self, error_message: str, *, error_code: str = "PROCESSING_ERROR") -> TaskProgressDetails:
        details = self._details(
            TaskProgressPhase.ERROR,
            error_code=error_code,
            error_message=_sanitize_progress_text(error_message),
        )
        self.task_service.update_progress(
            self.task_id,
            progress=self.task_service.get_task(self.task_id).progress,
            current_step="error",
            progress_details=details,
        )
        return details

    def on_check_start(self, check_id: str, check_name: str) -> None:
        with self._lock:
            self._current_check_id = check_id
            self._current_check_name = check_name
            index = self._check_positions.get(check_id)
            if index is None:
                return
            self._checks[index] = self._checks[index].model_copy(
                update={"status": TaskCheckProgressStatus.RUNNING, "progress": 30}
            )
            overall_progress = _rule_overall_progress(index, len(self._checks))
        self._write(TaskProgressPhase.RULES, overall_progress, f"running report rule {check_id}")

    def on_check_complete(self, result: CheckResult) -> None:
        with self._lock:
            self._current_check_id = result.check_id
            self._current_check_name = result.check_name
            index = self._check_positions.get(result.check_id)
            if index is not None:
                self._checks[index] = _progress_for_result(result)
                overall_progress = _rule_overall_progress(index + 1, len(self._checks))
            else:
                overall_progress = 45
        self._write(TaskProgressPhase.RULES, overall_progress, f"completed report rule {result.check_id}")

    def codex_targets_ready(self, jobs: list[CodexAuditJob], *, max_targets_per_batch: int | None) -> None:
        total_targets = sum(len(job.request.targets) for job in jobs)
        first_target = next((target for job in jobs for target in job.request.targets), None)
        self._completed_batches = 0
        self._completed_reviews = 0
        self._codex_audit = TaskCodexAuditProgress(
            enabled=bool(jobs),
            status=CodexAuditProgressStatus.RUNNING if jobs else CodexAuditProgressStatus.COMPLETED,
            current_check_id=first_target.check_id if first_target is not None else None,
            current_target_type=first_target.target_type.value if first_target is not None else None,
            total_reviews_count=total_targets,
            total_batches_count=len(jobs),
            max_targets_per_batch=max_targets_per_batch,
        )
        self._write(TaskProgressPhase.CODEX_AUDIT, 60, "running Codex audit")

    def on_codex_job_start(self, job: CodexAuditJob) -> None:
        first_target = job.request.targets[0] if job.request.targets else None
        self._codex_audit.status = CodexAuditProgressStatus.RUNNING
        if first_target is not None:
            self._codex_audit.current_check_id = first_target.check_id
            self._codex_audit.current_target_type = first_target.target_type.value
        self._write(TaskProgressPhase.CODEX_AUDIT, self._codex_overall_progress(), "running Codex audit batch")

    def on_codex_job_complete(self, job: CodexAuditJob, reviews: list[CodexReviewResult]) -> None:
        del job
        self._completed_batches += 1
        self._completed_reviews += len(reviews)
        self._codex_audit.completed_batches_count = self._completed_batches
        self._codex_audit.completed_reviews_count = min(
            self._completed_reviews,
            self._codex_audit.total_reviews_count,
        )
        failed_error_code = _first_failed_error_code(reviews)
        if failed_error_code is not None:
            self._codex_audit.status = CodexAuditProgressStatus.FAILED
            self._codex_audit.error_code = failed_error_code
            if failed_error_code == "CODEX_TIMEOUT":
                self._codex_audit.last_retry_reason = "CODEX_TIMEOUT"
        elif self._completed_batches >= self._codex_audit.total_batches_count:
            self._codex_audit.status = CodexAuditProgressStatus.COMPLETED
        self._write(TaskProgressPhase.CODEX_AUDIT, self._codex_overall_progress(), "completed Codex audit batch")

    def on_codex_progress_event(self, event: dict[str, Any]) -> None:
        status = event.get("status")
        if status == "retrying":
            self._codex_audit.status = CodexAuditProgressStatus.RETRYING
            self._codex_audit.retry_count = max(self._codex_audit.retry_count, int(event.get("retry_count") or 1))
            reason = event.get("last_retry_reason")
            self._codex_audit.last_retry_reason = str(reason) if reason else None
        elif status == "failed":
            self._codex_audit.status = CodexAuditProgressStatus.FAILED
            error_code = event.get("error_code")
            self._codex_audit.error_code = str(error_code) if error_code else self._codex_audit.error_code
        self._write(TaskProgressPhase.CODEX_AUDIT, self._codex_overall_progress(), "updating Codex audit progress")

    def snapshot(self) -> TaskProgressDetails:
        return self._details(self._phase)

    def _write(
        self,
        phase: TaskProgressPhase,
        progress: int,
        current_step: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._phase = phase
        self.task_service.update_progress(
            self.task_id,
            progress=progress,
            current_step=current_step,
            progress_details=self._details(phase, error_code=error_code, error_message=error_message),
        )

    def _details(
        self,
        phase: TaskProgressPhase,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> TaskProgressDetails:
        return TaskProgressDetails(
            phase=phase,
            phase_label=PHASE_LABELS[phase],
            current_check_id=self._current_check_id,
            current_check_name=self._current_check_name,
            checks=list(self._checks),
            codex_audit=self._codex_audit,
            error_code=error_code,
            error_message=error_message,
        )

    def _apply_check_results(self, results: list[CheckResult]) -> None:
        for result in results:
            index = self._check_positions.get(result.check_id)
            if index is not None:
                self._checks[index] = _progress_for_result(result)

    def _codex_overall_progress(self) -> int:
        total = max(1, self._codex_audit.total_batches_count)
        ratio = min(1.0, self._completed_batches / total)
        return round(60 + (35 * ratio))


def _progress_for_result(result: CheckResult) -> TaskCheckProgress:
    summary = CheckSummary.from_results([result])
    return TaskCheckProgress(
        check_id=result.check_id,
        check_name=result.check_name,
        status=_check_status_for_result(result.status),
        progress=100,
        candidate_findings_count=summary.candidate_findings_count,
        confirmed_errors_count=summary.confirmed_errors_count,
        manual_review_required_count=summary.manual_review_required_count,
        refuted_findings_count=summary.refuted_findings_count,
    )


def _check_status_for_result(status: CheckStatus) -> TaskCheckProgressStatus:
    if status is CheckStatus.PASS:
        return TaskCheckProgressStatus.PASSED
    if status is CheckStatus.FAIL:
        return TaskCheckProgressStatus.FAILED
    if status is CheckStatus.REVIEW:
        return TaskCheckProgressStatus.NEEDS_REVIEW
    if status is CheckStatus.SKIP:
        return TaskCheckProgressStatus.SKIPPED
    return TaskCheckProgressStatus.ERROR


def _rule_overall_progress(position: int, total: int) -> int:
    if total <= 0:
        return 45
    ratio = min(1.0, max(0.0, position / total))
    return round(25 + (20 * ratio))


def _first_failed_error_code(reviews: list[CodexReviewResult]) -> str | None:
    for review in reviews:
        if review.error is not None:
            return review.error.code
    return None


def _sanitize_progress_text(value: str) -> str:
    return value.replace("/Users/", "[redacted]/")


__all__ = ["ReportCheckProgressReporter"]
