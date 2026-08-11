import { useMemo, useState } from "react";

import {
  findingCodexFinalStatus,
  normalizeCodexReviews,
} from "../../../entities/codexReview/types";
import {
  findingUserFacingStatus,
  findingUserFacingStatusLabel,
  findingUserFacingStatusTone,
} from "../../../entities/finding/types";
import type { Finding } from "../../../entities/finding/types";
import { REPORT_RULE_GROUPS } from "../../../entities/report/types";
import type { ReportSeverityFilter } from "../../../entities/report/types";
import type {
  CheckResult,
  ComparisonDetails,
  ComparisonExtract,
  ComparisonField,
  ExplanationComparisonRow,
  ExplanationDetails,
  ExplanationEvidenceGroup,
  TaskResult,
  TaskStatus,
} from "../../../entities/task/types";
import { AnimatedCounter } from "../../../shared/ui/AnimatedCounter";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { ExportButtonGroup } from "../../../shared/ui/ExportButton";
import { GlassCard } from "../../../shared/ui/GlassCard";
import {
  buildCheckFinalView,
  buildTaskFinalView,
  finalStatusPriority,
} from "../model/finalView";
import type { CheckFinalView } from "../model/finalView";

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
  const resultBadge = buildTaskFinalView(result);
  const checkIds = useMemo(() => result.check_results.map((item) => item.check_id), [result.check_results]);
  const filteredChecks = result.check_results.filter((check) => {
    const severity = finalSeverity(check);
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
          <h1>{resultBadge.label}</h1>
          <p className="muted">{resultBadge.summary}</p>
          <p className="muted">任务 ID: {task.task_id}</p>
        </div>
        <Badge variant={resultBadge.tone}>{resultBadge.label}</Badge>
      </header>

      <div className="metric-grid">
        <Metric label="确认错误" value={result.summary.confirmed_errors_count} tone="danger" />
        <Metric label="人工复核" value={result.summary.manual_review_required_count} tone="warn" />
        <Metric label="通过规则" value={result.check_results.filter((check) => isFinalPass(check)).length} />
      </div>

      <AuditScopeNotice metadata={result.metadata} />

      <GlassCard className="result-card">
        <div className="row-head">
          <div className="filter-row" role="group" aria-label="报告自检筛选">
            <select
              aria-label="按严重级别筛选"
              onChange={(event) => setSeverityFilter(event.target.value as ReportSeverityFilter)}
              value={severityFilter}
            >
              <option value="all">全部级别</option>
              <option value="error">确认问题</option>
              <option value="warn">需人工复核</option>
              <option value="info">通过</option>
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

function finalSeverity(check: CheckResult): ReportSeverityFilter {
  const status = buildCheckFinalView(check).final_status;
  if (status === "confirmed_error") return "error";
  if (status === "needs_manual_review" || status === "candidate_only" || status === "audit_incomplete") return "warn";
  return "info";
}

function isFinalPass(check: CheckResult): boolean {
  const status = buildCheckFinalView(check).final_status;
  return status === "passed" || status === "passed_after_review";
}

function finalVisibleFindings(check: CheckResult): Finding[] {
  const reviews = normalizeCodexReviews(check.codex_reviews);
  return check.findings.filter((finding) => {
    const relatedReviews = reviews.filter((review) => review.target.finding_id === finding.id);
    const finalStatus = findingCodexFinalStatus(finding, relatedReviews);
    const userStatus = findingUserFacingStatus(finding, finalStatus);
    return userStatus !== "refuted" && userStatus !== "passed";
  });
}

function AuditScopeNotice({ metadata }: { metadata: Record<string, unknown> }) {
  const auditMetadata = metadataRecord(metadata, "codex_audit");
  const auditScope = metadataString(auditMetadata, "audit_scope");
  const includedCheckIds = metadataArray(auditMetadata, "included_check_ids");

  if (auditScope !== "targeted") return null;

  return (
    <GlassCard className="result-card">
      <div className="row-head">
        <div>
          <p className="row-title">限定范围核对</p>
          <p className="muted">
            本次只覆盖 {includedCheckIds.length > 0 ? includedCheckIds.join(", ") : "配置筛选范围"}，未纳入范围的规则不计入最终结论。
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
  const sortedChecks = [...checks].sort((left, right) => {
    const leftView = buildCheckFinalView(left);
    const rightView = buildCheckFinalView(right);
    const priorityDiff = finalStatusPriority(leftView.final_status) - finalStatusPriority(rightView.final_status);
    return priorityDiff || left.check_id.localeCompare(right.check_id);
  });

  return (
    <GlassCard className="results-card">
      <h2>{title}</h2>
      <p className="muted">{description}</p>
      <div className="check-list">
        {sortedChecks.map((check) => (
          <CheckRow check={check} key={check.check_id} />
        ))}
      </div>
    </GlassCard>
  );
}

function CheckRow({ check }: { check: CheckResult }) {
  const [expanded, setExpanded] = useState(false);
  const finalFindings = finalVisibleFindings(check);
  const finalComparisonDetails = check.metadata.final_comparison_details;
  const explanationDetails = finalComparisonDetails ? undefined : check.metadata.explanation_details;
  const comparisonDetails = finalComparisonDetails ?? check.metadata.comparison_details;
  const finalView = buildCheckFinalView(check);

  return (
    <article className={`check-row ${finalView.primary_tone === "danger" ? "issue-danger" : finalView.primary_tone === "warn" ? "issue-warn" : ""}`}>
      <div className="row-head">
        <div>
          <p className="row-title">
            {check.check_id}: {check.check_name}
          </p>
          <p className="row-summary">{finalView.final_summary}</p>
        </div>
        <div className="button-row">
          {finalView.confirmed_errors_count > 0 ? <Badge variant="danger">确认问题 {finalView.confirmed_errors_count}</Badge> : null}
          {finalView.manual_review_required_count > 0 ? <Badge variant="warn">待复核 {finalView.manual_review_required_count}</Badge> : null}
          <Badge pulse={finalView.primary_tone === "danger" || finalView.primary_tone === "warn"} variant={finalView.primary_tone}>
            {finalView.final_label}
          </Badge>
          <Button onClick={() => setExpanded((value) => !value)} size="sm" variant="ghost">
            {expanded ? "收起" : "展开"}
          </Button>
        </div>
      </div>
      {expanded ? (
        <div className="details">
          <FinalResultPanel finalView={finalView} />
          {finalFindings.length > 0 ? <FindingList findings={finalFindings} /> : null}
          {comparisonDetails ? <ComparisonDetailsPanel details={comparisonDetails} /> : null}
          {!comparisonDetails && explanationDetails ? (
            <ExplanationDetailsPanel details={explanationDetails} finalView={finalView} />
          ) : null}
          {!explanationDetails && !comparisonDetails ? <p className="muted">后端未返回核对明细。</p> : null}
        </div>
      ) : null}
    </article>
  );
}

function FinalResultPanel({ finalView }: { finalView: CheckFinalView }) {
  return (
    <section className="final-review-panel" aria-label="最终核对结果">
      <div className="row-head">
        <div>
          <p className="codex-review-list-title">最终核对结果</p>
          <p className="final-review-title">{finalView.final_label}</p>
          <p className="final-review-summary">{finalView.final_summary}</p>
        </div>
        <Badge variant={finalView.primary_tone}>{finalView.final_label}</Badge>
      </div>
      <div className="final-review-stats">
        <FinalStat label="确认问题" value={finalView.confirmed_errors_count} tone={finalView.confirmed_errors_count > 0 ? "danger" : "info"} />
        <FinalStat label="仍需人工复核" value={finalView.manual_review_required_count} tone={finalView.manual_review_required_count > 0 ? "warn" : "info"} />
      </div>
    </section>
  );
}

function FinalStat({ label, value, tone }: { label: string; value: number; tone: "danger" | "warn" | "info" }) {
  return (
    <div className={`final-review-stat final-review-stat-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ExplanationDetailsPanel({ details, finalView }: { details: ExplanationDetails; finalView: CheckFinalView }) {
  const rows = details.comparison_rows ?? [];
  const sources = details.source_sections ?? [];
  const groups = details.evidence_groups ?? [];
  const decision = details.decision;

  return (
    <section className="comparison-details explanation-details" aria-label="核对明细">
      <div className="comparison-details-head">
        <div>
          <p className="codex-review-list-title">核对依据 / 摘录明细</p>
          <p className="comparison-title">核对明细</p>
          {finalView.final_status === "passed_after_review" ? (
            <p className="comparison-reason">本项核对通过，未发现最终问题。</p>
          ) : null}
        </div>
        {decision ? <Badge variant={comparisonStatusTone(decision.user_facing_status)}>{decision.label || userFacingCheckLabel(decision.user_facing_status)}</Badge> : null}
      </div>

      <div className="explanation-summary-grid">
        {details.check_goal ? (
          <div>
            <p className="detail-kicker">检查目的</p>
            <p>{details.check_goal}</p>
          </div>
        ) : null}
        {details.user_question ? (
          <div>
            <p className="detail-kicker">用户问题</p>
            <p>{details.user_question}</p>
          </div>
        ) : null}
        {details.overall_reason ? (
          <div>
            <p className="detail-kicker">判断理由</p>
            <p>{details.overall_reason}</p>
          </div>
        ) : null}
        {details.next_action ? (
          <div>
            <p className="detail-kicker">下一步建议</p>
            <p>{details.next_action}</p>
          </div>
        ) : null}
      </div>

      {sources.length > 0 ? (
        <div>
          <p className="codex-review-list-title">摘录来源</p>
          <div className="comparison-source-list">
            {sources.map((source) => (
              <span className="comparison-source" key={`${source.label}-${source.page_number ?? source.display_page_label ?? source.description}`}>
                {source.label}
                {source.display_page_label || source.page_number ? ` · ${source.display_page_label || `PDF 第 ${source.page_number} 页`}` : ""}
                {source.description ? ` · ${source.description}` : ""}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {rows.length > 0 ? (
        <div>
          <p className="codex-review-list-title">比对明细</p>
          <div className="comparison-table-wrap">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>字段</th>
                  <th>左侧摘录</th>
                  <th>右侧摘录</th>
                  <th>状态</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <ExplanationRow row={row} key={`${row.field}-${index}`} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {groups.length > 0 ? (
        <div>
          <p className="codex-review-list-title">证据链</p>
          <div className="explanation-evidence-groups">
            {groups.map((group) => (
              <ExplanationEvidenceGroupCard group={group} key={group.title} />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ExplanationRow({ row }: { row: ExplanationComparisonRow }) {
  return (
    <tr className={`comparison-row comparison-row-${comparisonStatusTone(row.status)}`}>
      <td>{row.field}</td>
      <td>{formatLabeledValue(row.left_label, row.left_value)}</td>
      <td>{formatLabeledValue(row.right_label, row.right_value)}</td>
      <td>
        <Badge variant={comparisonStatusTone(row.status)}>{comparisonStatusLabel(row.status)}</Badge>
      </td>
      <td>{row.reason || "无"}</td>
    </tr>
  );
}

function ExplanationEvidenceGroupCard({ group }: { group: ExplanationEvidenceGroup }) {
  const items = group.items ?? [];
  return (
    <div className="explanation-evidence-group">
      <p className="comparison-title">{group.title}</p>
      {items.length > 0 ? (
        <div className="explanation-evidence-list">
          {items.map((item, index) => (
            <span className="comparison-source" key={`${item.label}-${index}`}>
              {item.label}
              {item.display_page_label || item.page_number ? ` · ${item.display_page_label || `PDF 第 ${item.page_number} 页`}` : ""}
              {item.evidence_type ? ` · ${item.evidence_type}` : ""}
              {item.status ? ` · ${item.status}` : ""}
            </span>
          ))}
        </div>
      ) : (
        <p className="muted">暂无结构化证据项。</p>
      )}
    </div>
  );
}

function ComparisonDetailsPanel({ details }: { details: ComparisonDetails }) {
  const fields = details.fields ?? [];
  const sources = details.sources ?? [];

  return (
    <section className="comparison-details" aria-label="核对明细">
      <div className="comparison-details-head">
        <div>
          <p className="codex-review-list-title">核对依据</p>
          <p className="comparison-title">{details.title}</p>
        </div>
        <Badge variant={comparisonStatusTone(details.overall_status)}>{comparisonStatusLabel(details.overall_status)}</Badge>
      </div>
      {sources.length > 0 ? (
        <div className="comparison-source-list">
          {sources.map((source) => (
            <span className="comparison-source" key={`${source.source_key}-${source.page_number ?? source.display_page_label ?? source.label}`}>
              {source.label}
              {source.display_page_label || source.page_number ? ` · ${source.display_page_label || `PDF 第 ${source.page_number} 页`}` : ""}
              {source.section ? ` · ${source.section}` : ""}
            </span>
          ))}
        </div>
      ) : null}
      {details.overall_reason ? (
        <p className="comparison-reason">
          <strong>通过原因</strong>
          {details.overall_reason}
        </p>
      ) : null}
      {fields.length > 0 ? (
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>字段</th>
                <th>来源 A 摘录</th>
                <th>来源 B 摘录</th>
                <th>比对结果</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, index) => (
                <ComparisonFieldRow
                  field={field}
                  key={`${field.field_key}-${field.field_label}-${field.right?.page_number ?? "no-page"}-${index}`}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">暂无字段级核对明细。</p>
      )}
    </section>
  );
}

function ComparisonFieldRow({ field }: { field: ComparisonField }) {
  return (
    <tr className={`comparison-row comparison-row-${comparisonStatusTone(field.status)}`}>
      <td>{field.field_label}</td>
      <td>{formatComparisonExtract(field.left)}</td>
      <td>{formatComparisonExtract(field.right)}</td>
      <td>
        <Badge variant={comparisonStatusTone(field.status)}>{comparisonStatusLabel(field.status)}</Badge>
      </td>
      <td>{field.reason || "无"}</td>
    </tr>
  );
}

function formatComparisonExtract(extract?: ComparisonExtract | null): string {
  if (!extract) return "无";
  const source = extract.label || extract.source_key || "";
  const page = extract.display_page_label || (extract.page_number ? `PDF 第 ${extract.page_number} 页` : "");
  const text = extract.raw_text || extract.normalized_text || "";
  return [source, page, text].filter(Boolean).join(" · ") || "无";
}

function comparisonStatusLabel(status: string): string {
  if (status === "match") return "一致";
  if (status === "mismatch") return "不一致";
  if (status === "missing") return "缺失";
  if (status === "passed") return "通过";
  if (status === "refuted") return "通过";
  if (status === "candidate_issue") return "待核对";
  if (status === "confirmed_error") return "确认问题";
  if (status === "manual_review_required") return "仍需人工复核";
  if (status === "audit_failed") return "自动核对未完成";
  if (status === "missing_left") return "来源 A 缺失";
  if (status === "missing_right") return "来源 B 缺失";
  if (status === "needs_review") return "需复核";
  if (status === "not_applicable") return "不适用";
  if (status === "skipped") return "已跳过";
  return status;
}

function comparisonStatusTone(status: string): "success" | "danger" | "warn" | "info" {
  if (status === "match" || status === "passed" || status === "refuted") return "success";
  if (status === "mismatch" || status === "missing" || status === "missing_left" || status === "missing_right" || status === "confirmed_error" || status === "audit_failed") return "danger";
  if (status === "needs_review" || status === "manual_review_required" || status === "candidate_issue") return "warn";
  return "info";
}

function FindingList({ findings }: { findings: Finding[] }) {
  return (
    <div className="panel-stack">
      {findings.map((finding) => (
        <FindingItem finding={finding} key={finding.id} />
      ))}
    </div>
  );
}

function FindingItem({ finding }: { finding: Finding }) {
  const finalStatus = findingCodexFinalStatus(finding, []);
  const userStatus = findingUserFacingStatus(finding, finalStatus);

  return (
    <div className="evidence-text">
      <div className="button-row">
        <Badge variant={findingUserFacingStatusTone(userStatus)}>
          {findingUserFacingStatusLabel(userStatus, finding)}
        </Badge>
        <span>
          <strong>{finding.code}</strong>: {finding.message}
          {finding.location?.page_number ? `（第 ${finding.location.page_number} 页）` : ""}
          <FindingValue label="期望" value={finding.expected} />
          <FindingValue label="实际" value={finding.actual} />
        </span>
      </div>
    </div>
  );
}

function userFacingCheckLabel(status: string): string {
  if (status === "confirmed_error") return "确认错误";
  if (status === "needs_review") return "需复核";
  if (status === "candidate_issue") return "候选问题";
  if (status === "refuted") return "通过";
  return "通过";
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

function formatLabeledValue(label: string | null | undefined, value: unknown): string {
  const text = value === null || value === undefined || value === "" ? "无" : formatValue(value);
  return [label, text].filter(Boolean).join(" · ");
}
