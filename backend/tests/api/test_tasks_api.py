from fastapi.testclient import TestClient

from app.api.routes_tasks import get_task_service
from app.application.task_service import TaskService
from app.domain.task import TaskState, TaskType
from app.main import create_app


def _client_with_task_service() -> tuple[TestClient, TaskService]:
    task_service = TaskService()
    app = create_app()
    app.dependency_overrides[get_task_service] = lambda: task_service
    return TestClient(app), task_service


def test_task_result_endpoint_returns_202_while_task_is_processing() -> None:
    client, task_service = _client_with_task_service()
    task = task_service.create_task(TaskType.REPORT_CHECK)
    task_service.start_task(task.task_id, current_step="extracting")

    response = client.get(f"/api/tasks/{task.task_id}/result")

    assert response.status_code == 202
    assert response.json()["detail"] == "Task still processing"


def test_task_result_endpoint_returns_failure_detail_for_error_task() -> None:
    client, task_service = _client_with_task_service()
    task = task_service.create_task(TaskType.PTR_COMPARE)
    task_service.fail_task(task.task_id, "PTR extraction failed")

    response = client.get(f"/api/tasks/{task.task_id}/result")

    assert response.status_code == 400
    assert response.json()["detail"] == "PTR extraction failed"


def test_task_export_rejects_unsupported_format_before_task_lookup() -> None:
    client, _ = _client_with_task_service()

    response = client.get("/api/tasks/missing/export", params={"format": "csv"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported export format"


def test_task_export_rejects_unfinished_task() -> None:
    client, task_service = _client_with_task_service()
    task = task_service.create_task(TaskType.REPORT_CHECK)
    task_service.start_task(task.task_id)

    response = client.get(f"/api/tasks/{task.task_id}/export", params={"format": "json"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Task not completed yet"
    assert task_service.get_task(task.task_id).status == TaskState.PROCESSING
