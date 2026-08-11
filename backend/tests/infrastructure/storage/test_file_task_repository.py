from datetime import datetime, timezone

import pytest

from app.application.task_repository import TaskNotFoundError, TaskResult, TaskResultNotFoundError
from app.domain.result import CheckResult, CheckStatus, CheckSummary
from app.domain.task import TaskState, TaskStatus, TaskType
from app.infrastructure.storage.file_task_repository import FileTaskRepository


def _task(task_id: str = "task-persisted") -> TaskStatus:
    now = datetime.now(timezone.utc)
    return TaskStatus(
        task_id=task_id,
        task_type=TaskType.PTR_COMPARE,
        status=TaskState.PENDING,
        progress=0,
        current_step="created",
        created_at=now,
        updated_at=now,
    )


def _result(task_id: str) -> TaskResult:
    check = CheckResult(
        task_id=task_id,
        check_id="PTR_SCOPE",
        check_name="PTR scope",
        status=CheckStatus.PASS,
        summary="covered",
        metadata={"ptr_comparison_details": {"requirements_count": 1}},
    )
    return TaskResult(
        task_id=task_id,
        task_type=TaskType.PTR_COMPARE,
        summary=CheckSummary.from_results([check]),
        check_results=[check],
        metadata={"source": "restart-test"},
    )


def test_file_task_repository_restores_task_and_result_after_recreation(tmp_path) -> None:
    writer = FileTaskRepository(tmp_path / "tasks")
    task = writer.create_task(_task())
    writer.update_task(task.task_id, status=TaskState.COMPLETED, progress=100)
    writer.save_result(task.task_id, _result(task.task_id))

    reader = FileTaskRepository(tmp_path / "tasks")

    assert reader.get_task(task.task_id).status == TaskState.COMPLETED
    assert reader.get_result(task.task_id).metadata == {"source": "restart-test"}
    assert reader.get_result(task.task_id).check_results[0].metadata["ptr_comparison_details"] == {
        "requirements_count": 1
    }


def test_file_task_repository_updates_atomically_and_returns_deep_values(tmp_path) -> None:
    repository = FileTaskRepository(tmp_path / "tasks")
    task = repository.create_task(_task())
    repository.save_result(task.task_id, _result(task.task_id))

    returned = repository.get_result(task.task_id)
    returned.metadata["source"] = "mutated"
    updated = repository.update_task(task.task_id, progress=75, current_step="export ready")

    assert updated.progress == 75
    assert repository.get_result(task.task_id).metadata["source"] == "restart-test"
    assert not list((tmp_path / "tasks").rglob(".*.tmp"))


def test_file_task_repository_ignores_corrupt_entries_when_listing(tmp_path) -> None:
    repository = FileTaskRepository(tmp_path / "tasks")
    repository.create_task(_task("valid-task"))
    corrupt_dir = tmp_path / "tasks" / "corrupt-task"
    corrupt_dir.mkdir()
    (corrupt_dir / "task.json").write_text("{not-json", encoding="utf-8")

    assert [task.task_id for task in repository.list_tasks()] == ["valid-task"]


def test_file_task_repository_preserves_missing_errors_and_rejects_unsafe_ids(tmp_path) -> None:
    repository = FileTaskRepository(tmp_path / "tasks")

    with pytest.raises(TaskNotFoundError):
        repository.get_task("missing")
    with pytest.raises(TaskResultNotFoundError):
        repository.get_result("missing")
    with pytest.raises(ValueError):
        repository.get_task("../outside")
