from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PTRComparisonOverallStatus(StrEnum):
    PASSED = "passed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    AUDIT_INCOMPLETE = "audit_incomplete"


class PTRUserFacingStatus(StrEnum):
    COVERED_PASSED = "covered_passed"
    MISSING_IN_REPORT = "missing_in_report"
    VALUE_MISMATCH = "value_mismatch"
    NEEDS_REVIEW = "needs_review"
    CANDIDATE_ISSUE = "candidate_issue"
    REFUTED = "refuted"
    CONFIRMED_ERROR = "confirmed_error"
    AUDIT_INCOMPLETE = "audit_incomplete"


class PTRDisplayFinalStatus(StrEnum):
    PASSED = "passed"
    CONFIRMED_ERROR = "confirmed_error"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    REFUTED = "refuted"
    CANDIDATE_ISSUE = "candidate_issue"
    AUDIT_INCOMPLETE = "audit_incomplete"


class PTRReportMatch(BaseModel):
    item_no: str | None = None
    report_page: int | None = None
    standard_clause: str | None = None
    item_name: str | None = None
    standard_requirement: str | None = None
    test_result: str | None = None
    single_conclusion: str | None = None
    remark: str | None = None


class PTRNormalizedComparison(BaseModel):
    requirement_type: str = "unknown"
    expected: Any | None = None
    actual: Any | None = None
    unit: str | None = None
    operator: str | None = None
    status: str = "needs_review"


class PTRComparisonItem(BaseModel):
    ptr_clause_id: str
    ptr_title: str | None = None
    ptr_page: int | None = None
    ptr_requirement_text: str
    report_matches: list[PTRReportMatch] = Field(default_factory=list)
    normalized_comparison: PTRNormalizedComparison
    rule_status: PTRUserFacingStatus
    user_facing_status: PTRUserFacingStatus
    final_status: PTRDisplayFinalStatus
    reason: str
    next_action: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    candidate_report_items: list[PTRReportMatch] = Field(default_factory=list)


class PTRComparisonDetails(BaseModel):
    overall_status: PTRComparisonOverallStatus
    overall_summary: str
    requirements_count: int = Field(default=0, ge=0)
    covered_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    mismatch_count: int = Field(default=0, ge=0)
    needs_review_count: int = Field(default=0, ge=0)
    confirmed_errors_count: int = Field(default=0, ge=0)
    manual_review_required_count: int = Field(default=0, ge=0)
    refuted_findings_count: int = Field(default=0, ge=0)
    items: list[PTRComparisonItem] = Field(default_factory=list)


__all__ = [
    "PTRComparisonDetails",
    "PTRComparisonItem",
    "PTRComparisonOverallStatus",
    "PTRDisplayFinalStatus",
    "PTRNormalizedComparison",
    "PTRReportMatch",
    "PTRUserFacingStatus",
]
