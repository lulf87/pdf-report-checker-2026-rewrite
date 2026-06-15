from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TaskType(StrEnum):
    REPORT_CHECK = "report_check"
    PTR_COMPARE = "ptr_compare"


class TaskState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class InputFileRef(BaseModel):
    file_id: str
    file_name: str
    content_type: str = "application/pdf"


class TaskStatus(BaseModel):
    task_id: str
    task_type: TaskType
    status: TaskState
    progress: int = Field(ge=0, le=100)
    current_step: str | None = None
    input_files: list[InputFileRef] = Field(default_factory=list)
    result_ref: str | None = None
    error_message: str | None = None
    logs: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
