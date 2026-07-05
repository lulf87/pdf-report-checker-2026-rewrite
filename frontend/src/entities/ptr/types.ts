import type { CodexReviewResult } from "../codexReview/types";
import { normalizeCodexReviews } from "../codexReview/types";
import type { DiffFragment, Finding, FindingSeverity } from "../finding/types";
import type {
  CheckResult,
  PTRComparisonItem,
  PTRExcludedComparisonItem,
  PTRScopeConsistency,
  TaskResult,
  TaskStatus,
} from "../task/types";

export type PTRFilterMode = "all" | "issues";

export interface PTRClauseViewModel {
  id: string;
  checkId: string;
  title: string;
  status: CheckResult["status"];
  severity?: FindingSeverity | null;
  summary?: string | null;
  findings: Finding[];
  diffs: DiffFragment[];
  codexReviews: CodexReviewResult[];
  ptrItem?: PTRComparisonItem | null;
  scopeConsistency?: PTRScopeConsistency | null;
}

export interface PTRCompareResultView {
  task: TaskStatus;
  result: TaskResult;
  clauses: PTRClauseViewModel[];
}

export function toPTRClauseViewModel(result: CheckResult, index: number): PTRClauseViewModel {
  const primaryFinding = result.findings[0];
  return {
    id: `${result.check_id}-${index}`,
    checkId: result.check_id,
    title: result.check_name || result.check_id,
    status: result.status,
    severity: result.severity ?? primaryFinding?.severity ?? null,
    summary: result.summary,
    findings: result.findings,
    diffs: result.findings.flatMap((finding) => finding.diff_fragments),
    codexReviews: normalizeCodexReviews(result.codex_reviews),
    ptrItem: null,
    scopeConsistency: null,
  };
}

export function toPTRClauseViewModels(result: TaskResult): PTRClauseViewModel[] {
  const details = result.metadata.ptr_comparison_details;
  if (details?.items?.length) {
    const codexReviews = result.check_results.flatMap((item) => normalizeCodexReviews(item.codex_reviews));
    const included = details.items.map((item, index) => {
      const findings = result.findings.filter((finding) => findingMatchesPtrItem(finding, item));
      return {
        id: `PTR-${item.ptr_clause_id}-${index}`,
        checkId: item.ptr_clause_id,
        title: item.ptr_title || "技术要求",
        status: ptrItemCheckStatus(item),
        severity: ptrItemSeverity(item),
        summary: item.reason,
        findings,
        diffs: findings.flatMap((finding) => finding.diff_fragments),
        codexReviews: codexReviews.filter((review) => {
          const findingIds = new Set(findings.map((finding) => finding.id));
          return review.target.finding_id ? findingIds.has(review.target.finding_id) : review.target.check_id?.startsWith("PTR");
        }),
        ptrItem: item,
        scopeConsistency: details.scope_consistency ?? null,
      };
    });
    const excluded = (details.excluded_items ?? []).map((item, index) => ({
      id: `PTR-excluded-${item.ptr_clause_id}-${index}`,
      checkId: item.ptr_clause_id,
      title: item.ptr_title || "排除条款",
      status: "skip" as CheckResult["status"],
      severity: "info" as const,
      summary: item.reason,
      findings: [],
      diffs: [],
      codexReviews: [],
      ptrItem: excludedToPtrItem(item),
      scopeConsistency: details.scope_consistency ?? null,
    }));
    return [...included, ...excluded];
  }
  return result.check_results.map((item, index) => toPTRClauseViewModel(item, index));
}

export function isPTRIssue(clause: PTRClauseViewModel): boolean {
  if (clause.ptrItem) {
    return !["covered_passed", "refuted", "excluded_by_scope"].includes(clause.ptrItem.coverage_status ?? clause.ptrItem.user_facing_status);
  }
  return clause.status === "fail" || clause.status === "review" || clause.status === "system_error";
}

function findingMatchesPtrItem(finding: Finding, item: PTRComparisonItem): boolean {
  const metadataClause = finding.metadata.clause_number;
  if (typeof metadataClause === "string" && metadataClause === item.ptr_clause_id) return true;
  return finding.id.includes(`:${item.ptr_clause_id}:`);
}

function ptrItemCheckStatus(item: PTRComparisonItem): CheckResult["status"] {
  const status = item.coverage_status ?? item.user_facing_status;
  if (status === "covered_passed" || status === "refuted") return "pass";
  if (status === "excluded_by_scope") return "skip";
  if (status === "confirmed_error" || status === "audit_incomplete") return "fail";
  return "review";
}

function ptrItemSeverity(item: PTRComparisonItem): FindingSeverity | null {
  const status = item.coverage_status ?? item.user_facing_status;
  if (status === "confirmed_error" || status === "audit_incomplete") return "error";
  if (status === "covered_passed" || status === "refuted" || status === "excluded_by_scope") return "info";
  return "warn";
}

function excludedToPtrItem(item: PTRExcludedComparisonItem): PTRComparisonItem {
  return {
    ptr_clause_id: item.ptr_clause_id,
    ptr_title: item.ptr_title,
    ptr_requirement_text: item.ptr_requirement_text,
    report_matches: [],
    external_standard_coverages: [],
    atomic_requirements: [],
    atomic_comparison_rows: [],
    normalized_comparison: {
      requirement_type: "excluded_by_scope",
      expected: item.ptr_requirement_text,
      actual: item.excluded_topic,
      status: "not_applicable",
    },
    rule_status: item.status,
    coverage_status: item.status,
    user_facing_status: item.status,
    final_status: "passed",
    reason: item.reason,
    evidence_refs: [],
    search_keywords: [item.ptr_clause_id, item.ptr_title ?? ""].filter(Boolean),
    candidate_report_items: [],
  };
}
