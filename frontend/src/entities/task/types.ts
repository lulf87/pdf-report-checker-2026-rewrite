import type { CodexReviewResult } from "../codexReview/types";
import type { Evidence, Finding, FindingSeverity } from "../finding/types";

export type TaskType = "report_check" | "ptr_compare";
export type TaskState = "pending" | "processing" | "completed" | "error";
export type CheckStatus = "pass" | "fail" | "review" | "skip" | "system_error";
export type ExportFormat = "json" | "pdf" | "xlsx";
export type AuditScope = "full" | "targeted";
export type FinalAuditStatus = "passed" | "needs_manual_review" | "failed" | "audit_failed";
export type TaskProgressPhase =
  | "upload"
  | "parse"
  | "extract"
  | "rules"
  | "evidence"
  | "codex_audit"
  | "finalize"
  | "completed"
  | "error";
export type TaskCheckProgressStatus =
  | "pending"
  | "running"
  | "passed"
  | "failed"
  | "skipped"
  | "needs_review"
  | "needs_policy_review"
  | "error";
export type CodexAuditProgressStatus = "pending" | "running" | "retrying" | "completed" | "failed";
export type CodexReasoningEffort = "low" | "medium" | "high" | "xhigh" | "max";

export interface InputFileRef {
  file_id: string;
  file_name: string;
  content_type: string;
}

export interface AuditOptions {
  profile?: string;
  included_check_ids?: string;
  included_finding_codes?: string;
  excluded_check_ids?: string;
  max_targets_per_batch?: number;
  max_parallel_jobs?: number;
  timeout_seconds?: number;
  model?: string;
  reasoning_effort?: CodexReasoningEffort;
}

export interface CodexRuntimeProfile {
  profile_id: string;
  label: string;
  model: string | null;
  reasoning_effort: CodexReasoningEffort | null;
  timeout_seconds: number | null;
  max_targets_per_batch: number | null;
  max_parallel_jobs: number | null;
}

export interface CodexRuntimeConfig {
  default_model: string | null;
  model_options: string[];
  default_reasoning_effort: CodexReasoningEffort;
  reasoning_effort_options: CodexReasoningEffort[];
  default_profile: string;
  profiles: CodexRuntimeProfile[];
  runtime_config_version: string;
}

export interface TaskCheckProgress {
  check_id: string;
  check_name: string;
  status: TaskCheckProgressStatus;
  progress: number;
  candidate_findings_count: number;
  confirmed_errors_count: number;
  manual_review_required_count: number;
  refuted_findings_count: number;
}

export interface TaskCodexAuditProgress {
  enabled: boolean;
  status: CodexAuditProgressStatus;
  current_check_id?: string | null;
  current_target_type?: string | null;
  completed_reviews_count: number;
  total_reviews_count: number;
  completed_batches_count: number;
  total_batches_count: number;
  retry_count: number;
  last_retry_reason?: string | null;
  timeout_seconds?: number | null;
  max_targets_per_batch?: number | null;
  error_code?: string | null;
}

export interface TaskProgressDetails {
  phase: TaskProgressPhase;
  phase_label?: string | null;
  current_check_id?: string | null;
  current_check_name?: string | null;
  checks: TaskCheckProgress[];
  codex_audit?: TaskCodexAuditProgress | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface TaskStatus {
  task_id: string;
  task_type: TaskType;
  status: TaskState;
  progress: number;
  current_step?: string | null;
  input_files: InputFileRef[];
  result_ref?: string | null;
  error_message?: string | null;
  logs: string[];
  metadata: Record<string, unknown>;
  progress_details?: TaskProgressDetails | null;
  created_at: string;
  updated_at: string;
}

export interface CheckSummary {
  audit_scope: AuditScope | null;
  full_audit: boolean | null;
  final_audit_status: FinalAuditStatus | null;
  total_checks: number;
  pass_count: number;
  fail_count: number;
  review_count: number;
  skip_count: number;
  system_error_count: number;
  error_count: number;
  warn_count: number;
  info_count: number;
  candidate_findings_count: number;
  candidate_errors_count: number;
  confirmed_findings_count: number;
  confirmed_errors_count: number;
  confirmed_document_issue_count: number;
  refuted_findings_count: number;
  manual_review_required_count: number;
  policy_review_required_count: number;
  suggested_additional_findings_count: number;
  out_of_scope_findings_count: number;
  summary_only_findings_count: number;
  unreviewed_required_findings_count: number;
  codex_reviews_count: number;
  codex_runtime_failure_count: number;
}

export interface ComparisonSource {
  source_key: string;
  label: string;
  page_number?: number | null;
  display_page_label?: string | null;
  section?: string | null;
}

export interface ComparisonExtract {
  source_key?: string | null;
  label?: string | null;
  page_number?: number | null;
  display_page_label?: string | null;
  raw_text?: string | null;
  normalized_text?: string | null;
}

export type ComparisonFieldStatus =
  | "match"
  | "mismatch"
  | "missing_left"
  | "missing_right"
  | "needs_review"
  | "not_applicable"
  | string;

export interface ComparisonField {
  field_key: string;
  field_label: string;
  left?: ComparisonExtract | null;
  right?: ComparisonExtract | null;
  status: ComparisonFieldStatus;
  reason?: string | null;
  evidence_ids?: string[];
}

export interface ComparisonDetails {
  title: string;
  overall_status: "match" | "mismatch" | "needs_review" | "skipped" | string;
  overall_reason?: string | null;
  sources?: ComparisonSource[];
  fields?: ComparisonField[];
}

export interface ExplanationSourceSection {
  label: string;
  page_number?: number | null;
  display_page_label?: string | null;
  description?: string | null;
}

export interface ExplanationComparisonRow {
  field: string;
  left_label?: string | null;
  left_value?: unknown;
  right_label?: string | null;
  right_value?: unknown;
  status: "match" | "mismatch" | "missing" | "needs_review" | "skipped" | "not_applicable" | string;
  reason?: string | null;
}

export interface ExplanationEvidenceItem {
  label: string;
  page_number?: number | null;
  display_page_label?: string | null;
  evidence_type?: string | null;
  status?: string | null;
}

export interface ExplanationEvidenceGroup {
  title: string;
  items?: ExplanationEvidenceItem[];
}

export interface ExplanationDecision {
  user_facing_status: "passed" | "candidate_issue" | "needs_review" | "confirmed_error" | "refuted" | string;
  label?: string | null;
  reason?: string | null;
}

export interface ExplanationDetails {
  check_goal?: string | null;
  user_question?: string | null;
  overall_reason?: string | null;
  source_sections?: ExplanationSourceSection[];
  comparison_rows?: ExplanationComparisonRow[];
  evidence_groups?: ExplanationEvidenceGroup[];
  decision?: ExplanationDecision | null;
  next_action?: string | null;
}

export type PTRComparisonOverallStatus = "passed" | "needs_review" | "failed" | "audit_incomplete" | string;
export type PTRComparisonUserFacingStatus =
  | "covered_passed"
  | "coverage_only_needs_review"
  | "missing_in_report"
  | "value_mismatch"
  | "needs_review"
  | "candidate_issue"
  | "refuted"
  | "confirmed_error"
  | "confirmed_document_issue"
  | "confirmed_issue"
  | "needs_policy_review"
  | "audit_incomplete"
  | string;
export type PTRComparisonFinalStatus =
  | "passed"
  | "confirmed_error"
  | "confirmed_document_issue"
  | "confirmed_issue"
  | "needs_policy_review"
  | "manual_review_required"
  | "refuted"
  | "candidate_issue"
  | "audit_incomplete"
  | string;

export interface PTRReportAtomicResult {
  atomic_id: string;
  clause_id: string;
  label: string;
  actual?: string | null;
  unit?: string | null;
  preset?: string | null;
  report_item_no?: string | null;
  report_page?: number | null;
  report_clause_number?: string | null;
  report_source_row?: number | null;
  source_text?: string | null;
  confidence?: string | null;
  diagnostics?: Record<string, unknown>[];
  candidate_actuals?: string[];
}

export interface PTRReportMatch {
  item_no?: string | null;
  page?: number | null;
  report_page?: number | null;
  report_pages?: number[];
  page_span?: [number, number] | null;
  standard_clause?: string | null;
  item_name?: string | null;
  standard_requirement?: string | null;
  test_result?: string | null;
  single_conclusion?: string | null;
  remark?: string | null;
  report_atomic_results?: PTRReportAtomicResult[];
}

export interface PTRNormalizedComparison {
  requirement_type: "numeric_limit" | "text_requirement" | "coverage" | "external_standard_coverage" | "unknown" | string;
  expected?: unknown;
  actual?: unknown;
  unit?: string | null;
  operator?: string | null;
  status: "match" | "mismatch" | "needs_review" | string;
}

export interface PTRAtomicRequirement {
  atomic_id: string;
  clause_id: string;
  label: string;
  condition?: string | null;
  expected_text?: string | null;
  expected_value?: number | null;
  operator?: string | null;
  unit?: string | null;
  source: "ptr_text" | "ptr_table" | string;
  table_number?: string | null;
  table_title?: string | null;
  table_key?: string | null;
  metadata?: Record<string, unknown>;
}

export interface PTRAtomicComparisonRow {
  atomic_id: string;
  clause_id: string;
  label: string;
  preset?: string | null;
  condition?: string | null;
  model_column?: string | null;
  table_row_label?: string | null;
  parent_clause?: string | null;
  expected?: string | null;
  actual?: string | null;
  unit?: string | null;
  expected_operator?: string | null;
  expected_value?: number | null;
  expected_unit?: string | null;
  actual_operator?: string | null;
  actual_value?: number | null;
  actual_unit?: string | null;
  report_conclusion?: string | null;
  candidate_actuals?: string[];
  status: "match" | "mismatch" | "needs_review" | "candidate_found_needs_mapping" | "not_applicable" | string;
  reason?: string | null;
  report_page?: number | null;
  report_item_no?: string | null;
  report_clause_number?: string | null;
  report_source_row?: number | null;
  confidence?: string | null;
  source: "ptr_text" | "ptr_table" | string;
  source_text?: string | null;
  table_number?: string | null;
  table_title?: string | null;
  table_key?: string | null;
  diagnostics?: Record<string, unknown>[];
}

export interface PTRClauseStatement {
  clause_id: string;
  title?: string | null;
  local_text: string;
  page?: number | null;
}

export interface PTRReportClauseIdentity {
  identity_id: string;
  item_no?: string | null;
  group_id: string;
  clause_number?: string | null;
  title?: string | null;
  normalized_title?: string | null;
  standard_requirement_text?: string;
  row_label?: string | null;
  parent_clause?: string | null;
  referenced_tables?: string[];
  parameter_terms?: string[];
  units?: string[];
  test_result?: string | null;
  conclusion?: string | null;
  source_page?: number | null;
  source_row?: number | null;
  evidence_refs?: string[];
}

export interface PTRClauseIdentityCandidate {
  report_identity_id: string;
  ptr_clause_number: string;
  report_clause_number?: string | null;
  report_item_no?: string | null;
  report_title?: string | null;
  report_page?: number | null;
  report_source_row?: number | null;
  number_relation: "exact" | "different" | "parent_only" | "missing" | string;
  title_relation: "exact" | "alias" | "similar" | "conflict" | "missing" | string;
  table_row_relation: "exact" | "alias" | "similar" | "conflict" | "missing" | string;
  parameter_relation: "exact" | "alias" | "similar" | "conflict" | "missing" | string;
  parent_relation: "same" | "different" | string;
  score: number;
  positive_signals?: string[];
  negative_signals?: string[];
  rejected_reason?: string | null;
}

export interface PTRClauseIdentityAlignment {
  status: "exact_match" | "semantic_match_number_mismatch" | "identity_mismatch" | "ambiguous" | "missing" | "not_applicable" | string;
  ptr_clause_number: string;
  ptr_title?: string | null;
  selected_report_clause_number?: string | null;
  selected_report_title?: string | null;
  selected_report_item_no?: string | null;
  selected_report_page?: number | null;
  selected_report_source_row?: number | null;
  selected_report_identity?: PTRReportClauseIdentity | null;
  number_matches: boolean;
  title_matches: boolean;
  parameter_matches: boolean;
  table_row_matches: boolean;
  confidence: "high" | "medium" | "low" | string;
  reason: string;
  candidate_count: number;
  candidates?: PTRClauseIdentityCandidate[];
}

export interface PTRClauseSequenceOffsetEntry {
  ptr: string;
  report: string;
  title?: string | null;
  report_title?: string | null;
  report_item_no?: string | null;
  report_page?: number | null;
}

export interface PTRClauseSequenceOffsetGroup {
  aggregate_id?: string | null;
  parent_clause?: string | null;
  offset: number;
  confidence?: string | null;
  affected_clauses: PTRClauseSequenceOffsetEntry[];
}

export interface PTREffectiveRequirement {
  requirement_id: string;
  label: string;
  source_type: string;
  requirement_type?: string | null;
  parent_clause?: string | null;
  table_number?: string | null;
  table_title?: string | null;
  table_row_label?: string | null;
  model?: string | null;
  preset?: string | null;
  load?: string | null;
  condition?: string | null;
  selected_column?: string | null;
  expected?: string | null;
  operator?: string | null;
  expected_value?: number | null;
  unit?: string | null;
  source_page?: number | null;
  evidence_ref?: string | null;
}

export interface PTRReportRequirementMatch {
  report_item_no?: string | null;
  report_clause?: string | null;
  row_label?: string | null;
  condition?: string | null;
  model?: string | null;
  load?: string | null;
  preset?: string | null;
  standard_requirement_text: string;
  page?: number | null;
  source_row?: number | null;
  evidence_ref?: string | null;
}

export interface PTRTraceResultComparison {
  comparison_id: string;
  label: string;
  condition?: string | null;
  model?: string | null;
  load?: string | null;
  preset?: string | null;
  expected?: string | null;
  actual?: string | null;
  unit?: string | null;
  status: string;
  reason: string;
  verification_basis: string;
  page?: number | null;
  item_no?: string | null;
}

export interface PTRTraceDecision {
  status: string;
  reason: string;
  ptr_evidence_refs?: string[];
  report_evidence_refs?: string[];
}

export interface PTRTechnicalEvidence {
  ptr_full_text?: string | null;
  ptr_tables?: Record<string, unknown>[];
  report_groups?: Record<string, unknown>[];
  raw_finding_ids?: string[];
  evidence_refs?: string[];
}

export interface PTRCoverageComparisonRow {
  ptr_clause_id: string;
  ptr_title?: string | null;
  ptr_requirement?: string | null;
  report_item_no?: string | null;
  report_page?: number | null;
  report_standard_clause?: string | null;
  report_requirement_excerpt?: string | null;
  report_result?: string | null;
  report_conclusion?: string | null;
  status: PTRComparisonUserFacingStatus | string;
  reason?: string | null;
}

export interface PTRScopeRange {
  start: string;
  end: string;
  source_text: string;
}

export interface PTRExternalStandardRange {
  start_item_no: string;
  end_item_no: string;
  standard: string;
  source_page?: number | null;
  source_text: string;
}

export interface PTRScopeConsistency {
  status: "passed" | "failed" | "needs_review" | string;
  declared_scope?: string[];
  declared_scope_ranges?: PTRScopeRange[];
  actual_report_scope?: string[];
  external_standard_ranges?: PTRExternalStandardRange[];
  excluded_topics?: string[];
  ptr_direct_content_starts_after?: string | null;
  source_page?: number | null;
  source_text?: string | null;
  reason?: string | null;
}

export interface PTRReportModelCandidate {
  value: string;
  source: string;
  page?: number | null;
  confidence?: string | null;
}

export interface PTRReportModelContext {
  primary_model?: string | null;
  model_candidates?: PTRReportModelCandidate[];
  diagnostics?: string[];
}

export interface PTRTableAxis {
  axis_type: "model" | "preset" | "load" | "condition" | "unknown" | string;
  labels: string[];
}

export interface PTRTableRegistryEntry {
  parent_clause?: string | null;
  table_number: string;
  table_title?: string | null;
  row_labels?: string[];
  column_axes?: PTRTableAxis[];
  source_page?: number | null;
  table_id?: string | null;
}

export interface PTRExternalStandardCoverage {
  standard?: string | null;
  start_item_no?: string | null;
  end_item_no?: string | null;
  source_page?: number | null;
  source_text?: string | null;
  item_count?: number;
  passed_count?: number;
  review_count?: number;
  sample_items?: PTRReportMatch[];
}

export interface PTRComparisonItem {
  ptr_clause_id: string;
  ptr_title?: string | null;
  ptr_page?: number | null;
  ptr_requirement_text: string;
  report_matches: PTRReportMatch[];
  external_standard_coverage?: PTRExternalStandardCoverage | null;
  external_standard_coverages?: PTRExternalStandardCoverage[];
  atomic_requirements?: PTRAtomicRequirement[];
  atomic_comparison_rows?: PTRAtomicComparisonRow[];
  coverage_comparison_rows?: PTRCoverageComparisonRow[];
  ptr_clause_statement?: PTRClauseStatement | null;
  clause_identity_alignment?: PTRClauseIdentityAlignment | null;
  effective_requirements?: PTREffectiveRequirement[];
  report_requirement_matches?: PTRReportRequirementMatch[];
  result_comparisons?: PTRTraceResultComparison[];
  requirement_alignment?: PTRTraceDecision | null;
  result_compliance?: PTRTraceDecision | null;
  technical_evidence?: PTRTechnicalEvidence | null;
  normalized_comparison: PTRNormalizedComparison;
  rule_status: PTRComparisonUserFacingStatus;
  coverage_status?: PTRComparisonUserFacingStatus;
  user_facing_status: PTRComparisonUserFacingStatus;
  final_status: PTRComparisonFinalStatus;
  reason: string;
  next_action?: string | null;
  evidence_refs: string[];
  search_keywords?: string[];
  candidate_report_items?: PTRReportMatch[];
}

export interface PTRExcludedComparisonItem {
  ptr_clause_id: string;
  ptr_title?: string | null;
  ptr_requirement_text: string;
  status: "excluded_by_scope" | string;
  reason: string;
  excluded_topic?: string | null;
  evidence?: string | null;
}

export interface PTRComparisonDetails {
  overall_status: PTRComparisonOverallStatus;
  overall_summary: string;
  ptr_extraction_status?: string | null;
  ptr_ocr_required?: boolean;
  ptr_pages_need_ocr?: number[];
  source_type?: string | null;
  scope_consistency?: PTRScopeConsistency | null;
  report_model_context?: PTRReportModelContext | null;
  ptr_table_registry?: PTRTableRegistryEntry[];
  requirements_count: number;
  covered_count: number;
  missing_count: number;
  mismatch_count: number;
  needs_review_count: number;
  confirmed_errors_count: number;
  confirmed_findings_count: number;
  confirmed_document_issue_count: number;
  manual_review_required_count: number;
  policy_review_required_count: number;
  refuted_findings_count: number;
  clause_sequence_offset_groups?: PTRClauseSequenceOffsetGroup[];
  section_container_clause_ids?: string[];
  items: PTRComparisonItem[];
  excluded_items?: PTRExcludedComparisonItem[];
}

export interface CheckResultMetadata extends Record<string, unknown> {
  comparison_details?: ComparisonDetails;
  final_comparison_details?: ComparisonDetails;
  explanation_details?: ExplanationDetails;
  ptr_comparison_details?: PTRComparisonDetails;
}

export interface TaskResultMetadata extends Record<string, unknown> {
  ptr_comparison_details?: PTRComparisonDetails;
}

export interface CheckResult {
  task_id: string;
  check_id: string;
  check_name: string;
  status: CheckStatus;
  severity?: FindingSeverity | null;
  summary?: string | null;
  findings: Finding[];
  evidence: Evidence[];
  codex_reviews?: CodexReviewResult[];
  metrics: Record<string, unknown>;
  metadata: CheckResultMetadata;
}

export interface TaskResult {
  task_id: string;
  task_type: TaskType;
  summary: CheckSummary;
  check_results: CheckResult[];
  findings: Finding[];
  input_files: InputFileRef[];
  diagnostics: string[];
  metadata: TaskResultMetadata;
}

export type TaskModuleState = "ready" | "pending";

export interface TaskModule {
  id: string;
  title: string;
  description: string;
  state: TaskModuleState;
}

export function checkStatusLabel(status: CheckStatus): string {
  const labels: Record<CheckStatus, string> = {
    pass: "通过",
    fail: "失败",
    review: "需复核",
    skip: "跳过",
    system_error: "系统错误",
  };
  return labels[status];
}

export function taskStateLabel(status: TaskState): string {
  const labels: Record<TaskState, string> = {
    pending: "等待中",
    processing: "处理中",
    completed: "已完成",
    error: "失败",
  };
  return labels[status];
}
