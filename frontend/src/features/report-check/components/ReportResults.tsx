import { useMemo, useState } from "react";

import {
  codexFinalStatusLabel,
  codexFinalStatusTone,
  findingCodexFinalStatus,
  groupCodexReviewsByFinding,
  normalizeCodexReviews,
} from "../../../entities/codexReview/types";
import {
  findingUserFacingStatus,
  findingUserFacingStatusLabel,
  findingUserFacingStatusTone,
  severityTone,
} from "../../../entities/finding/types";
import type { Finding, FindingSeverity } from "../../../entities/finding/types";
import type { UserFacingFindingStatus } from "../../../entities/finding/types";
import { REPORT_RULE_GROUPS, checkResultSeverity } from "../../../entities/report/types";
import type { ReportSeverityFilter } from "../../../entities/report/types";
import type { CheckResult, TaskResult, TaskStatus } from "../../../entities/task/types";
import { checkStatusLabel } from "../../../entities/task/types";
import { AnimatedCounter } from "../../../shared/ui/AnimatedCounter";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { ExportButtonGroup } from "../../../shared/ui/ExportButton";
import { GlassCard } from "../../../shared/ui/GlassCard";
import { CodexReviewList, CodexReviewOverview, FindingCodexReviewSummary } from "../../codex-review/components/CodexReviewPanel";

export interface ReportResultsProps {
  task: TaskStatus;
  result: TaskResult;
  onBack: () => void;
  onReupload: () => void;
}

export function ReportResults({ task, result, onBack, onReupload }: ReportResultsProps) {
  const [severityFilter, setSeverityFilter] = useState<ReportSeverityFilter>("all");
  const [checkIdFilter, setCheckIdFilter] = useState<string>("all");
  const [exportError, setExportError] = useState<string | null>(null);
  const resultBadge = finalResultBadge(result);
  const checkIds = useMemo(() => result.check_results.map((item) => item.check_id), [result.check_results]);
  const codexReviews = useMemo(
    () => result.check_results.flatMap((item) => normalizeCodexReviews(item.codex_reviews)),
    [result.check_results],
  );
  const filteredChecks = result.check_results.filter((check) => {
    const severity = checkResultSeverity(check);
    return (
      (severityFilter === "all" || severity === severityFilter) &&
      (checkIdFilter === "all" || check.check_id === checkIdFilter)
    );
  });

  return (
    <section className="panel-stack">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">REPORT RESULT</p>
          <h1>报告自检结果</h1>
          <p className="muted">任务 ID: {task.task_id}</p>
        </div>
        <Badge variant={resultBadge.variant}>{resultBadge.label}</Badge>
      </header>

      <div className="metric-grid">
        <Metric label="候选错误" value={result.summary.candidate_errors_count} tone="warn" />
        <Metric label="确认错误" value={result.summary.confirmed_errors_count} tone="danger" />
        <Metric label="人工复核" value={result.summary.manual_review_required_count} tone="warn" />
        <Metric label="已反驳候选" value={result.summary.refuted_findings_count} />
        {result.summary.out_of_scope_findings_count > 0 ? (
          <Metric label="本次未覆盖" value={result.summary.out_of_scope_findings_count} />
        ) : null}
      </div>

      <CodexAuditScopeNotice metadata={result.metadata} />

      <CodexReviewOverview reviews={codexReviews} />

      <GlassCard className="result-card">
        <div className="row-head">
          <div className="filter-row" role="group" aria-label="报告自检筛选">
            <select
              aria-label="按严重级别筛选"
              onChange={(event) => setSeverityFilter(event.target.value as ReportSeverityFilter)}
              value={severityFilter}
            >
              <option value="all">全部级别</option>
              <option value="error">候选错误</option>
              <option value="warn">需复核</option>
              <option value="info">信息</option>
            </select>
            <select aria-label="按规则编号筛选" onChange={(event) => setCheckIdFilter(event.target.value)} value={checkIdFilter}>
              <option value="all">全部规则</option>
              {checkIds.map((checkId) => (
                <option key={checkId} value={checkId}>
                  {checkId}
                </option>
              ))}
            </select>
          </div>
          <ExportButtonGroup onError={setExportError} taskId={task.task_id} />
        </div>
        {exportError ? <p className="form-error">{exportError}</p> : null}
      </GlassCard>

      {REPORT_RULE_GROUPS.map((group) => {
        const groupChecks = filteredChecks.filter((item) => group.checkIds.includes(item.check_id as never));
        if (groupChecks.length === 0) return null;
        return <CheckGroup checks={groupChecks} description={group.description} key={group.title} title={group.title} />;
      })}

      {filteredChecks.length === 0 ? (
        <GlassCard className="result-card">
          <p className="muted">当前筛选条件下没有结果。</p>
        </GlassCard>
      ) : null}

      {result.diagnostics.length > 0 ? (
        <GlassCard className="result-card">
          <h2>诊断信息</h2>
          <ul className="diagnostic-list">
            {result.diagnostics.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </GlassCard>
      ) : null}

      <div className="button-row">
        <Button onClick={onBack} variant="secondary">
          返回首页
        </Button>
        <Button onClick={onReupload}>重新上传</Button>
      </div>
    </section>
  );
}

function Metric({ label, value, tone = "info" }: { label: string; value: number; tone?: "info" | "danger" | "warn" }) {
  return (
    <GlassCard className={`metric-card ${tone === "danger" ? "issue-danger" : tone === "warn" ? "issue-warn" : ""}`}>
      <p className="muted">{label}</p>
      <p className="metric-value">
        <AnimatedCounter value={value} />
      </p>
    </GlassCard>
  );
}

function finalResultBadge(result: TaskResult): { label: string; variant: "success" | "danger" | "warn" | "info" } {
  if (result.summary.final_audit_status === "audit_failed") {
    return { label: "Codex 审核未完成", variant: "danger" };
  }
  if (result.summary.final_audit_status === "failed") {
    return { label: "Codex 审核完成", variant: "danger" };
  }
  if (result.summary.final_audit_status === "needs_manual_review") {
    return { label: "Codex 审核完成", variant: "warn" };
  }
  if (result.summary.final_audit_status === "passed") {
    return { label: "Codex 审核完成", variant: "success" };
  }
  if (result.summary.codex_runtime_failure_count > 0 || result.summary.unreviewed_required_findings_count > 0) {
    return { label: "Codex 审核未完成", variant: "danger" };
  }
  if (result.summary.confirmed_errors_count > 0) {
    return { label: "Codex 确认错误", variant: "danger" };
  }
  if (result.summary.manual_review_required_count > 0) {
    return { label: "需人工复核", variant: "warn" };
  }
  if (result.summary.codex_reviews_count === 0 && result.summary.candidate_errors_count > 0) {
    return { label: "候选错误待审核", variant: "warn" };
  }
  return { label: "未见最终错误", variant: "success" };
}

function CodexAuditScopeNotice({ metadata }: { metadata: Record<string, unknown> }) {
  const auditMetadata = metadataRecord(metadata, "codex_audit");
  const auditScope = metadataString(auditMetadata, "audit_scope");
  const includedCheckIds = metadataArray(auditMetadata, "included_check_ids");

  if (auditScope !== "targeted") return null;

  return (
    <GlassCard className="result-card">
      <div className="row-head">
        <div>
          <p className="row-title">Codex targeted validation</p>
          <p className="muted">
            本次只覆盖 {includedCheckIds.length > 0 ? includedCheckIds.join(", ") : "配置筛选范围"}，未覆盖候选会标记为“本次未覆盖”。
          </p>
        </div>
        <Badge variant="warn">非完整审核</Badge>
      </div>
    </GlassCard>
  );
}

function metadataRecord(metadata: Record<string, unknown>, key: string): Record<string, unknown> {
  const value = metadata[key];
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function metadataString(metadata: Record<string, unknown>, key: string): string | null {
  const value = metadata[key];
  return typeof value === "string" ? value : null;
}

function metadataArray(metadata: Record<string, unknown>, key: string): string[] {
  const value = metadata[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function CheckGroup({ title, description, checks }: { title: string; description: string; checks: CheckResult[] }) {
  return (
    <GlassCard className="results-card">
      <h2>{title}</h2>
      <p className="muted">{description}</p>
      <div className="check-list">
        {checks.map((check) => (
          <CheckRow check={check} key={check.check_id} />
        ))}
      </div>
    </GlassCard>
  );
}

function CheckRow({ check }: { check: CheckResult }) {
  const [expanded, setExpanded] = useState(false);
  const severity = checkResultSeverity(check);
  const checkUserStatus = checkUserFacingStatus(check);
  const tone = userFacingCheckTone(checkUserStatus, severity);
  const codexReviews = normalizeCodexReviews(check.codex_reviews);
  const groupedCodexReviews = groupCodexReviewsByFinding(check.findings, codexReviews);

  return (
    <article className={`check-row ${tone === "danger" ? "issue-danger" : tone === "warn" ? "issue-warn" : ""}`}>
      <div className="row-head">
        <div>
          <p className="row-title">
            {check.check_id}: {check.check_name}
          </p>
          <p className="row-summary">{check.summary || checkStatusLabel(check.status)}</p>
        </div>
        <div className="button-row">
          {codexReviews.length > 0 ? <Badge variant="accent">Codex {codexReviews.length}</Badge> : null}
          <Badge pulse={severity !== "info"} variant={tone}>
            {userFacingCheckLabel(checkUserStatus)}
          </Badge>
          <Button onClick={() => setExpanded((value) => !value)} size="sm" variant="ghost">
            {expanded ? "收起" : "展开"}
          </Button>
        </div>
      </div>
      {expanded ? (
        <div className="details">
          {check.findings.length > 0 ? (
            <FindingList findings={check.findings} reviewsByFindingId={groupedCodexReviews.byFindingId} />
          ) : (
            <p className="muted">后端未返回 Finding。</p>
          )}
          <CodexReviewList reviews={groupedCodexReviews.unassociated} title="其他 Codex 审核意见" />
        </div>
      ) : null}
    </article>
  );
}

function FindingList({
  findings,
  reviewsByFindingId,
}: {
  findings: Finding[];
  reviewsByFindingId: Record<string, ReturnType<typeof normalizeCodexReviews>>;
}) {
  return (
    <div className="panel-stack">
      {findings.map((finding) => (
        <FindingItem finding={finding} key={finding.id} reviews={reviewsByFindingId[finding.id]} />
      ))}
    </div>
  );
}

function FindingItem({ finding, reviews }: { finding: Finding; reviews: ReturnType<typeof normalizeCodexReviews> }) {
  const finalStatus = findingCodexFinalStatus(finding, reviews);
  const userStatus = findingUserFacingStatus(finding, finalStatus);

  return (
    <div className="evidence-text">
      <div className="button-row">
        <Badge variant={findingUserFacingStatusTone(userStatus)}>
          {findingUserFacingStatusLabel(userStatus, finding)}
        </Badge>
        {userStatus === "needs_review" && finalStatus !== "pending" ? (
          <Badge variant={codexFinalStatusTone(finalStatus)}>{codexFinalStatusLabel(finalStatus)}</Badge>
        ) : null}
        <span>
          <strong>{finding.code}</strong>: {finding.message}
          {finding.location?.page_number ? `（第 ${finding.location.page_number} 页）` : ""}
          <FindingValue label="期望" value={finding.expected} />
          <FindingValue label="实际" value={finding.actual} />
        </span>
      </div>
      <FindingCodexReviewSummary reviews={reviews} />
    </div>
  );
}

function checkUserFacingStatus(check: CheckResult): string {
  const metadataStatus = metadataString(check.metadata, "user_facing_status");
  if (metadataStatus) return metadataStatus;
  if (check.findings.length === 0) return "passed";
  const findingStatuses = check.findings.map((finding) => findingUserFacingStatus(finding));
  const statusPriority: UserFacingFindingStatus[] = ["confirmed_error", "needs_review", "candidate_issue", "refuted"];
  for (const status of statusPriority) {
    if (findingStatuses.includes(status)) return status;
  }
  return "passed";
}

function userFacingCheckLabel(status: string): string {
  if (status === "confirmed_error") return "确认错误";
  if (status === "needs_review") return "需复核";
  if (status === "candidate_issue") return "候选问题";
  if (status === "refuted") return "已反驳";
  return "通过";
}

function userFacingCheckTone(status: string, fallbackSeverity: FindingSeverity): "success" | "danger" | "warn" | "info" {
  if (status === "confirmed_error") return "danger";
  if (status === "needs_review" || status === "candidate_issue") return "warn";
  if (status === "refuted" || status === "passed") return "info";
  return severityTone(fallbackSeverity);
}

function FindingValue({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <span>
      {" "}
      {label}: {formatValue(value)}
    </span>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
