import type { CodexReviewResult } from "../codexReview/types";
import { normalizeCodexReviews } from "../codexReview/types";
import type { DiffFragment, Finding, FindingSeverity } from "../finding/types";
import type { CheckResult, TaskResult, TaskStatus } from "../task/types";

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
  };
}

export function isPTRIssue(clause: PTRClauseViewModel): boolean {
  return clause.status === "fail" || clause.status === "review" || clause.status === "system_error";
}
