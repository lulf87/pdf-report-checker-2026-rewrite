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
    CONFIRMED_ISSUE = "confirmed_issue"
    CONFIRMED_DOCUMENT_ISSUE = "confirmed_document_issue"
    NEEDS_POLICY_REVIEW = "needs_policy_review"
    AUDIT_INCOMPLETE = "audit_incomplete"


class PTRDisplayFinalStatus(StrEnum):
    PASSED = "passed"
    CONFIRMED_ERROR = "confirmed_error"
    CONFIRMED_ISSUE = "confirmed_issue"
    CONFIRMED_DOCUMENT_ISSUE = "confirmed_document_issue"
    NEEDS_POLICY_REVIEW = "needs_policy_review"
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
    condition: str | None = None
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
    condition: str | None = None
    model_column: str | None = None
    table_row_label: str | None = None
    parent_clause: str | None = None
    expected: str | None = None
    actual: str | None = None
    unit: str | None = None
    expected_operator: str | None = None
    expected_value: float | None = None
    expected_unit: str | None = None
    actual_operator: str | None = None
    actual_value: float | None = None
    actual_unit: str | None = None
    report_conclusion: str | None = None
    candidate_actuals: list[str] = Field(default_factory=list)
    status: str = "needs_review"
    reason: str | None = None
    report_page: int | None = None
    report_item_no: str | None = None
    report_clause_number: str | None = None
    report_source_row: int | None = None
    confidence: str | None = None
    source: str = "ptr_text"
    source_text: str | None = None
    table_number: str | None = None
    table_title: str | None = None
    table_key: str | None = None
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class PTRCoverageComparisonRow(BaseModel):
    ptr_clause_id: str
    ptr_title: str | None = None
    ptr_requirement: str | None = None
    report_item_no: str | None = None
    report_page: int | None = None
    report_standard_clause: str | None = None
    report_requirement_excerpt: str | None = None
    report_result: str | None = None
    report_conclusion: str | None = None
    status: str = "needs_review"
    reason: str | None = None


class PTRReportAtomicResult(BaseModel):
    atomic_id: str
    clause_id: str
    label: str
    actual: str | None = None
    unit: str | None = None
    preset: str | None = None
    condition: str | None = None
    report_item_no: str | None = None
    report_page: int | None = None
    report_clause_number: str | None = None
    report_source_row: int | None = None
    source_text: str | None = None
    confidence: str | None = None
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    candidate_actuals: list[str] = Field(default_factory=list)


class PTRClauseStatement(BaseModel):
    clause_id: str
    title: str | None = None
    local_text: str = ""
    page: int | None = None


class PTRClauseIdentity(BaseModel):
    clause_id: str
    clause_number: str
    title: str | None = None
    normalized_title: str | None = None
    local_text: str = ""
    parent_clause: str | None = None
    referenced_tables: list[str] = Field(default_factory=list)
    table_row_labels: list[str] = Field(default_factory=list)
    parameter_terms: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    source_page: int | None = None


class ReportClauseIdentity(BaseModel):
    identity_id: str
    item_no: str | None = None
    group_id: str
    clause_number: str | None = None
    title: str | None = None
    normalized_title: str | None = None
    standard_requirement_text: str = ""
    row_label: str | None = None
    parent_clause: str | None = None
    referenced_tables: list[str] = Field(default_factory=list)
    parameter_terms: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    test_result: str | None = None
    conclusion: str | None = None
    source_page: int | None = None
    source_row: int | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ReportSubclauseIndex(BaseModel):
    identities: list[ReportClauseIdentity] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)


class ClauseIdentityCandidate(BaseModel):
    report_identity_id: str
    ptr_clause_number: str
    report_clause_number: str | None = None
    report_item_no: str | None = None
    report_title: str | None = None
    report_page: int | None = None
    report_source_row: int | None = None
    number_relation: str
    title_relation: str
    table_row_relation: str
    parameter_relation: str
    parent_relation: str
    score: int
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    rejected_reason: str | None = None


class ClauseIdentityAlignment(BaseModel):
    status: str
    ptr_clause_number: str
    ptr_title: str | None = None
    selected_report_clause_number: str | None = None
    selected_report_title: str | None = None
    selected_report_item_no: str | None = None
    selected_report_page: int | None = None
    selected_report_source_row: int | None = None
    selected_report_identity: ReportClauseIdentity | None = None
    number_matches: bool = False
    title_matches: bool = False
    parameter_matches: bool = False
    table_row_matches: bool = False
    confidence: str = "low"
    reason: str
    candidate_count: int = 0
    candidates: list[ClauseIdentityCandidate] = Field(default_factory=list)


class PTREffectiveRequirement(BaseModel):
    requirement_id: str
    label: str
    source_type: str
    requirement_type: str | None = None
    parent_clause: str | None = None
    table_number: str | None = None
    table_title: str | None = None
    table_row_label: str | None = None
    model: str | None = None
    preset: str | None = None
    load: str | None = None
    condition: str | None = None
    selected_column: str | None = None
    expected: str | None = None
    operator: str | None = None
    expected_value: float | None = None
    unit: str | None = None
    source_page: int | None = None
    evidence_ref: str | None = None


class PTRReportRequirementMatch(BaseModel):
    report_item_no: str | None = None
    report_clause: str | None = None
    row_label: str | None = None
    condition: str | None = None
    model: str | None = None
    load: str | None = None
    preset: str | None = None
    standard_requirement_text: str
    page: int | None = None
    source_row: int | None = None
    evidence_ref: str | None = None


class PTRTraceResultComparison(BaseModel):
    comparison_id: str
    label: str
    condition: str | None = None
    model: str | None = None
    load: str | None = None
    preset: str | None = None
    expected: str | None = None
    actual: str | None = None
    unit: str | None = None
    status: str
    reason: str
    verification_basis: str
    page: int | None = None
    item_no: str | None = None


class PTRRequirementAlignment(BaseModel):
    status: str
    reason: str
    ptr_evidence_refs: list[str] = Field(default_factory=list)
    report_evidence_refs: list[str] = Field(default_factory=list)


class PTRResultCompliance(BaseModel):
    status: str
    reason: str


class PTRTechnicalEvidence(BaseModel):
    ptr_full_text: str | None = None
    ptr_tables: list[dict[str, Any]] = Field(default_factory=list)
    report_groups: list[dict[str, Any]] = Field(default_factory=list)
    raw_finding_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PTRComparisonTrace(BaseModel):
    ptr_clause_statement: PTRClauseStatement
    clause_identity_alignment: ClauseIdentityAlignment | None = None
    effective_requirements: list[PTREffectiveRequirement] = Field(default_factory=list)
    report_requirement_matches: list[PTRReportRequirementMatch] = Field(default_factory=list)
    result_comparisons: list[PTRTraceResultComparison] = Field(default_factory=list)
    requirement_alignment: PTRRequirementAlignment
    result_compliance: PTRResultCompliance
    technical_evidence: PTRTechnicalEvidence


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
    coverage_comparison_rows: list[PTRCoverageComparisonRow] = Field(default_factory=list)
    ptr_clause_statement: PTRClauseStatement | None = None
    clause_identity_alignment: ClauseIdentityAlignment | None = None
    effective_requirements: list[PTREffectiveRequirement] = Field(default_factory=list)
    report_requirement_matches: list[PTRReportRequirementMatch] = Field(default_factory=list)
    result_comparisons: list[PTRTraceResultComparison] = Field(default_factory=list)
    requirement_alignment: PTRRequirementAlignment | None = None
    result_compliance: PTRResultCompliance | None = None
    technical_evidence: PTRTechnicalEvidence | None = None
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
    ptr_extraction_status: str | None = None
    ptr_ocr_required: bool = False
    ptr_pages_need_ocr: list[int] = Field(default_factory=list)
    source_type: str | None = None
    scope_consistency: dict[str, Any] | None = None
    report_model_context: dict[str, Any] | None = None
    ptr_table_registry: list[dict[str, Any]] = Field(default_factory=list)
    requirements_count: int = Field(default=0, ge=0)
    covered_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    mismatch_count: int = Field(default=0, ge=0)
    needs_review_count: int = Field(default=0, ge=0)
    confirmed_errors_count: int = Field(default=0, ge=0)
    confirmed_findings_count: int = Field(default=0, ge=0)
    confirmed_document_issue_count: int = Field(default=0, ge=0)
    manual_review_required_count: int = Field(default=0, ge=0)
    policy_review_required_count: int = Field(default=0, ge=0)
    refuted_findings_count: int = Field(default=0, ge=0)
    clause_sequence_offset_groups: list[dict[str, Any]] = Field(default_factory=list)
    section_container_clause_ids: list[str] = Field(default_factory=list)
    items: list[PTRComparisonItem] = Field(default_factory=list)
    excluded_items: list[PTRExcludedComparisonItem] = Field(default_factory=list)


__all__ = [
    "PTRComparisonDetails",
    "PTRAtomicComparisonRow",
    "PTRAtomicRequirement",
    "ClauseIdentityAlignment",
    "ClauseIdentityCandidate",
    "PTRCoverageComparisonRow",
    "PTRClauseStatement",
    "PTRClauseIdentity",
    "PTRComparisonTrace",
    "PTREffectiveRequirement",
    "PTRComparisonItem",
    "PTRExcludedComparisonItem",
    "PTRComparisonOverallStatus",
    "PTRDisplayFinalStatus",
    "PTRNormalizedComparison",
    "PTRReportMatch",
    "PTRReportAtomicResult",
    "ReportClauseIdentity",
    "ReportSubclauseIndex",
    "PTRReportRequirementMatch",
    "PTRRequirementAlignment",
    "PTRResultCompliance",
    "PTRTechnicalEvidence",
    "PTRTraceResultComparison",
    "PTRUserFacingStatus",
]
