from fastapi.testclient import TestClient

from app.api.routes_ptr_compare import get_ptr_compare_usecase
from app.api.routes_tasks import get_task_service
from app.application.task_service import TaskService
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import InputFileRef, TaskState, TaskType
from app.main import create_app


class FakePTRCompareUseCase:
    def __init__(self, task_service: TaskService) -> None:
        self.task_service = task_service
        self.calls: list[dict[str, object]] = []

    def run(
        self,
        *,
        ptr_file_name: str,
        ptr_content: bytes,
        ptr_content_type: str,
        report_file_name: str,
        report_content: bytes,
        report_content_type: str,
    ) -> object:
        self.calls.append(
            {
                "ptr_file_name": ptr_file_name,
                "ptr_content": ptr_content,
                "ptr_content_type": ptr_content_type,
                "report_file_name": report_file_name,
                "report_content": report_content,
                "report_content_type": report_content_type,
            }
        )
        task = self.task_service.create_task(
            TaskType.PTR_COMPARE,
            input_files=[
                InputFileRef(file_id="ptr-file", file_name=ptr_file_name, content_type=ptr_content_type),
                InputFileRef(file_id="report-file", file_name=report_file_name, content_type=report_content_type),
            ],
        )
        self.task_service.start_task(task.task_id, current_step="fake ptr compare")
        self.task_service.complete_task(
            task.task_id,
            [
                CheckResult(
                    task_id=task.task_id,
                    check_id="PTR_CLAUSE",
                    check_name="PTR 条款正文一致性",
                    status=CheckStatus.PASS,
                    summary="条款一致",
                )
            ],
            diagnostics=["fake ptr usecase"],
        )
        return self.task_service.get_task(task.task_id)


def _client_with_fake_usecase() -> tuple[TestClient, FakePTRCompareUseCase]:
    task_service = TaskService()
    fake_usecase = FakePTRCompareUseCase(task_service)
    app = create_app()
    app.dependency_overrides[get_task_service] = lambda: task_service
    app.dependency_overrides[get_ptr_compare_usecase] = lambda: fake_usecase
    return TestClient(app), fake_usecase


def test_ptr_compare_upload_creates_task_through_usecase_and_exposes_result() -> None:
    client, fake_usecase = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/ptr-compare",
        files={
            "ptr_file": ("ptr.pdf", b"%PDF-1.4 ptr", "application/pdf"),
            "report_file": ("report.pdf", b"%PDF-1.4 report", "application/pdf"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    task_id = payload["task_id"]
    assert payload["status"] == TaskState.COMPLETED
    assert payload["task_type"] == TaskType.PTR_COMPARE
    assert {item["file_name"] for item in payload["input_files"]} == {"ptr.pdf", "report.pdf"}
    assert fake_usecase.calls == [
        {
            "ptr_file_name": "ptr.pdf",
            "ptr_content": b"%PDF-1.4 ptr",
            "ptr_content_type": "application/pdf",
            "report_file_name": "report.pdf",
            "report_content": b"%PDF-1.4 report",
            "report_content_type": "application/pdf",
        }
    ]

    result_response = client.get(f"/api/tasks/{task_id}/result")
    assert result_response.status_code == 200
    result_payload = result_response.json()
    assert result_payload["task_type"] == TaskType.PTR_COMPARE
    assert result_payload["summary"]["pass_count"] == 1
    assert result_payload["check_results"][0]["check_id"] == "PTR_CLAUSE"


def test_ptr_compare_upload_rejects_non_pdf_before_usecase() -> None:
    client, fake_usecase = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/ptr-compare",
        files={
            "ptr_file": ("ptr.txt", b"ptr text", "text/plain"),
            "report_file": ("report.pdf", b"%PDF-1.4 report", "application/pdf"),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported"
    assert fake_usecase.calls == []


def test_ptr_compare_upload_requires_both_files() -> None:
    client, _ = _client_with_fake_usecase()

    response = client.post(
        "/api/tasks/ptr-compare",
        files={"ptr_file": ("ptr.pdf", b"%PDF-1.4 ptr", "application/pdf")},
    )

    assert response.status_code == 422
