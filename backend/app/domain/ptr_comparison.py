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
    COVERAGE_ONLY_NEEDS_REVIEW = "coverage_only_needs_review"
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
    report_pages: list[int] = Field(default_factory=list)
    page_span: tuple[int, int] | None = None
    standard_clause: str | None = None
    item_name: str | None = None
    standard_requirement: str | None = None
    test_result: str | None = None
    single_conclusion: str | None = None
    remark: str | None = None
    report_atomic_results: list["PTRReportAtomicResult"] = Field(default_factory=list)


class PTRNormalizedComparison(BaseModel):
    requirement_type: str = "unknown"
    expected: Any | None = None
    actual: Any | None = None
    unit: str | None = None
    operator: str | None = None
    status: str = "needs_review"


class PTRAtomicRequirement(BaseModel):
    atomic_id: str
    clause_id: str
    label: str
    expected_text: str | None = None
    expected_value: float | None = None
    operator: str | None = None
    unit: str | None = None
    source: str = "ptr_text"
    table_number: str | None = None
    table_title: str | None = None
    table_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PTRAtomicComparisonRow(BaseModel):
    atomic_id: str
    clause_id: str
    label: str
    preset: str | None = None
    expected: str | None = None
    actual: str | None = None
    unit: str | None = None
    candidate_actuals: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    reason: str | None = None
    report_page: int | None = None
    report_item_no: str | None = None
    confidence: str | None = None
    source: str = "ptr_text"
    source_text: str | None = None
    table_number: str | None = None
    table_title: str | None = None
    table_key: str | None = None


class PTRReportAtomicResult(BaseModel):
    atomic_id: str
    clause_id: str
    label: str
    actual: str | None = None
    unit: str | None = None
    preset: str | None = None
    report_item_no: str | None = None
    report_page: int | None = None
    source_text: str | None = None
    confidence: str | None = None
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    candidate_actuals: list[str] = Field(default_factory=list)


class PTRComparisonItem(BaseModel):
    ptr_clause_id: str
    ptr_title: str | None = None
    ptr_page: int | None = None
    ptr_requirement_text: str
    report_matches: list[PTRReportMatch] = Field(default_factory=list)
    external_standard_coverage: dict[str, Any] | None = None
    external_standard_coverages: list[dict[str, Any]] = Field(default_factory=list)
    atomic_requirements: list[PTRAtomicRequirement] = Field(default_factory=list)
    atomic_comparison_rows: list[PTRAtomicComparisonRow] = Field(default_factory=list)
    normalized_comparison: PTRNormalizedComparison
    rule_status: PTRUserFacingStatus
    coverage_status: PTRUserFacingStatus
    user_facing_status: PTRUserFacingStatus
    final_status: PTRDisplayFinalStatus
    reason: str
    next_action: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    candidate_report_items: list[PTRReportMatch] = Field(default_factory=list)


class PTRExcludedComparisonItem(BaseModel):
    ptr_clause_id: str
    ptr_title: str | None = None
    ptr_requirement_text: str = ""
    status: str = "excluded_by_scope"
    reason: str
    excluded_topic: str | None = None
    evidence: str | None = None


class PTRComparisonDetails(BaseModel):
    overall_status: PTRComparisonOverallStatus
    overall_summary: str
    scope_consistency: dict[str, Any] | None = None
    requirements_count: int = Field(default=0, ge=0)
    covered_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    mismatch_count: int = Field(default=0, ge=0)
    needs_review_count: int = Field(default=0, ge=0)
    confirmed_errors_count: int = Field(default=0, ge=0)
    manual_review_required_count: int = Field(default=0, ge=0)
    refuted_findings_count: int = Field(default=0, ge=0)
    items: list[PTRComparisonItem] = Field(default_factory=list)
    excluded_items: list[PTRExcludedComparisonItem] = Field(default_factory=list)


__all__ = [
    "PTRComparisonDetails",
    "PTRAtomicComparisonRow",
    "PTRAtomicRequirement",
    "PTRComparisonItem",
    "PTRExcludedComparisonItem",
    "PTRComparisonOverallStatus",
    "PTRDisplayFinalStatus",
    "PTRNormalizedComparison",
    "PTRReportMatch",
    "PTRReportAtomicResult",
    "PTRUserFacingStatus",
]
