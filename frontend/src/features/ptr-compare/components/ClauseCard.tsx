import { useState } from "react";

import type { Finding } from "../../../entities/finding/types";
import {
  findingUserFacingStatus,
  findingUserFacingStatusLabel,
  findingUserFacingStatusTone,
  severityLabel,
  severityTone,
} from "../../../entities/finding/types";
import type { PTRClauseViewModel } from "../../../entities/ptr/types";
import type {
  PTRAtomicComparisonRow,
  PTRClauseIdentityAlignment,
  PTRClauseIdentityCandidate,
  PTRComparisonItem,
  PTRCoverageComparisonRow,
  PTREffectiveRequirement,
  PTRExternalStandardCoverage,
  PTRReportRequirementMatch,
  PTRReportMatch,
  PTRScopeConsistency,
  PTRTraceDecision,
  PTRTraceResultComparison,
} from "../../../entities/task/types";
import { checkStatusLabel } from "../../../entities/task/types";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
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
          <Badge pulse={hasIssue} variant={tone}>
            {statusLabel}
          </Badge>
          <Button onClick={() => setExpanded((value) => !value)} size="sm" variant="ghost">
            {expanded ? "收起详情" : "查看比对细节"}
          </Button>
        </div>
      </div>

      {clause.ptrItem ? <PTRClausePreview item={clause.ptrItem} /> : null}

      {expanded ? (
        <div className="details">
          {clause.ptrItem ? (
            <PTRExplanationDetails
              item={clause.ptrItem}
              legacyFallback={firstFinding?.message ?? clause.summary}
              scopeConsistency={clause.scopeConsistency}
              findings={clause.findings}
              diffs={clause.diffs}
            />
          ) : (
            <>
              <DiffViewer diffs={clause.diffs} fallbackText={firstFinding?.message ?? clause.summary} />
              {clause.findings.length > 0 ? (
                <div className="panel-stack">
                  {clause.findings.map((finding) => (
                    <ClauseFindingItem finding={finding} key={finding.id} />
                  ))}
                </div>
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
      {item.result_comparisons?.length ? (
        <span className="comparison-source">结果比对 · {item.result_comparisons.length} 项</span>
      ) : item.atomic_comparison_rows?.length ? (
        <span className="comparison-source">{atomicPreviewSummary(item.atomic_comparison_rows)}</span>
      ) : item.coverage_comparison_rows?.length ? (
        <span className="comparison-source">条款覆盖对比 · {item.coverage_comparison_rows.length} 项</span>
      ) : null}
      {item.clause_identity_alignment ? (
        <span className="comparison-source">
          条款身份 · {clauseIdentityStatusLabel(item.clause_identity_alignment.status)}
        </span>
      ) : null}
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
          {item.report_requirement_matches?.length ? ` · 要求行 ${item.report_requirement_matches.length} 项` : ""}
        </span>
      ) : (
        <span className="comparison-source">报告匹配 · 未找到对应检验项</span>
      )}
      <span className="comparison-source">最终状态 · {ptrStatusLabel(item.coverage_status ?? item.user_facing_status)}</span>
    </div>
  );
}

function PTRExplanationDetails({
  item,
  findings,
  diffs,
  legacyFallback,
  scopeConsistency,
}: {
  item: PTRComparisonItem;
  findings: Finding[];
  diffs: PTRClauseViewModel["diffs"];
  legacyFallback?: string | null;
  scopeConsistency?: PTRScopeConsistency | null;
}) {
  const displayStatus = item.coverage_status ?? item.user_facing_status;
  const hasTrace = Boolean(item.ptr_clause_statement && item.requirement_alignment && item.result_compliance);

  if (!hasTrace) {
    return (
      <LegacyPTRExplanationDetails
        item={item}
        findings={findings}
        diffs={diffs}
        legacyFallback={legacyFallback}
        scopeConsistency={scopeConsistency}
      />
    );
  }

  return (
    <div className="panel-stack">
      <section className="trace-section" aria-label="本条 PTR 正文">
        <p className="detail-kicker">本条 PTR 正文</p>
        <p>{item.ptr_clause_statement?.local_text || item.ptr_requirement_text || "未返回当前条款正文。"}</p>
        {item.ptr_clause_statement?.page ? <p className="trace-meta">PTR 第 {item.ptr_clause_statement.page} 页</p> : null}
      </section>

      <PTRClauseIdentitySection alignment={item.clause_identity_alignment} />
      <PTREffectiveRequirementsTable rows={item.effective_requirements ?? []} />
      <PTRReportRequirementsTable rows={item.report_requirement_matches ?? []} />
      <PTRTraceDecisionSection decision={item.requirement_alignment!} label="要求一致性结论" />
      <PTRResultComparisonTable rows={item.result_comparisons ?? []} />
      <PTRTraceDecisionSection decision={item.result_compliance!} label="结果符合性结论" />

      <section className="trace-section trace-final" aria-label="最终结论">
        <p className="detail-kicker">最终结论</p>
        <p>
          <Badge variant={ptrStatusTone(displayStatus)}>{ptrStatusLabel(displayStatus)}</Badge>
        </p>
        <p>{item.reason}</p>
        {item.next_action ? <p>{item.next_action}</p> : null}
      </section>

      <PTRTechnicalDetails
        diffs={diffs}
        findings={findings}
        item={item}
        legacyFallback={legacyFallback}
        scopeConsistency={scopeConsistency}
      />
    </div>
  );
}

function PTRClauseIdentitySection({
  alignment,
}: {
  alignment?: PTRClauseIdentityAlignment | null;
}) {
  if (!alignment) return null;
  const candidates = alignment.candidates ?? [];
  const selectedIdentityId = alignment.selected_report_identity?.identity_id;
  const showCandidateTable = ["identity_mismatch", "ambiguous", "missing"].includes(alignment.status);
  const visibleCandidates = showCandidateTable
    ? clauseIdentityCandidatesForDisplay(candidates, selectedIdentityId)
    : [];
  const rejectedExactCandidate = candidates.find(
    (candidate) => candidate.number_relation === "exact" && candidate.rejected_reason,
  );
  const reportClauseNumber = alignment.selected_report_clause_number ?? rejectedExactCandidate?.report_clause_number;
  const reportTitle = alignment.selected_report_title ?? rejectedExactCandidate?.report_title;
  const reportItemNo = alignment.selected_report_item_no ?? rejectedExactCandidate?.report_item_no;
  const reportPage = alignment.selected_report_page ?? rejectedExactCandidate?.report_page;

  return (
    <section className="trace-section clause-identity-section" aria-label="条款身份对齐">
      <div className="comparison-details-head">
        <div>
          <p className="detail-kicker">条款身份对齐</p>
          <p className="comparison-title">
            PTR {alignment.ptr_clause_number} · {alignment.ptr_title || "未命名条款"}
          </p>
        </div>
        <Badge variant={clauseIdentityStatusTone(alignment.status)}>
          {clauseIdentityStatusLabel(alignment.status)}
        </Badge>
      </div>

      <div className="comparison-source-list">
        <span className="comparison-source">
          PTR 条款 · {alignment.ptr_clause_number} · {alignment.ptr_title || "未命名条款"}
        </span>
        <span className="comparison-source">
          报告对应条款 · {reportClauseNumber || "未选中"}
          {reportTitle ? ` · ${reportTitle}` : ""}
        </span>
        {reportItemNo ? (
          <span className="comparison-source">报告序号 · {reportItemNo}</span>
        ) : null}
        {reportPage ? (
          <span className="comparison-source">报告页码 · 第 {reportPage} 页</span>
        ) : null}
        <span className="comparison-source">编号 · {alignment.number_matches ? "一致" : "不一致或未确认"}</span>
        <span className="comparison-source">名称 · {alignment.title_matches ? "一致" : "不一致或未确认"}</span>
      </div>
      {alignment.status === "identity_mismatch" && rejectedExactCandidate ? (
        <p className="trace-callout trace-callout-danger">
          同编号但内容不一致：PTR 要求“{alignment.ptr_title || "未命名条款"}”，报告同编号条款为“{rejectedExactCandidate.report_title || "未命名条款"}”，不能使用该报告结果。
        </p>
      ) : null}
      <p>{alignment.reason}</p>

      {visibleCandidates.length ? (
        <>
          <p className="trace-meta">以下候选仅用于定位条款，不代表最终不一致；系统只使用已选中的对应条款参与结果判断。</p>
          <div className="comparison-table-wrap">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>报告编号</th>
                  <th>报告名称</th>
                  <th>序号/页码</th>
                  <th>编号关系</th>
                  <th>名称关系</th>
                  <th>参数关系</th>
                  <th>候选结论</th>
                </tr>
              </thead>
              <tbody>
                {visibleCandidates.map((candidate) => (
                  <tr key={candidate.report_identity_id}>
                    <td>{candidate.report_clause_number || "未标注"}</td>
                    <td>{candidate.report_title || "未命名"}</td>
                    <td>
                      {candidate.report_item_no ? `序号 ${candidate.report_item_no}` : ""}
                      {candidate.report_page ? `${candidate.report_item_no ? " / " : ""}第 ${candidate.report_page} 页` : ""}
                    </td>
                    <td>{clauseIdentityRelationLabel(candidate.number_relation)}</td>
                    <td>{clauseIdentityRelationLabel(candidate.title_relation)}</td>
                    <td>{clauseIdentityRelationLabel(candidate.parameter_relation)}</td>
                    <td>
                      <Badge variant={clauseIdentityCandidateTone(candidate, selectedIdentityId)}>
                        {clauseIdentityCandidateLabel(candidate, selectedIdentityId)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : showCandidateTable ? (
        <p>报告中未形成可核验的子条款候选。</p>
      ) : null}
    </section>
  );
}

function LegacyPTRExplanationDetails({
  item,
  findings,
  diffs,
  legacyFallback,
  scopeConsistency,
}: {
  item: PTRComparisonItem;
  findings: Finding[];
  diffs: PTRClauseViewModel["diffs"];
  legacyFallback?: string | null;
  scopeConsistency?: PTRScopeConsistency | null;
}) {
  return (
    <div className="panel-stack">
      {item.atomic_comparison_rows?.length ? (
        <PTRAtomicComparisonTable rows={item.atomic_comparison_rows} />
      ) : item.coverage_comparison_rows?.length ? (
        <PTRCoverageComparisonTable rows={item.coverage_comparison_rows} />
      ) : null}
      <section className="trace-section">
        <p className="detail-kicker">PTR 摘录</p>
        <p>{item.ptr_requirement_text || "无"}</p>
      </section>
      <PTRTechnicalDetails
        diffs={diffs}
        findings={findings}
        item={item}
        legacyFallback={legacyFallback}
        scopeConsistency={scopeConsistency}
      />
    </div>
  );
}

function PTREffectiveRequirementsTable({ rows }: { rows: PTREffectiveRequirement[] }) {
  return (
    <section className="comparison-details" aria-label="适用 PTR 要求">
      <p className="detail-kicker">适用 PTR 要求</p>
      {rows.length ? (
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>参数/功能</th>
                <th>来源</th>
                <th>适用列/条件</th>
                <th>PTR 要求</th>
                <th>页码</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.requirement_id}>
                  <td>{row.label}</td>
                  <td>{effectiveRequirementSource(row)}</td>
                  <td>{traceContext(row) || "通用"}</td>
                  <td>{row.expected || "未结构化"}</td>
                  <td>{row.source_page ? `第 ${row.source_page} 页` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>未稳定提取本条适用要求。</p>
      )}
    </section>
  );
}

function PTRReportRequirementsTable({ rows }: { rows: PTRReportRequirementMatch[] }) {
  return (
    <section className="comparison-details" aria-label="报告对应标准要求">
      <p className="detail-kicker">报告对应标准要求</p>
      {rows.length ? (
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>报告序号/条款</th>
                <th>参数/功能</th>
                <th>条件</th>
                <th>标准要求</th>
                <th>定位</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`${row.evidence_ref ?? row.report_item_no ?? "row"}-${index}`}>
                  <td>{`${row.report_item_no || "未编号"}${row.report_clause ? ` / ${row.report_clause}` : ""}`}</td>
                  <td>{row.row_label || "未标注"}</td>
                  <td>{traceContext(row) || "通用"}</td>
                  <td>{row.standard_requirement_text}</td>
                  <td>
                    {row.page ? `第 ${row.page} 页` : ""}
                    {row.source_row !== null && row.source_row !== undefined ? `${row.page ? " / " : ""}行 ${row.source_row}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>未定位到本条对应的报告标准要求行。</p>
      )}
    </section>
  );
}

function PTRTraceDecisionSection({ decision, label }: { decision: PTRTraceDecision; label: string }) {
  return (
    <section className="trace-section trace-decision" aria-label={label}>
      <div>
        <p className="detail-kicker">{label}</p>
        <p>{decision.reason}</p>
      </div>
      <Badge variant={traceStatusTone(decision.status)}>{traceStatusLabel(decision.status)}</Badge>
    </section>
  );
}

function PTRResultComparisonTable({ rows }: { rows: PTRTraceResultComparison[] }) {
  return (
    <section className="comparison-details" aria-label="报告结果比对表">
      <p className="detail-kicker">报告结果比对表</p>
      {rows.length ? (
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>参数/功能</th>
                <th>条件</th>
                <th>PTR 要求</th>
                <th>报告实测结果</th>
                <th>状态</th>
                <th>说明</th>
                <th>页码/序号</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr className={`comparison-row comparison-row-${ptrAtomicStatusTone(row.status)}`} key={row.comparison_id}>
                  <td>{row.label}</td>
                  <td>{traceContext(row) || "通用"}</td>
                  <td>{row.expected || "未返回"}</td>
                  <td>{formatTraceActual(row)}</td>
                  <td>
                    <Badge variant={ptrAtomicStatusTone(row.status)}>{ptrAtomicStatusLabel(row.status)}</Badge>
                  </td>
                  <td>{row.reason}</td>
                  <td>
                    {row.page ? `第 ${row.page} 页` : ""}
                    {row.item_no ? `${row.page ? " / " : ""}序号 ${row.item_no}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>未绑定到本条可追溯的报告结果行。</p>
      )}
    </section>
  );
}

function PTRAtomicComparisonTable({ rows }: { rows: PTRAtomicComparisonRow[] }) {
  const title = atomicComparisonTitle(rows);
  const inactiveModelRows = rows.filter((row) => row.model_column && row.status === "not_applicable");
  const primaryRows = rows.filter((row) => !row.model_column || row.status !== "not_applicable");

  return (
    <section className="comparison-details" aria-label="参数级比对表">
      <div className="comparison-details-head">
        <div>
          <p className="detail-kicker">参数级比对表</p>
          <p className="comparison-title">{title}</p>
        </div>
      </div>
      <AtomicRowsTable rows={primaryRows} />
      {inactiveModelRows.length > 0 ? (
        <details className="inactive-model-details">
          <summary>查看其他不适用型号（{inactiveModelRows.length} 项）</summary>
          <AtomicRowsTable rows={inactiveModelRows} />
        </details>
      ) : null}
    </section>
  );
}

function AtomicRowsTable({ rows }: { rows: PTRAtomicComparisonRow[] }) {
  return (
    <div className="comparison-table-wrap">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>参数</th>
            <th>条件/预设</th>
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
              <td>{row.model_column || row.condition || row.preset || "不适用"}</td>
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
  );
}

function PTRCoverageComparisonTable({ rows }: { rows: PTRCoverageComparisonRow[] }) {
  return (
    <section className="comparison-details" aria-label="条款覆盖对比表">
      <div className="comparison-details-head">
        <div>
          <p className="detail-kicker">条款覆盖对比表</p>
          <p className="comparison-title">PTR 条款与报告检验项目对应关系</p>
        </div>
      </div>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>PTR 条款</th>
              <th>PTR 要求</th>
              <th>报告序号</th>
              <th>报告条款</th>
              <th>报告结果</th>
              <th>单项结论</th>
              <th>状态</th>
              <th>说明</th>
              <th>页码</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr className={`comparison-row comparison-row-${ptrStatusTone(row.status)}`} key={`${row.ptr_clause_id}-${row.report_item_no ?? index}`}>
                <td>
                  {row.ptr_clause_id}
                  {row.ptr_title ? ` · ${row.ptr_title}` : ""}
                </td>
                <td>{row.ptr_requirement || "未返回 PTR 摘录"}</td>
                <td>{row.report_item_no || "未编号"}</td>
                <td>
                  {row.report_standard_clause || "未标注"}
                  {row.report_requirement_excerpt ? ` · ${row.report_requirement_excerpt}` : ""}
                </td>
                <td>{row.report_result || "未返回报告结果"}</td>
                <td>{row.report_conclusion || "未返回结论"}</td>
                <td>
                  <Badge variant={ptrStatusTone(row.status)}>{ptrStatusLabel(row.status)}</Badge>
                </td>
                <td>{row.reason || "报告检验项目覆盖该 PTR 要求。"}</td>
                <td>{row.report_page ? `第 ${row.report_page} 页` : ""}</td>
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

function atomicPreviewSummary(rows: PTRAtomicComparisonRow[]): string {
  const matchCount = rows.filter((row) => row.status === "match").length;
  const notApplicableCount = rows.filter((row) => row.status === "not_applicable").length;
  const mismatchCount = rows.filter((row) => row.status === "mismatch").length;
  const reviewCount = rows.filter((row) => row.status === "needs_review" || row.status === "candidate_found_needs_mapping").length;
  if (mismatchCount > 0) return `参数级比对 ${rows.length} 项，${mismatchCount} 项不满足`;
  if (reviewCount > 0) return `参数级比对 ${rows.length} 项，${reviewCount} 项需复核`;
  if (matchCount + notApplicableCount === rows.length) return `参数级比对 ${rows.length} 项，全部满足`;
  return `参数级比对 ${rows.length} 项`;
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
  item,
  findings,
  diffs,
  legacyFallback,
  scopeConsistency,
}: {
  item: PTRComparisonItem;
  findings: Finding[];
  diffs: PTRClauseViewModel["diffs"];
  legacyFallback?: string | null;
  scopeConsistency?: PTRScopeConsistency | null;
}) {
  const technical = item.technical_evidence;
  const hasTechnicalEvidence = Boolean(
    technical?.ptr_full_text
    || technical?.ptr_tables?.length
    || technical?.report_groups?.length
    || item.atomic_comparison_rows?.length
    || item.coverage_comparison_rows?.length
    || item.report_matches.length,
  );
  if (!hasTechnicalEvidence && findings.length === 0 && diffs.length === 0) return null;
  return (
    <details className="technical-details">
      <summary>技术详情</summary>
      <div className="technical-details-body">
        {scopeConsistency ? (
          <section>
            <p className="detail-kicker">报告首页范围声明</p>
            <p>{scopeConsistency.source_text || scopeConsistency.declared_scope?.join("、") || "未返回范围声明"}</p>
          </section>
        ) : null}
        {technical?.ptr_full_text ? (
          <section>
            <p className="detail-kicker">完整 PTR 条款与附表证据</p>
            <pre className="technical-evidence-text">{technical.ptr_full_text}</pre>
          </section>
        ) : null}
        {technical?.ptr_tables?.length ? (
          <section>
            <p className="detail-kicker">完整 PTR 表格结构</p>
            <pre className="technical-evidence-text">{JSON.stringify(technical.ptr_tables, null, 2)}</pre>
          </section>
        ) : null}
        {technical?.report_groups?.length ? (
          <section>
            <p className="detail-kicker">完整报告检验组</p>
            <pre className="technical-evidence-text">{JSON.stringify(technical.report_groups, null, 2)}</pre>
          </section>
        ) : null}
        {item.report_matches.length ? (
          <section>
            <p className="detail-kicker">报告原始匹配项</p>
            {item.report_matches.map((match, index) => (
              <ReportMatchLine key={`${match.item_no ?? "match"}-${index}`} match={match} />
            ))}
          </section>
        ) : null}
        {item.atomic_comparison_rows?.length ? <PTRAtomicComparisonTable rows={item.atomic_comparison_rows} /> : null}
        {item.coverage_comparison_rows?.length ? <PTRCoverageComparisonTable rows={item.coverage_comparison_rows} /> : null}
        {diffs.length > 0 ? <DiffViewer diffs={diffs} fallbackText={legacyFallback} /> : null}
        {findings.map((finding) => (
          <ClauseFindingItem finding={finding} key={finding.id} />
        ))}
      </div>
    </details>
  );
}

function effectiveRequirementSource(row: PTREffectiveRequirement): string {
  if (!row.table_number) return "当前条款正文";
  const table = `表 ${row.table_number}${row.table_title ? ` ${row.table_title}` : ""}`;
  return `${row.parent_clause ? `父级 ${row.parent_clause} / ` : ""}${table}${row.table_row_label ? ` / ${row.table_row_label}` : ""}`;
}

function traceContext(row: {
  model?: string | null;
  preset?: string | null;
  condition?: string | null;
  load?: string | null;
  selected_column?: string | null;
}): string {
  return Array.from(
    new Set([row.model, row.preset, row.condition, row.load, row.selected_column].filter((value): value is string => Boolean(value))),
  ).join(" / ");
}

function traceStatusLabel(status: string): string {
  if (status === "equivalent") return "要求一致";
  if (status === "match") return "结果满足";
  if (status === "mismatch") return "不一致";
  if (status === "needs_review") return "需人工复核";
  if (status === "needs_policy_review") return "标准版本政策待确认";
  if (status === "not_applicable") return "不适用";
  return status;
}

function traceStatusTone(status: string): "success" | "danger" | "warn" | "info" {
  if (status === "equivalent" || status === "match") return "success";
  if (status === "mismatch") return "danger";
  if (status === "needs_review" || status === "needs_policy_review") return "warn";
  return "info";
}

function clauseIdentityStatusLabel(status: string): string {
  if (status === "exact_match") return "完全对应";
  if (status === "semantic_match_number_mismatch") return "内容对应但编号不一致";
  if (status === "identity_mismatch") return "同编号但内容不一致";
  if (status === "ambiguous") return "候选不唯一";
  if (status === "missing") return "报告中未找到";
  if (status === "not_applicable") return "由其他结构化证据验证";
  return status;
}

function clauseIdentityStatusTone(status: string): "success" | "danger" | "warn" | "info" {
  if (status === "exact_match") return "success";
  if (status === "identity_mismatch") return "danger";
  if (status === "semantic_match_number_mismatch" || status === "ambiguous" || status === "missing") return "warn";
  return "info";
}

function clauseIdentityRelationLabel(relation: string): string {
  if (relation === "exact") return "一致";
  if (relation === "alias") return "同义";
  if (relation === "similar") return "相似";
  if (relation === "conflict") return "冲突";
  if (relation === "different") return "不同";
  if (relation === "parent_only") return "仅父级";
  if (relation === "same") return "同父级";
  if (relation === "missing") return "未标注";
  return relation;
}

function clauseIdentityCandidateLabel(
  candidate: PTRClauseIdentityCandidate,
  selectedIdentityId?: string,
): string {
  if (candidate.report_identity_id === selectedIdentityId) {
    return candidate.number_relation === "exact" ? "已选中" : "已选中：内容对应但编号不同";
  }
  if (candidate.rejected_reason === "exact_number_semantic_conflict") return "已排除：同编号但内容不同";
  if (candidate.rejected_reason) return "已排除";
  return "备选";
}

function clauseIdentityCandidateTone(
  candidate: PTRClauseIdentityCandidate,
  selectedIdentityId?: string,
): "success" | "danger" | "warn" | "info" {
  if (candidate.report_identity_id === selectedIdentityId) return "success";
  if (candidate.rejected_reason) return "danger";
  return "info";
}

function clauseIdentityCandidatesForDisplay(
  candidates: PTRClauseIdentityCandidate[],
  selectedIdentityId?: string,
): PTRClauseIdentityCandidate[] {
  const prioritized = [
    ...candidates.filter((candidate) => candidate.report_identity_id === selectedIdentityId),
    ...candidates.filter(
      (candidate) => candidate.report_identity_id !== selectedIdentityId
        && candidate.number_relation === "exact"
        && Boolean(candidate.rejected_reason),
    ),
    ...[...candidates]
      .filter(
        (candidate) => candidate.report_identity_id !== selectedIdentityId
          && !(candidate.number_relation === "exact" && candidate.rejected_reason),
      )
      .sort((left, right) => right.score - left.score),
  ];
  const result: PTRClauseIdentityCandidate[] = [];
  const seenClauseNumbers = new Set<string>();
  for (const candidate of prioritized) {
    const key = candidate.report_clause_number || candidate.report_identity_id;
    if (seenClauseNumbers.has(key)) continue;
    seenClauseNumbers.add(key);
    result.push(candidate);
    if (result.length >= 4) break;
  }
  return result;
}

function formatTraceActual(row: PTRTraceResultComparison): string {
  const actual = row.actual?.trim();
  if (!actual) return "未返回报告实测结果";
  return row.unit && !actual.includes(row.unit) ? `${actual} ${row.unit}` : actual;
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
  if (row.status === "candidate_refuted" || row.status === "refuted_candidate_resolved") return "满足";
  return "未返回报告结果";
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
  if (status === "needs_policy_review") return "标准版本政策待确认";
  if (status === "candidate_issue") return "需人工复核";
  if (status === "refuted") return "满足";
  if (status === "confirmed_error") return "确认问题";
  if (status === "confirmed_document_issue") return "条款编号偏移";
  if (status === "confirmed_issue") return "确认条款差异";
  if (status === "audit_incomplete") return "自动核对未完成";
  return status;
}

function ptrStatusTone(status: string): "success" | "danger" | "warn" | "info" | "accent" {
  if (status === "covered_passed" || status === "refuted") return "success";
  if (status === "excluded_by_scope") return "info";
  if (status === "confirmed_error" || status === "confirmed_issue" || status === "audit_incomplete") return "danger";
  if (status === "confirmed_document_issue") return "warn";
  if (
    status === "needs_review"
    || status === "needs_policy_review"
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
  if (status === "pass_by_report_conclusion") return "仅报告结论通过";
  if (status === "not_applicable") return "不适用";
  if (status === "candidate_refuted" || status === "refuted_candidate_resolved") return "满足";
  return status;
}

function ptrAtomicStatusTone(status: string): "success" | "danger" | "warn" | "info" {
  if (status === "match") return "success";
  if (status === "candidate_refuted" || status === "refuted_candidate_resolved") return "success";
  if (status === "mismatch") return "danger";
  if (status === "needs_review" || status === "candidate_found_needs_mapping" || status === "pass_by_report_conclusion") return "warn";
  return "info";
}

function ptrAtomicSourceLabel(source: string): string {
  if (source === "codex_review") return "自动复核结果";
  if (source === "ptr_table") return "规则结构化抽取";
  if (source === "ptr_text") return "规则结构化抽取";
  return source || "未标注";
}

function ClauseFindingItem({ finding }: { finding: Finding }) {
  const userStatus = findingUserFacingStatus(finding);

  return (
    <div className="evidence-text">
      <div className="button-row">
        <Badge variant={findingUserFacingStatusTone(userStatus)}>
          {findingUserFacingStatusLabel(userStatus, finding)}
        </Badge>
        <span>
          <strong>{finding.code}</strong>: {finding.message}
          {finding.location?.page_number ? `（第 ${finding.location.page_number} 页）` : ""}
        </span>
      </div>
    </div>
  );
}
