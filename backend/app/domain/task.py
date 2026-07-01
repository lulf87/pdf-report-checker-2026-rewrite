from datetime import datetime
from enum import StrEnum
from typing import Any

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


class TaskProgressPhase(StrEnum):
    UPLOAD = "upload"
    PARSE = "parse"
    EXTRACT = "extract"
    RULES = "rules"
    EVIDENCE = "evidence"
    CODEX_AUDIT = "codex_audit"
    FINALIZE = "finalize"
    COMPLETED = "completed"
    ERROR = "error"


class TaskCheckProgressStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


class CodexAuditProgressStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCheckProgress(BaseModel):
    check_id: str
    check_name: str
    status: TaskCheckProgressStatus = TaskCheckProgressStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    candidate_findings_count: int = Field(default=0, ge=0)
    confirmed_errors_count: int = Field(default=0, ge=0)
    manual_review_required_count: int = Field(default=0, ge=0)
    refuted_findings_count: int = Field(default=0, ge=0)


class TaskCodexAuditProgress(BaseModel):
    enabled: bool = False
    status: CodexAuditProgressStatus = CodexAuditProgressStatus.PENDING
    current_check_id: str | None = None
    current_target_type: str | None = None
    completed_reviews_count: int = Field(default=0, ge=0)
    total_reviews_count: int = Field(default=0, ge=0)
    completed_batches_count: int = Field(default=0, ge=0)
    total_batches_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    last_retry_reason: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=0)
    max_targets_per_batch: int | None = Field(default=None, ge=1)
    error_code: str | None = None


class TaskProgressDetails(BaseModel):
    phase: TaskProgressPhase
    phase_label: str | None = None
    current_check_id: str | None = None
    current_check_name: str | None = None
    checks: list[TaskCheckProgress] = Field(default_factory=list)
    codex_audit: TaskCodexAuditProgress | None = None
    error_code: str | None = None
    error_message: str | None = None


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    progress_details: TaskProgressDetails | None = None
    created_at: datetime
    updated_at: datetime
