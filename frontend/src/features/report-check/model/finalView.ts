import { findingCodexFinalStatus, normalizeCodexReviews, summarizeCodexReviews } from "../../../entities/codexReview/types";
import type { CodexReviewResult } from "../../../entities/codexReview/types";
import type { Finding } from "../../../entities/finding/types";
import type { CheckResult, TaskResult } from "../../../entities/task/types";

export type CheckFinalStatus =
  | "passed"
  | "passed_after_review"
  | "needs_manual_review"
  | "confirmed_error"
  | "candidate_only"
  | "audit_incomplete";

export type FinalTone = "success" | "danger" | "warn" | "info" | "accent";

export interface CheckFinalView {
  final_status: CheckFinalStatus;
  final_label: string;
  final_summary: string;
  confirmed_errors_count: number;
  manual_review_required_count: number;
  refuted_findings_count: number;
  candidate_findings_count: number;
  codex_reviews_count: number;
  primary_tone: FinalTone;
  codex_verdict_labels: string[];
}

export interface TaskFinalView {
  label: string;
  summary: string;
  tone: FinalTone;
}

export function buildTaskFinalView(result: TaskResult): TaskFinalView {
  const audit = metadataRecord(result.metadata, "codex_audit");
  const finalStatus = result.summary.final_audit_status ?? metadataString(audit, "final_audit_status");
  const confirmed = summaryNumber(result, audit, "confirmed_errors_count");
  const manual = summaryNumber(result, audit, "manual_review_required_count");
  const runtimeFailures = summaryNumber(result, audit, "codex_runtime_failure_count");
  const unreviewed = summaryNumber(result, audit, "unreviewed_required_findings_count");

  if (finalStatus === "audit_failed" || runtimeFailures > 0 || unreviewed > 0) {
    return {
      label: "LLM 复核未完成",
      summary: "这不是报告确认错误，可重试或关闭 LLM 增强识别查看规则初筛。",
      tone: "danger",
    };
  }
  if (finalStatus === "failed" || confirmed > 0) {
    return {
      label: "本次核对不通过",
      summary: confirmed > 0 ? `发现 ${confirmed} 项确认问题。` : "发现确认问题。",
      tone: "danger",
    };
  }
  if (finalStatus === "needs_manual_review" || manual > 0) {
    return {
      label: "本次核对需人工复核",
      summary: manual > 0 ? `仍有 ${manual} 项无法自动确认。` : "仍有项目无法自动确认。",
      tone: "warn",
    };
  }
  if (finalStatus === "passed") {
    return {
      label: "本次核对通过",
      summary: "未发现确认问题或待人工复核项。",
      tone: "success",
    };
  }
  if (result.summary.candidate_errors_count > 0 || result.summary.candidate_findings_count > 0) {
    return {
      label: "规则初筛完成",
      summary: "存在规则初筛候选项，尚未形成完整 LLM/Codex 最终复审口径。",
      tone: "warn",
    };
  }
  return {
    label: "本次核对通过",
    summary: "未发现确认问题或待人工复核项。",
    tone: "success",
  };
}

export function buildCheckFinalView(check: CheckResult): CheckFinalView {
  const reviews = normalizeCodexReviews(check.codex_reviews);
  const candidateCount = check.findings.length;
  const failedReviewCount = reviews.filter((review) => review.status === "failed" || review.status === "skipped").length;
  const finalStatuses = check.findings.map((finding) => findingCodexFinalStatus(finding, reviewsForFinding(finding, reviews)));
  const refutedCount = finalStatuses.filter((status) => status === "refuted").length;
  const manualCount = finalStatuses.filter((status) => status === "manual_review_required").length;
  const confirmedCount = check.findings.filter((finding, index) => {
    const status = finalStatuses[index];
    return status === "confirmed" && finding.severity === "error";
  }).length;
  const finalizedCount = refutedCount + manualCount + confirmedCount;
  const codexSummary = summarizeCodexReviews(reviews);
  const codexVerdictLabels = codexVerdictUserLabels(reviews);

  if (confirmedCount > 0) {
    return view({
      check,
      final_status: "confirmed_error",
      final_label: confirmedLabel(check),
      final_summary: confirmedSummary(check, confirmedCount),
      confirmed_errors_count: confirmedCount,
      manual_review_required_count: manualCount,
      refuted_findings_count: refutedCount,
      candidate_findings_count: candidateCount,
      codex_reviews_count: reviews.length,
      primary_tone: "danger",
      codex_verdict_labels: codexVerdictLabels,
    });
  }

  if (manualCount > 0) {
    return view({
      check,
      final_status: "needs_manual_review",
      final_label: manualLabel(check),
      final_summary: manualSummary(check, manualCount),
      confirmed_errors_count: confirmedCount,
      manual_review_required_count: manualCount,
      refuted_findings_count: refutedCount,
      candidate_findings_count: candidateCount,
      codex_reviews_count: reviews.length,
      primary_tone: "warn",
      codex_verdict_labels: codexVerdictLabels,
    });
  }

  if (failedReviewCount > 0 || (candidateCount > 0 && reviews.length > 0 && finalizedCount < candidateCount)) {
    return view({
      check,
      final_status: "audit_incomplete",
      final_label: "LLM复核未完成",
      final_summary: "本项规则核对已完成，但 LLM/Codex 未返回完整复审结果；这不是报告确认错误。",
      confirmed_errors_count: confirmedCount,
      manual_review_required_count: manualCount,
      refuted_findings_count: refutedCount,
      candidate_findings_count: candidateCount,
      codex_reviews_count: reviews.length,
      primary_tone: "danger",
      codex_verdict_labels: codexVerdictLabels,
    });
  }

  if (candidateCount > 0 && refutedCount === candidateCount) {
    return view({
      check,
      final_status: "passed_after_review",
      final_label: passedAfterReviewLabel(check),
      final_summary: passedAfterReviewSummary(check, candidateCount),
      confirmed_errors_count: 0,
      manual_review_required_count: 0,
      refuted_findings_count: refutedCount,
      candidate_findings_count: candidateCount,
      codex_reviews_count: reviews.length,
      primary_tone: "success",
      codex_verdict_labels: codexVerdictLabels.length ? codexVerdictLabels : ["候选问题已排除"],
    });
  }

  if (candidateCount > 0) {
    const hasCodex = reviews.length > 0 || codexSummary.total > 0;
    return view({
      check,
      final_status: hasCodex ? "audit_incomplete" : "candidate_only",
      final_label: hasCodex ? "LLM复核未完成" : "规则初筛候选，待复审",
      final_summary: hasCodex
        ? "本项仍缺少完整 LLM/Codex 最终复审结果；请重试或查看技术详情。"
        : `规则初筛发现 ${candidateCount} 个候选问题，尚未完成 LLM/Codex 复审。`,
      confirmed_errors_count: confirmedCount,
      manual_review_required_count: manualCount,
      refuted_findings_count: refutedCount,
      candidate_findings_count: candidateCount,
      codex_reviews_count: reviews.length,
      primary_tone: hasCodex ? "danger" : "warn",
      codex_verdict_labels: codexVerdictLabels,
    });
  }

  return view({
    check,
    final_status: "passed",
    final_label: "通过",
    final_summary: passedSummary(check),
    confirmed_errors_count: 0,
    manual_review_required_count: 0,
    refuted_findings_count: 0,
    candidate_findings_count: 0,
    codex_reviews_count: reviews.length,
    primary_tone: "success",
    codex_verdict_labels: codexVerdictLabels,
  });
}

export function finalStatusPriority(status: CheckFinalStatus): number {
  if (status === "confirmed_error") return 0;
  if (status === "needs_manual_review") return 1;
  if (status === "candidate_only") return 2;
  if (status === "audit_incomplete") return 3;
  if (status === "passed_after_review") return 4;
  return 5;
}

export function codexVerdictUserLabel(verdict: string | null | undefined): string {
  if (verdict === "refute") return "候选问题已排除";
  if (verdict === "confirm") return "复审确认问题";
  if (verdict === "uncertain") return "仍需人工复核";
  if (verdict === "add_finding") return "复审建议新增问题";
  return "复审已完成";
}

function view(viewModel: CheckFinalView & { check: CheckResult }): CheckFinalView {
  const { check: _check, ...rest } = viewModel;
  return rest;
}

function passedAfterReviewLabel(check: CheckResult): string {
  if (check.check_id === "C07") return "通过（表格候选问题已排除）";
  return "通过（候选已排除）";
}

function passedAfterReviewSummary(check: CheckResult, candidateCount: number): string {
  if (check.check_id === "C04") {
    return `常规 OCR 未抽到部分标签字段，因此规则初筛产生 ${candidateCount} 个候选问题；LLM/Codex 复审后确认这些候选不是最终错误。`;
  }
  if (check.check_id === "C07") {
    return `规则初筛发现 ${candidateCount} 个表格候选问题，均已由 LLM/Codex 复审排除；当前没有确认错误或待人工复核项。`;
  }
  return `规则初筛发现 ${candidateCount} 个候选问题，均已由 LLM/Codex 复审排除；当前没有确认错误或待人工复核项。`;
}

function passedSummary(check: CheckResult): string {
  const explanation = metadataRecord(check.metadata, "explanation_details");
  const overallReason = metadataString(explanation, "overall_reason");
  if (overallReason) return overallReason;
  return check.summary || "本项核对通过，未发现确认问题或待人工复核项。";
}

function manualLabel(check: CheckResult): string {
  if (
    check.check_id === "C07" &&
    check.findings.some((finding) => finding.code === "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX")
  ) {
    return "需人工复核：复杂矩阵表";
  }
  return "仍需人工复核";
}

function manualSummary(check: CheckResult, manualCount: number): string {
  if (
    check.check_id === "C07" &&
    check.findings.some((finding) => finding.code === "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX")
  ) {
    return "复杂矩阵表仍需要人工查看矩阵列映射、单项结论列和跨页续表结构。";
  }
  return `仍有 ${manualCount} 项无法自动确认，需要人工复核。`;
}

function confirmedLabel(check: CheckResult): string {
  if (check.check_id === "C07") return "不通过：检验结果与单项结论不一致";
  return "不通过";
}

function confirmedSummary(check: CheckResult, confirmedCount: number): string {
  if (check.check_id === "C07") {
    return `复审确认 ${confirmedCount} 项检验结果与单项结论不一致。`;
  }
  return `复审确认 ${confirmedCount} 项最终问题。`;
}

function reviewsForFinding(finding: Finding, reviews: CodexReviewResult[]): CodexReviewResult[] {
  return reviews.filter((review) => {
    const targetFindingId =
      review.target?.finding_id ??
      metadataString(review.target?.metadata ?? {}, "finding_id") ??
      metadataString(review.target?.metadata ?? {}, "deterministic_finding_id");
    if (targetFindingId && targetFindingId === finding.id) return true;
    const metadataFindingCode =
      review.target?.finding_code ?? metadataString(review.target?.metadata ?? {}, "finding_code") ?? metadataString(review.metadata, "finding_code");
    return Boolean(metadataFindingCode && metadataFindingCode === finding.code && (!review.target?.check_id || review.target.check_id === finding.check_id));
  });
}

function codexVerdictUserLabels(reviews: CodexReviewResult[]): string[] {
  const labels = reviews
    .filter((review) => review.status === "succeeded" && review.verdict)
    .map((review) => codexVerdictUserLabel(review.verdict));
  return [...new Set(labels)];
}

function metadataRecord(metadata: Record<string, unknown>, key: string): Record<string, unknown> {
  const value = metadata[key];
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function summaryNumber(result: TaskResult, audit: Record<string, unknown>, key: keyof TaskResult["summary"]): number {
  const summaryValue = result.summary[key];
  if (typeof summaryValue === "number") return summaryValue;
  const auditValue = audit[key];
  return typeof auditValue === "number" ? auditValue : 0;
}
