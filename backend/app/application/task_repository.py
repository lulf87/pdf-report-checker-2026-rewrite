from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.domain.finding import Finding
from app.domain.result import CheckResult, CheckSummary
from app.domain.task import InputFileRef, TaskState, TaskStatus, TaskType


class TaskNotFoundError(KeyError):
    """Raised when a task id is not present in the task repository."""


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


class TaskRepository(Protocol):
    def create_task(self, task: TaskStatus) -> TaskStatus:
        ...

    def get_task(self, task_id: str) -> TaskStatus:
        ...

    def update_task(self, task_id: str, **updates: Any) -> TaskStatus:
        ...

    def save_result(self, task_id: str, result: TaskResult) -> TaskResult:
        ...

    def get_result(self, task_id: str) -> TaskResult:
        ...

    def mark_failed(self, task_id: str, error_message: str) -> TaskStatus:
        ...

    def list_tasks(self) -> list[TaskStatus]:
        ...


class InMemoryTaskRepository:
    """Thread-safe in-memory task repository for local development and tests."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskStatus] = {}
        self._results: dict[str, TaskResult] = {}
        self._lock = RLock()

    def create_task(self, task: TaskStatus) -> TaskStatus:
        with self._lock:
            self._tasks[task.task_id] = task.model_copy(deep=True)
            return task.model_copy(deep=True)

    def get_task(self, task_id: str) -> TaskStatus:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(task_id)
            return task.model_copy(deep=True)

    def update_task(self, task_id: str, **updates: Any) -> TaskStatus:
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

    def save_result(self, task_id: str, result: TaskResult) -> TaskResult:
        with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(task_id)
            self._results[task_id] = result.model_copy(deep=True)
            return result.model_copy(deep=True)

    def get_result(self, task_id: str) -> TaskResult:
        with self._lock:
            result = self._results.get(task_id)
            if result is None:
                raise TaskResultNotFoundError(task_id)
            return result.model_copy(deep=True)

    def mark_failed(self, task_id: str, error_message: str) -> TaskStatus:
        return self.update_task(
            task_id,
            status=TaskState.ERROR,
            current_step="error",
            error_message=error_message,
        )

    def list_tasks(self) -> list[TaskStatus]:
        with self._lock:
            return [task.model_copy(deep=True) for task in self._tasks.values()]


__all__ = [
    "InMemoryTaskRepository",
    "TaskNotFoundError",
    "TaskRepository",
    "TaskResult",
    "TaskResultNotFoundError",
]
