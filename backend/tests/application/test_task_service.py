import pytest

from app.application.task_repository import InMemoryTaskRepository
from app.application.task_service import (
    TaskNotFoundError,
    TaskResultNotFoundError,
    TaskService,
)
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.result import CheckResult, CheckStatus
from app.domain.task import InputFileRef, TaskState, TaskType


def _result(task_id: str, check_id: str, status: CheckStatus) -> CheckResult:
    return CheckResult(
        task_id=task_id,
        check_id=check_id,
        check_name=f"{check_id} check",
        status=status,
        summary=f"{check_id} summary",
    )


def test_task_service_tracks_lifecycle_and_stores_structured_result() -> None:
    service = TaskService()
    input_file = InputFileRef(file_id="file-1", file_name="report.pdf")

    task = service.create_task(TaskType.REPORT_CHECK, input_files=[input_file])
    assert task.status == TaskState.PENDING
    assert task.progress == 0
    assert task.current_step == "created"

    processing = service.start_task(task.task_id, current_step="extracting", progress=15)
    assert processing.status == TaskState.PROCESSING
    assert processing.progress == 15

    updated = service.update_progress(
        task.task_id,
        progress=60,
        current_step="running rules",
        log="parsed report",
    )
    assert updated.progress == 60
    assert updated.current_step == "running rules"
    assert updated.logs == ["parsed report"]

    completed = service.complete_task(
        task.task_id,
        [
            _result(task.task_id, "C01", CheckStatus.PASS),
            _result(task.task_id, "C02", CheckStatus.FAIL),
        ],
        diagnostics=["deterministic rules only"],
        metadata={"source": "unit-test"},
    )
    assert completed.status == TaskState.COMPLETED
    assert completed.progress == 100
    assert completed.result_ref == task.task_id

    result = service.get_result(task.task_id)
    assert result.summary.total_checks == 2
    assert result.summary.pass_count == 1
    assert result.summary.fail_count == 1
    assert result.input_files == [input_file]
    assert result.diagnostics == ["deterministic rules only"]
    assert result.metadata == {"source": "unit-test"}


def test_task_service_updates_progress_details_metadata() -> None:
    service = TaskService()
    task = service.create_task(TaskType.REPORT_CHECK)
    progress_details = {
        "phase": "rules",
        "phase_label": "规则初筛",
        "current_check_id": "C03",
        "current_check_name": "生产日期格式一致性",
        "checks": [
            {
                "check_id": "C03",
                "check_name": "生产日期格式一致性",
                "status": "skipped",
                "progress": 100,
                "candidate_findings_count": 0,
                "confirmed_errors_count": 0,
                "manual_review_required_count": 0,
                "refuted_findings_count": 0,
            }
        ],
        "codex_audit": {"enabled": False, "status": "pending"},
    }

    updated = service.update_progress(
        task.task_id,
        progress=40,
        current_step="running report rules",
        progress_details=progress_details,
    )

    assert updated.progress_details is not None
    assert updated.progress_details.phase == "rules"
    assert updated.progress_details.current_check_id == "C03"
    assert updated.metadata["progress_details"]["phase"] == "rules"
    assert updated.metadata["progress_details"]["checks"][0]["status"] == "skipped"


def test_task_service_stores_user_facing_status_for_unreviewed_candidate_error() -> None:
    service = TaskService()
    task = service.create_task(TaskType.REPORT_CHECK)
    evidence = Evidence(
        id="ev-c09",
        source_type=SourceType.REPORT,
        raw_text="序号列",
        method=EvidenceMethod.PDF_TEXT,
    )
    finding = Finding(
        id="finding-c09",
        task_id=task.task_id,
        check_id="C09",
        severity=FindingSeverity.ERROR,
        code="SERIAL_NUMBER_ERROR_001",
        message="序号候选问题",
        evidence=[evidence],
    )

    service.complete_task(
        task.task_id,
        [
            CheckResult(
                task_id=task.task_id,
                check_id="C09",
                check_name="序号连续性",
                status=CheckStatus.FAIL,
                findings=[finding],
            )
        ],
    )

    result = service.get_result(task.task_id)
    assert result.findings[0].metadata["user_facing_status"] == "candidate_issue"
    assert result.check_results[0].metadata["user_facing_status"] == "candidate_issue"
    assert result.summary.error_count == 1
    assert result.summary.candidate_errors_count == 1
    assert result.summary.confirmed_errors_count == 0


def test_task_service_returns_deep_copies_of_task_state() -> None:
    service = TaskService()
    task = service.create_task(TaskType.PTR_COMPARE)
    service.update_progress(task.task_id, progress=20, log="first log")

    returned = service.get_task(task.task_id)
    returned.logs.append("mutated outside service")

    assert service.get_task(task.task_id).logs == ["first log"]


def test_task_service_uses_injected_repository_for_shared_task_state() -> None:
    repository = InMemoryTaskRepository()
    writer = TaskService(repository=repository)
    reader = TaskService(repository=repository)

    task = writer.create_task(TaskType.REPORT_CHECK)
    writer.start_task(task.task_id, current_step="processing", progress=25)

    assert reader.get_task(task.task_id).status == TaskState.PROCESSING
    assert reader.get_task(task.task_id).progress == 25


def test_task_service_records_error_state_without_result() -> None:
    service = TaskService()
    task = service.create_task(TaskType.REPORT_CHECK)

    failed = service.fail_task(task.task_id, "PDF parse failed")

    assert failed.status == TaskState.ERROR
    assert failed.current_step == "error"
    assert failed.error_message == "PDF parse failed"
    with pytest.raises(TaskResultNotFoundError):
        service.get_result(task.task_id)


def test_task_service_raises_for_unknown_task_id() -> None:
    service = TaskService()

    with pytest.raises(TaskNotFoundError):
        service.get_task("missing")
    with pytest.raises(TaskNotFoundError):
        service.start_task("missing")
    with pytest.raises(TaskNotFoundError):
        service.complete_task("missing", [])
    with pytest.raises(TaskResultNotFoundError):
        service.get_result("missing")
