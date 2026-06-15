from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.finding import Finding
from app.domain.result import CheckResult, CheckSummary
from app.domain.task import TaskState, TaskStatus, TaskType
from app.domain.task import InputFileRef


class TaskNotFoundError(KeyError):
    """Raised when a task id is not present in the task service."""


class TaskResultNotFoundError(KeyError):
    """Raised when a task has no stored result."""


class TaskResult(BaseModel):
    task_id: str
    task_type: TaskType
    summary: CheckSummary
    check_results: list[CheckResult] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    input_files: list[InputFileRef] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskService:
    """In-memory task lifecycle service used by application use cases.

    The repository is intentionally replaceable. It keeps only task metadata
    and structured results; uploaded bytes remain in infrastructure storage.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskStatus] = {}
        self._results: dict[str, TaskResult] = {}
        self._lock = RLock()

    def create_task(
        self,
        task_type: TaskType,
        *,
        input_files: list[InputFileRef] | None = None,
    ) -> TaskStatus:
        now = datetime.now(timezone.utc)
        task = TaskStatus(
            task_id=str(uuid4()),
            task_type=task_type,
            status=TaskState.PENDING,
            progress=0,
            current_step="created",
            input_files=input_files or [],
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> TaskStatus:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(task_id)
            return task.model_copy(deep=True)

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
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(task_id)
            result = TaskResult(
                task_id=task_id,
                task_type=task.task_type,
                summary=CheckSummary.from_results(check_results),
                check_results=check_results,
                findings=[finding for result in check_results for finding in result.findings],
                input_files=task.input_files,
                diagnostics=diagnostics or [],
                metadata=metadata or {},
            )
            self._results[task_id] = result

        return self._mutate_task(
            task_id,
            status=TaskState.COMPLETED,
            progress=100,
            current_step="completed",
            result_ref=task_id,
            error_message=None,
        )

    def fail_task(self, task_id: str, error_message: str) -> TaskStatus:
        return self._mutate_task(
            task_id,
            status=TaskState.ERROR,
            current_step="error",
            error_message=error_message,
        )

    def get_result(self, task_id: str) -> TaskResult:
        with self._lock:
            result = self._results.get(task_id)
            if result is None:
                raise TaskResultNotFoundError(task_id)
            return result.model_copy(deep=True)

    def _mutate_task(self, task_id: str, **updates: Any) -> TaskStatus:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(task_id)
            data = task.model_dump()
            data.update(updates)
            data["updated_at"] = datetime.now(timezone.utc)
            updated = TaskStatus.model_validate(data)
            self._tasks[task_id] = updated
            return updated.model_copy(deep=True)


__all__ = [
    "TaskNotFoundError",
    "TaskResult",
    "TaskResultNotFoundError",
    "TaskService",
]
