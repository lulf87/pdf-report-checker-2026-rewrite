from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.schemas.task import TaskResultResponse, TaskStatusResponse
from app.application.task_service import (
    TaskNotFoundError,
    TaskResultNotFoundError,
    TaskService,
)
from app.domain.task import TaskState
from app.infrastructure.export.excel_exporter import export_check_results_to_xlsx
from app.infrastructure.export.json_exporter import export_check_results_to_json
from app.infrastructure.export.pdf_exporter import export_check_results_to_pdf


router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

_TASK_SERVICE = TaskService()


def get_task_service() -> TaskService:
    return _TASK_SERVICE


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
):
    try:
        return task_service.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.get("/{task_id}/result", response_model=TaskResultResponse)
def get_task_result(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
):
    try:
        task = task_service.get_task(task_id)
        if task.status in {TaskState.PENDING, TaskState.PROCESSING}:
            raise HTTPException(status_code=202, detail="Task still processing")
        if task.status == TaskState.ERROR:
            raise HTTPException(status_code=400, detail=task.error_message or "Task failed")
        return task_service.get_result(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except TaskResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No result available") from exc


@router.get("/{task_id}/export")
def export_task_result(
    task_id: str,
    format: str = Query(default="json"),
    task_service: TaskService = Depends(get_task_service),
) -> Response:
    export_format = (format or "json").lower()
    if export_format not in {"json", "pdf", "xlsx"}:
        raise HTTPException(status_code=400, detail="Unsupported export format")

    try:
        task = task_service.get_task(task_id)
        if task.status != TaskState.COMPLETED:
            raise HTTPException(status_code=400, detail="Task not completed yet")
        result = task_service.get_result(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except TaskResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No result available") from exc

    input_files = [input_file.file_name for input_file in result.input_files]
    if export_format == "json":
        content = export_check_results_to_json(
            result.check_results,
            task_id=result.task_id,
            task_type=result.task_type,
            input_files=input_files,
            diagnostics=result.diagnostics,
            metadata=result.metadata,
        )
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{task_id}.json"'},
        )

    if export_format == "pdf":
        content = export_check_results_to_pdf(
            result.check_results,
            task_id=result.task_id,
            task_type=result.task_type,
            input_files=input_files,
            diagnostics=result.diagnostics,
            metadata=result.metadata,
        )
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{task_id}.pdf"'},
        )

    content = export_check_results_to_xlsx(
        result.check_results,
        task_id=result.task_id,
        task_type=result.task_type,
        input_files=input_files,
        diagnostics=result.diagnostics,
        metadata=result.metadata,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{task_id}.xlsx"'},
    )


__all__ = ["get_task_service", "router"]
