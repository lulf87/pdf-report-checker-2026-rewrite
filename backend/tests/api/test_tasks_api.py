from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes_tasks import get_task_service
from app.application.task_service import TaskService
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import TaskState, TaskType
from app.infrastructure.storage.file_task_repository import FileTaskRepository
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


def test_task_export_rejects_unsupported_view_before_task_lookup() -> None:
    client, _ = _client_with_task_service()

    response = client.get("/api/tasks/missing/export", params={"format": "json", "view": "internal"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported export view"


def test_task_final_export_hides_refuted_findings() -> None:
    client, task_service = _client_with_task_service()
    task = task_service.create_task(TaskType.REPORT_CHECK)
    finding = Finding(
        id="refuted-finding",
        task_id=task.task_id,
        check_id="C03",
        severity=FindingSeverity.WARN,
        code="DATE_FIELD_MISSING",
        message="规则候选",
        missing_evidence=[MissingEvidence(label="中文铭牌", reason="测试候选")],
        metadata={"final_status": "refuted", "codex_review_id": "review-1"},
    )
    task_service.complete_task(
        task.task_id,
        [
            CheckResult(
                task_id=task.task_id,
                check_id="C03",
                check_name="生产日期格式一致性",
                status=CheckStatus.REVIEW,
                summary="规则候选 1 项",
                findings=[finding],
            )
        ],
        metadata={"codex_audit": {"final_audit_status": "passed"}},
    )

    response = client.get(
        f"/api/tasks/{task.task_id}/export",
        params={"format": "json", "view": "final"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["view"] == "final"
    assert payload["summary"]["final_audit_status"] == "passed"
    assert payload["findings"] == []
    assert payload["check_results"][0]["status"] == "pass"
    assert "codex_reviews" not in payload["check_results"][0]


def test_task_export_rejects_unfinished_task() -> None:
    client, task_service = _client_with_task_service()
    task = task_service.create_task(TaskType.REPORT_CHECK)
    task_service.start_task(task.task_id)

    response = client.get(f"/api/tasks/{task.task_id}/export", params={"format": "json"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Task not completed yet"
    assert task_service.get_task(task.task_id).status == TaskState.PROCESSING


@pytest.mark.parametrize(
    ("export_format", "content_type"),
    [
        ("json", "application/json"),
        ("pdf", "application/pdf"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_completed_task_exports_after_repository_restart(
    tmp_path: Path,
    export_format: str,
    content_type: str,
) -> None:
    repository_dir = tmp_path / "tasks"
    writer = TaskService(repository=FileTaskRepository(repository_dir))
    task = writer.create_task(TaskType.PTR_COMPARE)
    writer.complete_task(
        task.task_id,
        [
            CheckResult(
                task_id=task.task_id,
                check_id="PTR_SCOPE",
                check_name="PTR scope",
                status=CheckStatus.PASS,
                summary="covered",
            )
        ],
    )

    restarted_service = TaskService(repository=FileTaskRepository(repository_dir))
    app = create_app()
    app.dependency_overrides[get_task_service] = lambda: restarted_service
    response = TestClient(app).get(
        f"/api/tasks/{task.task_id}/export",
        params={"format": export_format},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert response.content
