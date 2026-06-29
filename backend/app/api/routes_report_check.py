from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.api.routes_tasks import get_app_settings, get_task_service
from app.api.schemas.task import TaskStatusResponse
from app.application.codex_audit_options import compact_audit_options_dict
from app.application.codex_runtime_factory import build_report_check_usecase
from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.core.config import Settings
from app.domain.task import TaskState


router = APIRouter(tags=["Report Check"])


def get_report_check_usecase(
    task_service: TaskService = Depends(get_task_service),
    settings: Settings = Depends(get_app_settings),
) -> ReportCheckUseCase:
    return build_report_check_usecase(settings, task_service=task_service)


@router.post("/api/tasks/report-check", response_model=TaskStatusResponse)
async def create_report_check_task(
    background_tasks: BackgroundTasks,
    report_file: UploadFile = File(..., description="Inspection report PDF file"),
    included_check_ids: str | None = Form(default=None),
    included_finding_codes: str | None = Form(default=None),
    excluded_check_ids: str | None = Form(default=None),
    max_targets_per_batch: int | None = Form(default=None),
    max_parallel_jobs: int | None = Form(default=None),
    usecase: ReportCheckUseCase = Depends(get_report_check_usecase),
):
    _validate_pdf_upload(report_file)
    content = await report_file.read()
    task = usecase.submit(
        file_name=report_file.filename or "report.pdf",
        content=content,
        content_type=report_file.content_type or "application/pdf",
        audit_options=compact_audit_options_dict(
            {
                "included_check_ids": included_check_ids,
                "included_finding_codes": included_finding_codes,
                "excluded_check_ids": excluded_check_ids,
                "max_targets_per_batch": max_targets_per_batch,
                "max_parallel_jobs": max_parallel_jobs,
            }
        ),
    )
    if task.status == TaskState.PROCESSING:
        background_tasks.add_task(usecase.process_task, task.task_id)
    return task


def _validate_pdf_upload(file: UploadFile) -> None:
    file_name = file.filename or ""
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")


__all__ = ["get_report_check_usecase", "router"]
