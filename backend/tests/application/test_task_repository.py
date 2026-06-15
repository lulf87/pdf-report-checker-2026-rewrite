from datetime import datetime, timezone

import pytest

from app.application.task_repository import (
    InMemoryTaskRepository,
    TaskNotFoundError,
    TaskRepository,
    TaskResult,
    TaskResultNotFoundError,
)
from app.domain.result import CheckResult, CheckStatus, CheckSummary
from app.domain.task import InputFileRef, TaskState, TaskStatus, TaskType


def _task(task_id: str = "task-1", task_type: TaskType = TaskType.REPORT_CHECK) -> TaskStatus:
    now = datetime.now(timezone.utc)
    return TaskStatus(
        task_id=task_id,
        task_type=task_type,
        status=TaskState.PENDING,
        progress=0,
        current_step="created",
        created_at=now,
        updated_at=now,
    )


def _check_result(task_id: str) -> CheckResult:
    return CheckResult(
        task_id=task_id,
        check_id="C01",
        check_name="首页与第三页一致性",
        status=CheckStatus.PASS,
        summary="字段一致",
    )


def _task_result(task_id: str) -> TaskResult:
    result = _check_result(task_id)
    return TaskResult(
        task_id=task_id,
        task_type=TaskType.REPORT_CHECK,
        summary=CheckSummary.from_results([result]),
        check_results=[result],
        input_files=[InputFileRef(file_id="file-1", file_name="report.pdf")],
        diagnostics=["repository test"],
        metadata={"source": "unit-test"},
    )


def test_in_memory_task_repository_satisfies_protocol_and_stores_task_lifecycle() -> None:
    repository: TaskRepository = InMemoryTaskRepository()
    created = repository.create_task(_task())

    updated = repository.update_task(
        created.task_id,
        status=TaskState.PROCESSING,
        progress=40,
        current_step="running rules",
        logs=["started"],
    )

    assert updated.status == TaskState.PROCESSING
    assert updated.progress == 40
    assert updated.current_step == "running rules"
    assert updated.logs == ["started"]
    assert updated.updated_at >= created.updated_at
    assert repository.get_task(created.task_id).status == TaskState.PROCESSING


def test_in_memory_task_repository_saves_results_and_returns_deep_copies() -> None:
    repository = InMemoryTaskRepository()
    task = repository.create_task(_task())
    repository.save_result(task.task_id, _task_result(task.task_id))

    returned = repository.get_result(task.task_id)
    returned.diagnostics.append("mutated outside repository")

    assert repository.get_result(task.task_id).summary.pass_count == 1
    assert repository.get_result(task.task_id).diagnostics == ["repository test"]


def test_in_memory_task_repository_marks_failed_and_lists_tasks() -> None:
    repository = InMemoryTaskRepository()
    first = repository.create_task(_task("task-1", TaskType.REPORT_CHECK))
    second = repository.create_task(_task("task-2", TaskType.PTR_COMPARE))

    failed = repository.mark_failed(first.task_id, "PDF parse failed")

    assert failed.status == TaskState.ERROR
    assert failed.current_step == "error"
    assert failed.error_message == "PDF parse failed"
    assert [task.task_id for task in repository.list_tasks()] == [first.task_id, second.task_id]


def test_in_memory_task_repository_raises_for_missing_task_or_result() -> None:
    repository = InMemoryTaskRepository()

    with pytest.raises(TaskNotFoundError):
        repository.get_task("missing")
    with pytest.raises(TaskNotFoundError):
        repository.update_task("missing", status=TaskState.PROCESSING)
    with pytest.raises(TaskNotFoundError):
        repository.save_result("missing", _task_result("missing"))
    with pytest.raises(TaskResultNotFoundError):
        repository.get_result("missing")
