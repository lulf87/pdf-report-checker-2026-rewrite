from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.application.task_repository import (
    InMemoryTaskRepository,
    TaskNotFoundError,
    TaskRepository,
    TaskResult,
    TaskResultNotFoundError,
)
from app.domain.result import CheckResult, CheckSummary
from app.domain.task import TaskState, TaskStatus, TaskType
from app.domain.task import InputFileRef


class TaskService:
    """Task lifecycle service used by application use cases.

    The repository is replaceable. It keeps only task metadata and structured
    results; uploaded bytes remain in infrastructure storage.
    """

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or InMemoryTaskRepository()

    def create_task(
        self,
        task_type: TaskType,
        *,
        input_files: list[InputFileRef] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskStatus:
        now = datetime.now(timezone.utc)
        task = TaskStatus(
            task_id=str(uuid4()),
            task_type=task_type,
            status=TaskState.PENDING,
            progress=0,
            current_step="created",
            input_files=input_files or [],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        return self.repository.create_task(task)

    def get_task(self, task_id: str) -> TaskStatus:
        return self.repository.get_task(task_id)

    def set_input_files(self, task_id: str, input_files: list[InputFileRef]) -> TaskStatus:
        return self._mutate_task(task_id, input_files=input_files)

    def start_task(
        self,
        task_id: str,
        *,
        current_step: str | None = None,
        progress: int = 1,
    ) -> TaskStatus:
        return self._mutate_task(
            task_id,
            status=TaskState.PROCESSING,
            progress=progress,
            current_step=current_step or "processing",
        )

    def update_progress(
        self,
        task_id: str,
        *,
        progress: int,
        current_step: str | None = None,
        log: str | None = None,
    ) -> TaskStatus:
        task = self.get_task(task_id)
        logs = list(task.logs)
        if log:
            logs.append(log)
        return self._mutate_task(
            task_id,
            progress=progress,
            current_step=current_step if current_step is not None else task.current_step,
            logs=logs,
        )

    def complete_task(
        self,
        task_id: str,
        check_results: list[CheckResult],
        *,
        diagnostics: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskStatus:
        task = self.get_task(task_id)
        result_metadata = metadata or {}
        summary = CheckSummary.from_results(check_results)
        _apply_codex_audit_summary_metadata(summary, result_metadata.get("codex_audit"))
        result = TaskResult(
            task_id=task_id,
            task_type=task.task_type,
            summary=summary,
            check_results=check_results,
            findings=[finding for result in check_results for finding in result.findings],
            input_files=task.input_files,
            diagnostics=diagnostics or [],
            metadata=result_metadata,
        )
        self.repository.save_result(task_id, result)

        return self._mutate_task(
            task_id,
            status=TaskState.COMPLETED,
            progress=100,
            current_step="completed",
            result_ref=task_id,
            error_message=None,
        )

    def update_result_metadata(self, task_id: str, metadata: dict[str, Any]) -> None:
        result = self.repository.get_result(task_id)
        self.repository.save_result(task_id, result.model_copy(update={"metadata": metadata}))

    def fail_task(self, task_id: str, error_message: str) -> TaskStatus:
        return self.repository.mark_failed(task_id, error_message)

    def get_result(self, task_id: str) -> TaskResult:
        return self.repository.get_result(task_id)

    def list_tasks(self) -> list[TaskStatus]:
        return self.repository.list_tasks()

    def _mutate_task(self, task_id: str, **updates: Any) -> TaskStatus:
        return self.repository.update_task(task_id, **updates)


def _apply_codex_audit_summary_metadata(summary: CheckSummary, codex_audit_metadata: Any) -> None:
    if not isinstance(codex_audit_metadata, dict):
        return

    audit_scope = codex_audit_metadata.get("audit_scope")
    if isinstance(audit_scope, str):
        summary.audit_scope = audit_scope

    full_audit = codex_audit_metadata.get("full_audit")
    if isinstance(full_audit, bool):
        summary.full_audit = full_audit

    final_audit_status = codex_audit_metadata.get("final_audit_status")
    if isinstance(final_audit_status, str):
        summary.final_audit_status = final_audit_status


__all__ = [
    "TaskNotFoundError",
    "TaskRepository",
    "TaskResult",
    "TaskResultNotFoundError",
    "TaskService",
]
