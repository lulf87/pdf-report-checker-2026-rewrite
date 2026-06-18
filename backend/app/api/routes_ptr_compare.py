from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.routes_tasks import get_app_settings, get_task_service
from app.api.schemas.task import TaskStatusResponse
from app.application.codex_runtime_factory import build_ptr_compare_usecase
from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.core.config import Settings


router = APIRouter(tags=["PTR Compare"])


def get_ptr_compare_usecase(
    task_service: TaskService = Depends(get_task_service),
    settings: Settings = Depends(get_app_settings),
) -> PTRCompareUseCase:
    return build_ptr_compare_usecase(settings, task_service=task_service)


@router.post("/api/tasks/ptr-compare", response_model=TaskStatusResponse)
async def create_ptr_compare_task(
    ptr_file: UploadFile = File(..., description="PTR PDF file"),
    report_file: UploadFile = File(..., description="Inspection report PDF file"),
    usecase: PTRCompareUseCase = Depends(get_ptr_compare_usecase),
):
    _validate_pdf_upload(ptr_file)
    _validate_pdf_upload(report_file)
    ptr_content = await ptr_file.read()
    report_content = await report_file.read()
    return usecase.run(
        ptr_file_name=ptr_file.filename or "ptr.pdf",
        ptr_content=ptr_content,
        ptr_content_type=ptr_file.content_type or "application/pdf",
        report_file_name=report_file.filename or "report.pdf",
        report_content=report_content,
        report_content_type=report_file.content_type or "application/pdf",
    )


def _validate_pdf_upload(file: UploadFile) -> None:
    file_name = file.filename or ""
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")


__all__ = ["get_ptr_compare_usecase", "router"]
