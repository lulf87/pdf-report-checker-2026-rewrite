from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from app.application.task_repository import (
    TaskNotFoundError,
    TaskResult,
    TaskResultNotFoundError,
)
from app.domain.task import TaskState, TaskStatus


class FileTaskRepository:
    """JSON-backed task repository that survives backend restarts."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def create_task(self, task: TaskStatus) -> TaskStatus:
        with self._lock:
            task_dir = self._task_dir(task.task_id)
            task_dir.mkdir(parents=True, exist_ok=False)
            self._write_model(task_dir / "task.json", task)
            return task.model_copy(deep=True)

    def get_task(self, task_id: str) -> TaskStatus:
        with self._lock:
            path = self._task_dir(task_id) / "task.json"
            if not path.is_file():
                raise TaskNotFoundError(task_id)
            return TaskStatus.model_validate_json(path.read_text(encoding="utf-8"))

    def update_task(self, task_id: str, **updates: Any) -> TaskStatus:
        with self._lock:
            task = self.get_task(task_id)
            data = task.model_dump()
            data.update(updates)
            data["updated_at"] = datetime.now(timezone.utc)
            updated = TaskStatus.model_validate(data)
            self._write_model(self._task_dir(task_id) / "task.json", updated)
            return updated.model_copy(deep=True)

    def save_result(self, task_id: str, result: TaskResult) -> TaskResult:
        with self._lock:
            task_dir = self._task_dir(task_id)
            if not (task_dir / "task.json").is_file():
                raise TaskNotFoundError(task_id)
            self._write_model(task_dir / "result.json", result)
            return result.model_copy(deep=True)

    def get_result(self, task_id: str) -> TaskResult:
        with self._lock:
            path = self._task_dir(task_id) / "result.json"
            if not path.is_file():
                raise TaskResultNotFoundError(task_id)
            return TaskResult.model_validate_json(path.read_text(encoding="utf-8"))

    def mark_failed(self, task_id: str, error_message: str) -> TaskStatus:
        return self.update_task(
            task_id,
            status=TaskState.ERROR,
            current_step="error",
            error_message=error_message,
        )

    def list_tasks(self) -> list[TaskStatus]:
        with self._lock:
            tasks: list[TaskStatus] = []
            for path in self.root_dir.glob("*/task.json"):
                try:
                    tasks.append(TaskStatus.model_validate_json(path.read_text(encoding="utf-8")))
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
            return sorted(tasks, key=lambda task: task.created_at)

    def _task_dir(self, task_id: str) -> Path:
        if not task_id or not re.fullmatch(r"[A-Za-z0-9_.:-]+", task_id):
            raise ValueError("invalid task id for file task repository")
        path = (self.root_dir / task_id).resolve()
        if not path.is_relative_to(self.root_dir):
            raise ValueError("task path must stay under repository root")
        return path

    @staticmethod
    def _write_model(path: Path, model: TaskStatus | TaskResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = model.model_dump_json(indent=2)
        file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


__all__ = ["FileTaskRepository"]
