from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CodexReviewVerdict(StrEnum):
    CONFIRM = "confirm"
    REFUTE = "refute"
    UNCERTAIN = "uncertain"
    ADD_FINDING = "add_finding"


class CodexReviewStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class CodexReviewConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CodexReviewTargetType(StrEnum):
    PTR_CLAUSE = "ptr_clause"
    PTR_TABLE = "ptr_table"
    PTR_PARAMETER = "ptr_parameter"
    REPORT_RULE = "report_rule"
    LABEL_OCR = "label_ocr"
    PHOTO_CAPTION = "photo_caption"
    INSPECTION_ITEM = "inspection_item"
    SAMPLE_DESCRIPTION = "sample_description"
    PAGE_NUMBER = "page_number"
    FINDING = "finding"
    CHECK_RESULT = "check_result"
    EVIDENCE_PACKAGE = "evidence_package"


class CodexEvidenceRef(BaseModel):
    ref_id: str
    source_type: str
    path: str | None = None
    page_number: int | None = Field(default=None, gt=0)
    section: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexReviewTarget(BaseModel):
    target_id: str
    target_type: CodexReviewTargetType
    check_id: str | None = None
    finding_id: str | None = None
    finding_code: str | None = None
    title: str | None = None
    summary: str | None = None
    evidence_refs: list[CodexEvidenceRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexReviewError(BaseModel):
    code: str
    message: str
    detail: str | None = None
    retryable: bool = False


class CodexReviewRequest(BaseModel):
    request_id: str
    task_id: str
    task_type: str
    mode: str = "verify"
    targets: list[CodexReviewTarget]
    prompt_version: str | None = None
    schema_version: str
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexSuggestedFinding(BaseModel):
    check_id: str | None = None
    severity: str | None = None
    code: str | None = None
    message: str
    expected: str | None = None
    actual: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodexReviewResult(BaseModel):
    review_id: str
    request_id: str
    task_id: str
    target: CodexReviewTarget
    status: CodexReviewStatus
    verdict: CodexReviewVerdict | None = None
    confidence: CodexReviewConfidence | None = None
    reasoning_summary: str | None = None
    suggested_severity: str | None = None
    suggested_finding: CodexSuggestedFinding | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    raw_output_path: str | None = None
    error: CodexReviewError | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_payload(self) -> "CodexReviewResult":
        if self.status == CodexReviewStatus.SUCCEEDED and self.verdict is None:
            raise ValueError("succeeded codex review results must include a verdict")
        if self.status == CodexReviewStatus.FAILED and self.error is None:
            raise ValueError("failed codex review results must include an error")
        if self.verdict == CodexReviewVerdict.ADD_FINDING and self.suggested_finding is None:
            raise ValueError("add_finding verdicts must include suggested_finding")
        return self


__all__ = [
    "CodexEvidenceRef",
    "CodexReviewConfidence",
    "CodexReviewError",
    "CodexReviewRequest",
    "CodexReviewResult",
    "CodexReviewStatus",
    "CodexReviewTarget",
    "CodexReviewTargetType",
    "CodexReviewVerdict",
    "CodexSuggestedFinding",
]
