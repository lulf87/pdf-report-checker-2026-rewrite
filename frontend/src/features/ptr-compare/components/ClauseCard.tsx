import { useState } from "react";

import {
  codexFinalStatusLabel,
  codexFinalStatusTone,
  findingCodexFinalStatus,
  groupCodexReviewsByFinding,
} from "../../../entities/codexReview/types";
import type { CodexReviewResult } from "../../../entities/codexReview/types";
import type { Finding } from "../../../entities/finding/types";
import { severityLabel, severityTone } from "../../../entities/finding/types";
import type { PTRClauseViewModel } from "../../../entities/ptr/types";
import type {
  PTRAtomicComparisonRow,
  PTRComparisonItem,
  PTRExternalStandardCoverage,
  PTRReportMatch,
  PTRScopeConsistency,
} from "../../../entities/task/types";
import { checkStatusLabel } from "../../../entities/task/types";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { CodexReviewList, FindingCodexReviewSummary } from "../../codex-review/components/CodexReviewPanel";
import { DiffViewer } from "./DiffViewer";

export interface ClauseCardProps {
  clause: PTRClauseViewModel;
}

export function ClauseCard({ clause }: ClauseCardProps) {
  const [expanded, setExpanded] = useState(false);
  const itemStatus = clause.ptrItem?.coverage_status ?? clause.ptrItem?.user_facing_status;
  const tone = clause.ptrItem && itemStatus ? ptrStatusTone(itemStatus) : severityTone(clause.severity);
  const hasIssue = tone === "danger" || tone === "warn";
  const firstFinding = clause.findings[0];
  const groupedCodexReviews = groupCodexReviewsByFinding(clause.findings, clause.codexReviews);
  const statusLabel = clause.ptrItem
    ? ptrStatusLabel(itemStatus ?? clause.ptrItem.user_facing_status)
    : clause.severity
      ? severityLabel(clause.severity)
      : checkStatusLabel(clause.status);

  return (
    <article className={`clause-card ${tone === "danger" ? "issue-danger" : tone === "warn" ? "issue-warn" : ""}`}>
      <div className="row-head">
        <div>
          <p className="row-title">
            {clause.ptrItem ? `PTR 条款 ${clause.ptrItem.ptr_clause_id}` : clause.checkId}: {clause.title}
          </p>
          <p className="row-summary">{clause.summary || firstFinding?.message || "后端未返回摘要"}</p>
        </div>
        <div className="button-row">
          {clause.codexReviews.length > 0 ? <Badge variant="accent">Codex {clause.codexReviews.length}</Badge> : null}
          <Badge pulse={hasIssue} variant={tone}>
            {statusLabel}
          </Badge>
          <Button onClick={() => setExpanded((value) => !value)} size="sm" variant="ghost">
            {expanded ? "收起" : "展开"}
          </Button>
        </div>
      </div>

      {clause.ptrItem ? <PTRClausePreview item={clause.ptrItem} /> : null}

      {expanded ? (
        <div className="details">
          {clause.ptrItem ? (
            <PTRExplanationDetails
              groupedCodexReviews={groupedCodexReviews}
              item={clause.ptrItem}
              legacyFallback={firstFinding?.message ?? clause.summary}
              scopeConsistency={clause.scopeConsistency}
              findings={clause.findings}
              reviews={clause.codexReviews}
              diffs={clause.diffs}
            />
          ) : (
            <>
              <DiffViewer diffs={clause.diffs} fallbackText={firstFinding?.message ?? clause.summary} />
              {clause.findings.length > 0 ? (
                <div className="panel-stack">
                  {clause.findings.map((finding) => (
                    <ClauseFindingItem
                      finding={finding}
                      key={finding.id}
                      reviews={groupedCodexReviews.byFindingId[finding.id] ?? []}
                    />
                  ))}
                  <CodexReviewList reviews={groupedCodexReviews.unassociated} title="其他 Codex 审核意见" />
                </div>
              ) : clause.codexReviews.length > 0 ? (
                <CodexReviewList reviews={clause.codexReviews} title="Codex 审核意见" />
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </article>
  );
}

function PTRClausePreview({ item }: { item: PTRComparisonItem }) {
  const primaryMatch = item.report_matches[0];
  const externalCoverages = externalCoverageList(item);
  return (
    <div className="comparison-source-list">
      <span className="comparison-source">PTR 摘录 · {truncate(item.ptr_requirement_text, 42)}</span>
      {externalCoverages.length > 0 ? (
        externalCoverages.map((coverage, index) => (
          <span className="comparison-source" key={`${coverage.standard ?? "standard"}-${index}`}>
            外部标准覆盖 · {coverage.standard || "未命名标准"}
            {coverage.start_item_no && coverage.end_item_no ? ` · 序号 ${coverage.start_item_no}～${coverage.end_item_no}` : ""}
          </span>
        ))
      ) : primaryMatch ? (
        <span className="comparison-source">
          报告匹配 · 序号 {primaryMatch.item_no || "未编号"}
          {reportPageText(primaryMatch) ? ` · ${reportPageText(primaryMatch)}` : ""}
          {primaryMatch.test_result ? ` · ${primaryMatch.test_result}` : ""}
        </span>
      ) : (
        <span className="comparison-source">报告匹配 · 未找到对应检验项</span>
      )}
      {item.atomic_comparison_rows?.length ? (
        <span className="comparison-source">参数级比对 · {item.atomic_comparison_rows.length} 项</span>
      ) : null}
      <span className="comparison-source">最终状态 · {ptrStatusLabel(item.coverage_status ?? item.user_facing_status)}</span>
    </div>
  );
}

function PTRExplanationDetails({
  item,
  findings,
  reviews,
  groupedCodexReviews,
  diffs,
  legacyFallback,
  scopeConsistency,
}: {
  item: PTRComparisonItem;
  findings: Finding[];
  reviews: CodexReviewResult[];
  groupedCodexReviews: ReturnType<typeof groupCodexReviewsByFinding>;
  diffs: PTRClauseViewModel["diffs"];
  legacyFallback?: string | null;
  scopeConsistency?: PTRScopeConsistency | null;
}) {
  const comparison = item.normalized_comparison;
  const reportRows = item.report_matches.length > 0 ? item.report_matches : (item.candidate_report_items ?? []);
  const externalCoverages = externalCoverageList(item);
  const displayStatus = item.coverage_status ?? item.user_facing_status;

  return (
    <div className="panel-stack">
      <div className="explanation-summary-grid">
        <section>
          <p className="detail-kicker">PTR 摘录</p>
          <p>
            {item.ptr_requirement_text || "无"}
            {item.ptr_page ? `（PTR 第 ${item.ptr_page} 页）` : ""}
          </p>
        </section>
        <section>
          <p className="detail-kicker">报告首页范围声明</p>
          {scopeConsistency ? (
            <>
              <p>
                {scopeConsistency.source_text || scopeConsistency.declared_scope?.join("、") || "未返回范围声明"}
                {scopeConsistency.source_page ? `（第 ${scopeConsistency.source_page} 页）` : ""}
              </p>
              {scopeConsistency.excluded_topics?.length ? <p>排除：{scopeConsistency.excluded_topics.join("、")}</p> : null}
            </>
          ) : (
            <p>未返回范围声明。</p>
          )}
        </section>
        <section>
          <p className="detail-kicker">报告实际检验表摘录</p>
          {reportRows.length > 0 ? (
            <>
              {reportRows.map((match, index) => <ReportMatchLine key={`${match.item_no ?? "candidate"}-${index}`} match={match} />)}
              {externalCoverages.map((coverage, index) => (
                <ExternalCoverageLine coverage={coverage} key={`${coverage.standard ?? "standard"}-${index}`} />
              ))}
            </>
          ) : externalCoverages.length > 0 ? (
            externalCoverages.map((coverage, index) => (
              <ExternalCoverageLine coverage={coverage} key={`${coverage.standard ?? "standard"}-${index}`} />
            ))
          ) : (
            <p>未找到报告匹配项。</p>
          )}
        </section>
        <section>
          <p className="detail-kicker">比对明细</p>
          <p>
            {formatComparisonLine(
              comparison.expected,
              comparison.actual,
              comparison.operator,
              comparison.unit,
              comparison.requirement_type,
              comparison.status,
            )}
          </p>
          <p>
            {comparison.requirement_type} · {comparison.status}
          </p>
        </section>
        <section>
          <p className="detail-kicker">最终复审结果 / 技术详情</p>
          <p>
            <Badge variant={ptrStatusTone(displayStatus)}>{ptrStatusLabel(displayStatus)}</Badge>
          </p>
          <p>{item.reason}</p>
          {item.next_action ? <p>{item.next_action}</p> : null}
        </section>
      </div>

      {item.atomic_comparison_rows?.length ? <PTRAtomicComparisonTable rows={item.atomic_comparison_rows} /> : null}
      {diffs.length > 0 ? <DiffViewer diffs={diffs} fallbackText={legacyFallback} /> : null}
      <PTRTechnicalDetails findings={findings} groupedCodexReviews={groupedCodexReviews} reviews={reviews} />
    </div>
  );
}

function PTRAtomicComparisonTable({ rows }: { rows: PTRAtomicComparisonRow[] }) {
  const title = atomicComparisonTitle(rows);

  return (
    <section className="comparison-details" aria-label="参数级比对表">
      <div className="comparison-details-head">
        <div>
          <p className="detail-kicker">参数级比对表</p>
          <p className="comparison-title">{title}</p>
        </div>
      </div>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>参数</th>
              <th>预设</th>
              <th>PTR 要求</th>
              <th>报告结果</th>
              <th>来源</th>
              <th>状态</th>
              <th>说明</th>
              <th>页码/序号</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className={`comparison-row comparison-row-${ptrAtomicStatusTone(row.status)}`} key={row.atomic_id}>
                <td>{row.label}</td>
                <td>{row.preset || "不适用"}</td>
                <td>{row.expected || "无"}</td>
                <td>{formatAtomicActual(row)}</td>
                <td>{ptrAtomicSourceLabel(row.source)}</td>
                <td>
                  <Badge variant={ptrAtomicStatusTone(row.status)}>{ptrAtomicStatusLabel(row.status)}</Badge>
                </td>
                <td>{row.reason || row.table_key || "无"}</td>
                <td>
                  {row.report_page ? `第 ${row.report_page} 页` : ""}
                  {row.report_item_no ? `${row.report_page ? " / " : ""}序号 ${row.report_item_no}` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function atomicComparisonTitle(rows: PTRAtomicComparisonRow[]): string {
  const tableKeys = Array.from(new Set(rows.map((row) => row.table_key).filter(Boolean)));
  if (tableKeys.length !== 1) return "Atomic requirements";
  const match = /^.+:表([^:]+):(.+)$/.exec(tableKeys[0] ?? "");
  if (!match) return tableKeys[0] ?? "Atomic requirements";
  return `表 ${match[1]} ${match[2]}比对表`;
}

function ReportMatchLine({ match }: { match: PTRReportMatch }) {
  return (
    <p>
      序号 {match.item_no || "未编号"}
      {reportPageText(match) ? ` · ${reportPageText(match)}` : ""}
      {match.standard_clause ? ` · 标准条款 ${match.standard_clause}` : ""}
      {match.item_name ? ` · ${match.item_name}` : ""}
      {match.standard_requirement ? ` · ${match.standard_requirement}` : ""}
      {match.test_result ? ` · 结果 ${match.test_result}` : ""}
      {match.single_conclusion ? ` · ${match.single_conclusion}` : ""}
    </p>
  );
}

function ExternalCoverageLine({ coverage }: { coverage: PTRExternalStandardCoverage }) {
  return (
    <p>
      {coverage.standard || "外部标准"}
      {coverage.start_item_no && coverage.end_item_no ? ` · 序号 ${coverage.start_item_no}～${coverage.end_item_no}` : ""}
      {coverage.source_page ? ` · 第 ${coverage.source_page} 页` : ""}
      {typeof coverage.passed_count === "number" ? ` · 符合项 ${coverage.passed_count}` : ""}
      {typeof coverage.review_count === "number" && coverage.review_count > 0 ? ` · 需复核 ${coverage.review_count}` : ""}
    </p>
  );
}

function externalCoverageList(item: PTRComparisonItem): PTRExternalStandardCoverage[] {
  if (item.external_standard_coverages?.length) return item.external_standard_coverages;
  return item.external_standard_coverage ? [item.external_standard_coverage] : [];
}

function reportPage(match: PTRReportMatch): number | null | undefined {
  return match.report_page ?? match.page;
}

function reportPageText(match: PTRReportMatch): string {
  const pages = match.report_pages?.filter((page): page is number => typeof page === "number") ?? [];
  if (pages.length > 1) return `第 ${pages[0]}-${pages[pages.length - 1]} 页`;
  const page = reportPage(match);
  return page ? `第 ${page} 页` : "";
}

function PTRTechnicalDetails({
  findings,
  groupedCodexReviews,
  reviews,
}: {
  findings: Finding[];
  groupedCodexReviews: ReturnType<typeof groupCodexReviewsByFinding>;
  reviews: CodexReviewResult[];
}) {
  if (findings.length === 0 && reviews.length === 0) return null;
  return (
    <details className="technical-details">
      <summary>技术详情</summary>
      <div className="technical-details-body">
        {findings.map((finding) => (
          <ClauseFindingItem
            finding={finding}
            key={finding.id}
            reviews={groupedCodexReviews.byFindingId[finding.id] ?? []}
          />
        ))}
        <CodexReviewList reviews={groupedCodexReviews.unassociated} title="其他 Codex 审核意见" />
      </div>
    </details>
  );
}

function formatAtomicActual(row: PTRAtomicComparisonRow): string {
  const actual = typeof row.actual === "string" ? row.actual.trim() : "";
  if (actual) {
    const unit = row.unit?.trim();
    return unit && !actual.includes(unit) ? `${actual} ${unit}` : actual;
  }
  const candidates = row.candidate_actuals?.filter((value) => value.trim()) ?? [];
  if (candidates.length > 0) return `候选值：${candidates.join("、")}，待绑定确认`;
  if (row.status === "needs_review" || row.status === "candidate_found_needs_mapping") return "未完成结构化抽取";
  if (row.status === "candidate_refuted" || row.status === "refuted_candidate_resolved") return "候选已排除，见说明";
  return "未返回报告结果";
}

function formatComparisonLine(
  expected: unknown,
  actual: unknown,
  operator?: string | null,
  unit?: string | null,
  requirementType?: string | null,
  status?: string | null,
): string {
  const expectedText = formatValue(expected);
  const actualText = formatValue(actual);
  const operatorText = operator ? `；操作符 ${operator}` : "";
  const unitText = unit ? `；单位 ${unit}` : "";
  const fallbackActual = requirementType === "atomic_parameter_comparison" && status === "needs_review" ? "未完成结构化抽取" : "无";
  return `期望 ${expectedText || "无"}；实际 ${actualText || fallbackActual}${operatorText}${unitText}`;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function truncate(value: string, maxLength: number): string {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

function ptrStatusLabel(status: string): string {
  if (status === "covered_passed") return "已覆盖并满足要求";
  if (status === "coverage_only_needs_review") return "仅覆盖，需参数级复核";
  if (status === "excluded_by_scope") return "本次范围排除";
  if (status === "missing_in_report") return "报告中未找到";
  if (status === "value_mismatch") return "结果不一致";
  if (status === "needs_review") return "需人工复核";
  if (status === "candidate_issue") return "规则初筛候选";
  if (status === "refuted") return "候选问题已排除";
  if (status === "confirmed_error") return "复审确认问题";
  if (status === "audit_incomplete") return "复审未完成";
  return status;
}

function ptrStatusTone(status: string): "success" | "danger" | "warn" | "info" | "accent" {
  if (status === "covered_passed" || status === "refuted") return "success";
  if (status === "excluded_by_scope") return "info";
  if (status === "confirmed_error" || status === "audit_incomplete") return "danger";
  if (
    status === "needs_review"
    || status === "coverage_only_needs_review"
    || status === "candidate_issue"
    || status === "missing_in_report"
    || status === "value_mismatch"
  ) return "warn";
  return "info";
}

function ptrAtomicStatusLabel(status: string): string {
  if (status === "match") return "满足";
  if (status === "mismatch") return "不满足";
  if (status === "needs_review") return "需复核";
  if (status === "candidate_found_needs_mapping") return "候选待绑定";
  if (status === "not_applicable") return "不适用";
  if (status === "candidate_refuted" || status === "refuted_candidate_resolved") return "候选已排除";
  return status;
}

function ptrAtomicStatusTone(status: string): "success" | "danger" | "warn" | "info" {
  if (status === "match") return "success";
  if (status === "candidate_refuted" || status === "refuted_candidate_resolved") return "success";
  if (status === "mismatch") return "danger";
  if (status === "needs_review" || status === "candidate_found_needs_mapping") return "warn";
  return "info";
}

function ptrAtomicSourceLabel(source: string): string {
  if (source === "codex_review") return "Codex 复审回填";
  if (source === "ptr_table") return "规则结构化抽取";
  if (source === "ptr_text") return "规则结构化抽取";
  return source || "未标注";
}

function ClauseFindingItem({ finding, reviews }: { finding: Finding; reviews: CodexReviewResult[] }) {
  const finalStatus = findingCodexFinalStatus(finding, reviews);

  return (
    <div className="evidence-text">
      <div className="button-row">
        <Badge variant={codexFinalStatusTone(finalStatus)}>{codexFinalStatusLabel(finalStatus)}</Badge>
        <span>
          <strong>{finding.code}</strong>: {finding.message}
          {finding.location?.page_number ? `（第 ${finding.location.page_number} 页）` : ""}
        </span>
      </div>
      <FindingCodexReviewSummary reviews={reviews} />
    </div>
  );
}
