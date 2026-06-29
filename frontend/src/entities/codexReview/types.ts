import type { Finding } from "../finding/types";

export type CodexReviewVerdict = "confirm" | "refute" | "uncertain" | "add_finding";
export type CodexReviewStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";
export type CodexReviewConfidence = "high" | "medium" | "low";
export type CodexReviewTargetType =
  | "ptr_clause"
  | "ptr_table"
  | "ptr_parameter"
  | "report_rule"
  | "label_ocr"
  | "photo_caption"
  | "inspection_item"
  | "sample_description"
  | "page_number"
  | "finding"
  | "check_result"
  | "evidence_package";

export interface CodexEvidenceRef {
  ref_id: string;
  source_type: string;
  path?: string | null;
  page_number?: number | null;
  section?: string | null;
  description?: string | null;
  metadata: Record<string, unknown>;
}

export interface CodexReviewTarget {
  target_id: string;
  target_type: CodexReviewTargetType;
  check_id?: string | null;
  finding_id?: string | null;
  finding_code?: string | null;
  title?: string | null;
  summary?: string | null;
  evidence_refs: CodexEvidenceRef[];
  metadata: Record<string, unknown>;
}

export interface CodexReviewError {
  code: string;
  message: string;
  detail?: string | null;
  retryable: boolean;
}

export interface CodexSuggestedFinding {
  check_id?: string | null;
  severity?: string | null;
  code?: string | null;
  message: string;
  expected?: string | null;
  actual?: string | null;
  evidence_refs: string[];
  metadata: Record<string, unknown>;
}

export interface CodexReviewResult {
  review_id: string;
  request_id: string;
  task_id: string;
  target: CodexReviewTarget;
  status: CodexReviewStatus;
  verdict?: CodexReviewVerdict | null;
  confidence?: CodexReviewConfidence | null;
  reasoning_summary?: string | null;
  suggested_severity?: string | null;
  suggested_finding?: CodexSuggestedFinding | null;
  evidence_refs: string[];
  raw_output_path?: string | null;
  error?: CodexReviewError | null;
  created_at: string;
  completed_at?: string | null;
  metadata: Record<string, unknown>;
}

export interface CodexReviewSummary {
  total: number;
  confirm: number;
  refute: number;
  uncertain: number;
  add_finding: number;
  pending: number;
  running: number;
  succeeded: number;
  failed: number;
  skipped: number;
  failed_or_skipped: number;
}

export interface GroupedCodexReviews {
  byFindingId: Record<string, CodexReviewResult[]>;
  unassociated: CodexReviewResult[];
}

export type CodexFinalStatus =
  | "confirmed"
  | "refuted"
  | "manual_review_required"
  | "suggested_additional_finding"
  | "out_of_scope"
  | "summary_only"
  | "pending";

export const CODEX_VERDICT_LABELS: Record<CodexReviewVerdict, string> = {
  confirm: "Codex 已确认",
  refute: "Codex 认为可能误报",
  uncertain: "需人工复核",
  add_finding: "Codex 建议新增问题",
};

export const CODEX_STATUS_LABELS: Record<CodexReviewStatus, string> = {
  pending: "待审核",
  running: "审核中",
  succeeded: "审核完成",
  failed: "审核失败",
  skipped: "已跳过",
};

export const CODEX_CONFIDENCE_LABELS: Record<CodexReviewConfidence, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export function normalizeCodexReviews(reviews?: readonly CodexReviewResult[] | null): CodexReviewResult[] {
  return Array.isArray(reviews) ? [...reviews] : [];
}

export function summarizeCodexReviews(reviews?: readonly CodexReviewResult[] | null): CodexReviewSummary {
  const summary: CodexReviewSummary = {
    total: 0,
    confirm: 0,
    refute: 0,
    uncertain: 0,
    add_finding: 0,
    pending: 0,
    running: 0,
    succeeded: 0,
    failed: 0,
    skipped: 0,
    failed_or_skipped: 0,
  };

  for (const review of normalizeCodexReviews(reviews)) {
    summary.total += 1;
    summary[review.status] += 1;
    if (review.status === "failed" || review.status === "skipped") {
      summary.failed_or_skipped += 1;
    }
    if (review.verdict) {
      summary[review.verdict] += 1;
    }
  }

  return summary;
}

export function groupCodexReviewsByFinding(
  findings: readonly Finding[],
  reviews?: readonly CodexReviewResult[] | null,
): GroupedCodexReviews {
  const byFindingId = Object.fromEntries(findings.map((finding) => [finding.id, [] as CodexReviewResult[]]));
  const unassociated: CodexReviewResult[] = [];

  for (const review of normalizeCodexReviews(reviews)) {
    const finding = findAssociatedFinding(findings, review);
    if (finding) {
      byFindingId[finding.id].push(review);
    } else {
      unassociated.push(review);
    }
  }

  return { byFindingId, unassociated };
}

export function codexReviewTone(review: CodexReviewResult): "success" | "danger" | "warn" | "info" | "accent" {
  if (review.status === "failed") return "danger";
  if (review.status === "skipped") return "info";
  if (review.status === "pending" || review.status === "running") return "accent";
  if (review.verdict === "confirm") return "success";
  if (review.verdict === "refute") return "info";
  if (review.verdict === "uncertain") return "warn";
  if (review.verdict === "add_finding") return "accent";
  return "info";
}

export function codexReviewPrimaryLabel(review: CodexReviewResult): string {
  if (review.verdict) return CODEX_VERDICT_LABELS[review.verdict];
  return CODEX_STATUS_LABELS[review.status];
}

export function findingCodexFinalStatus(
  finding: Finding,
  reviews?: readonly CodexReviewResult[] | null,
): CodexFinalStatus {
  const metadataStatus = metadataString(finding.metadata, "final_status");
  if (isCodexFinalStatus(metadataStatus)) return metadataStatus;

  const review = normalizeCodexReviews(reviews).find((item) => item.status === "succeeded" && item.verdict);
  if (review?.verdict === "confirm") return "confirmed";
  if (review?.verdict === "refute") return "refuted";
  if (review?.verdict === "uncertain") return "manual_review_required";
  if (review?.verdict === "add_finding") return "suggested_additional_finding";
  return "pending";
}

export function codexFinalStatusLabel(status: CodexFinalStatus): string {
  if (status === "confirmed") return "Codex 已确认";
  if (status === "refuted") return "Codex 已反驳";
  if (status === "manual_review_required") return "人工复核";
  if (status === "suggested_additional_finding") return "Codex 建议新增";
  if (status === "out_of_scope") return "本次未覆盖";
  if (status === "summary_only") return "摘要目标";
  return "待 Codex 审核";
}

export function codexFinalStatusTone(status: CodexFinalStatus): "success" | "danger" | "warn" | "info" | "accent" {
  if (status === "confirmed") return "success";
  if (status === "manual_review_required") return "warn";
  if (status === "suggested_additional_finding") return "accent";
  return "info";
}

function findAssociatedFinding(findings: readonly Finding[], review: CodexReviewResult): Finding | undefined {
  const target = review.target;
  const targetFindingId =
    target.finding_id ?? metadataString(target.metadata, "finding_id") ?? metadataString(target.metadata, "deterministic_finding_id");
  if (targetFindingId) {
    const exact = findings.find((finding) => finding.id === targetFindingId);
    if (exact) return exact;
  }

  const metadataFindingCode =
    target.finding_code ?? metadataString(target.metadata, "finding_code") ?? metadataString(review.metadata, "finding_code");
  if (metadataFindingCode) {
    const byCode = findings.find(
      (finding) =>
        finding.code === metadataFindingCode && (!target.check_id || finding.check_id === target.check_id),
    );
    if (byCode) return byCode;
  }

  if (target.check_id) {
    const sameCheckFindings = findings.filter((finding) => finding.check_id === target.check_id);
    if (sameCheckFindings.length === 1) return sameCheckFindings[0];
  }

  return undefined;
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function isCodexFinalStatus(value: string | null): value is CodexFinalStatus {
  return (
    value === "confirmed" ||
    value === "refuted" ||
    value === "manual_review_required" ||
    value === "suggested_additional_finding" ||
    value === "out_of_scope" ||
    value === "summary_only" ||
    value === "pending"
  );
}
