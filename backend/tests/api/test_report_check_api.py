from fastapi.testclient import TestClient

from app.api.routes_report_check import get_report_check_usecase
from app.api.routes_tasks import get_task_service
from app.application.task_service import TaskService
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import InputFileRef, TaskState, TaskType
from app.main import create_app


class FakeReportCheckUseCase:
    def __init__(self, task_service: TaskService) -> None:
        self.task_service = task_service
        self.calls: list[dict[str, object]] = []
        self.processed_task_ids: list[str] = []

    def submit(self, *, file_name: str, content: bytes, content_type: str, audit_options=None) -> object:
        self.calls.append(
            {
                "file_name": file_name,
                "content": content,
                "content_type": content_type,
                "audit_options": audit_options,
            }
        )
        task = self.task_service.create_task(
            TaskType.REPORT_CHECK,
            input_files=[
                InputFileRef(file_id="report-file", file_name=file_name, content_type=content_type)
            ],
        )
        return self.task_service.start_task(task.task_id, current_step="queued fake report check", progress=1)

    def process_task(self, task_id: str) -> object:
        self.processed_task_ids.append(task_id)
        self.task_service.update_progress(task_id, progress=35, current_step="fake report check")
        self.task_service.complete_task(
            task_id,
            [
                CheckResult(
                    task_id=task_id,
                    check_id="C01",
                    check_name="首页与第三页一致性",
                    status=CheckStatus.PASS,
                    summary="字段一致",
                )
            ],
            diagnostics=["fake report usecase"],
        )
        return self.task_service.get_task(task_id)


def _client_with_fake_usecase() -> tuple[TestClient, FakeReportCheckUseCase]:
    task_service = TaskService()
    fake_usecase = FakeReportCheckUseCase(task_service)
    app = create_app()
    app.dependency_overrides[get_task_service] = lambda: task_service
    app.dependency_overrides[get_report_check_usecase] = lambda: fake_usecase
    return TestClient(app), fake_usecase


def test_report_check_upload_returns_processing_task_then_background_exposes_result() -> None:
    client, fake_usecase = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/report-check",
        files={"report_file": ("report.pdf", b"%PDF-1.4 report", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    task_id = payload["task_id"]
    assert payload["status"] == TaskState.PROCESSING
    assert payload["progress"] == 1
    assert payload["current_step"] == "queued fake report check"
    assert payload["task_type"] == TaskType.REPORT_CHECK
    assert payload["input_files"][0]["file_name"] == "report.pdf"
    assert fake_usecase.calls == [
        {
            "file_name": "report.pdf",
            "content": b"%PDF-1.4 report",
            "content_type": "application/pdf",
            "audit_options": None,
        }
    ]
    assert fake_usecase.processed_task_ids == [task_id]

    status_response = client.get(f"/api/tasks/{task_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == TaskState.COMPLETED

    result_response = client.get(f"/api/tasks/{task_id}/result")
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["task_id"] == task_id
    assert result_payload["summary"]["pass_count"] == 1
    assert result_payload["check_results"][0]["check_id"] == "C01"
    assert result_payload["check_results"][0]["codex_reviews"] == []

    export_response = client.get(f"/api/tasks/{task_id}/export", params={"format": "json"})
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/json")
    assert export_response.json()["task"]["task_id"] == task_id


def test_report_check_upload_rejects_non_pdf_before_usecase() -> None:
    client, fake_usecase = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/report-check",
        files={"report_file": ("report.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported"
    assert fake_usecase.calls == []


def test_report_check_upload_passes_audit_options_to_usecase() -> None:
    client, fake_usecase = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/report-check",
        files={"report_file": ("report.pdf", b"%PDF-1.4 report", "application/pdf")},
        data={
            "included_check_ids": "C07",
            "included_finding_codes": "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
            "excluded_check_ids": "C04",
            "max_targets_per_batch": "1",
            "max_parallel_jobs": "2",
        },
    )

    assert response.status_code == 200
    assert fake_usecase.calls[0]["audit_options"] == {
        "included_check_ids": ["C07"],
        "included_finding_codes": ["CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX"],
        "excluded_check_ids": ["C04"],
        "max_targets_per_batch": 1,
        "max_parallel_jobs": 2,
    }


def test_task_routes_return_404_for_unknown_task() -> None:
    client, _ = _client_with_fake_usecase()

    assert client.get("/api/tasks/missing-task").status_code == 404
    assert client.get("/api/tasks/missing-task/result").status_code == 404
    assert client.get("/api/tasks/missing-task/export").status_code == 404
