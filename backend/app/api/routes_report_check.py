from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.routes_tasks import get_app_settings, get_task_service
from app.api.schemas.task import TaskStatusResponse
from app.application.codex_runtime_factory import build_report_check_usecase
from app.application.report_check_usecase import ReportCheckUseCase
from app.application.task_service import TaskService
from app.core.config import Settings


router = APIRouter(tags=["Report Check"])


def get_report_check_usecase(
    task_service: TaskService = Depends(get_task_service),
    settings: Settings = Depends(get_app_settings),
) -> ReportCheckUseCase:
    return build_report_check_usecase(settings, task_service=task_service)


@router.post("/api/tasks/report-check", response_model=TaskStatusResponse)
async def create_report_check_task(
    report_file: UploadFile = File(..., description="Inspection report PDF file"),
    usecase: ReportCheckUseCase = Depends(get_report_check_usecase),
):
    _validate_pdf_upload(report_file)
    content = await report_file.read()
    return usecase.run(
        file_name=report_file.filename or "report.pdf",
        content=content,
        content_type=report_file.content_type or "application/pdf",
    )


def _validate_pdf_upload(file: UploadFile) -> None:
    file_name = file.filename or ""
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")


__all__ = ["get_report_check_usecase", "router"]
