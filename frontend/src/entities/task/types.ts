import type { CodexReviewResult } from "../codexReview/types";
import type { Evidence, Finding, FindingSeverity } from "../finding/types";

export type TaskType = "report_check" | "ptr_compare";
export type TaskState = "pending" | "processing" | "completed" | "error";
export type CheckStatus = "pass" | "fail" | "review" | "skip" | "system_error";
export type ExportFormat = "json" | "pdf" | "xlsx";
export type AuditScope = "full" | "targeted";
export type FinalAuditStatus = "passed" | "needs_manual_review" | "failed" | "audit_failed";

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
  metadata: Record<string, unknown>;
}

export interface TaskResult {
  task_id: string;
  task_type: TaskType;
  summary: CheckSummary;
  check_results: CheckResult[];
  findings: Finding[];
  input_files: InputFileRef[];
  diagnostics: string[];
  metadata: Record<string, unknown>;
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
