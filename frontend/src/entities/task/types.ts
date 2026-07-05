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
  | "error";
export type CodexAuditProgressStatus = "pending" | "running" | "retrying" | "completed" | "failed";

export interface InputFileRef {
  file_id: string;
  file_name: string;
  content_type: string;
}

export interface AuditOptions {
  included_check_ids?: string;
  included_finding_codes?: string;
  excluded_check_ids?: string;
  max_targets_per_batch?: number;
  max_parallel_jobs?: number;
  timeout_seconds?: number;
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
  refuted_findings_count: number;
  manual_review_required_count: number;
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
  | "missing_in_report"
  | "value_mismatch"
  | "needs_review"
  | "candidate_issue"
  | "refuted"
  | "confirmed_error"
  | "audit_incomplete"
  | string;
export type PTRComparisonFinalStatus =
  | "passed"
  | "confirmed_error"
  | "manual_review_required"
  | "refuted"
  | "candidate_issue"
  | "audit_incomplete"
  | string;

export interface PTRReportMatch {
  item_no?: string | null;
  report_page?: number | null;
  standard_clause?: string | null;
  item_name?: string | null;
  standard_requirement?: string | null;
  test_result?: string | null;
  single_conclusion?: string | null;
  remark?: string | null;
}

export interface PTRNormalizedComparison {
  requirement_type: "numeric_limit" | "text_requirement" | "coverage" | "unknown" | string;
  expected?: unknown;
  actual?: unknown;
  unit?: string | null;
  operator?: string | null;
  status: "match" | "mismatch" | "needs_review" | string;
}

export interface PTRComparisonItem {
  ptr_clause_id: string;
  ptr_title?: string | null;
  ptr_page?: number | null;
  ptr_requirement_text: string;
  report_matches: PTRReportMatch[];
  normalized_comparison: PTRNormalizedComparison;
  rule_status: PTRComparisonUserFacingStatus;
  user_facing_status: PTRComparisonUserFacingStatus;
  final_status: PTRComparisonFinalStatus;
  reason: string;
  next_action?: string | null;
  evidence_refs: string[];
  search_keywords?: string[];
  candidate_report_items?: PTRReportMatch[];
}

export interface PTRComparisonDetails {
  overall_status: PTRComparisonOverallStatus;
  overall_summary: string;
  requirements_count: number;
  covered_count: number;
  missing_count: number;
  mismatch_count: number;
  needs_review_count: number;
  confirmed_errors_count: number;
  manual_review_required_count: number;
  refuted_findings_count: number;
  items: PTRComparisonItem[];
}

export interface CheckResultMetadata extends Record<string, unknown> {
  comparison_details?: ComparisonDetails;
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
