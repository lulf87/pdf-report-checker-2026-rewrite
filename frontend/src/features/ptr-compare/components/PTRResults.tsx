import { useMemo, useState } from "react";

import type { PTRFilterMode } from "../../../entities/ptr/types";
import { toPTRClauseViewModels } from "../../../entities/ptr/types";
import type { PTRComparisonDetails, TaskResult, TaskStatus } from "../../../entities/task/types";
import { normalizeCodexReviews } from "../../../entities/codexReview/types";
import { CodexReviewOverview } from "../../codex-review/components/CodexReviewPanel";
import { AnimatedCounter } from "../../../shared/ui/AnimatedCounter";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { ExportButtonGroup } from "../../../shared/ui/ExportButton";
import { GlassCard } from "../../../shared/ui/GlassCard";
import { ClauseList } from "./ClauseList";

export interface PTRResultsProps {
  task: TaskStatus;
  result: TaskResult;
  onBack: () => void;
  onReupload: () => void;
}

export function PTRResults({ task, result, onBack, onReupload }: PTRResultsProps) {
  const [filter, setFilter] = useState<PTRFilterMode>("issues");
  const [exportError, setExportError] = useState<string | null>(null);
  const ptrDetails = result.metadata.ptr_comparison_details;
  const ptrOcrRequired = isPtrOcrRequired(ptrDetails);
  const resultBadge = finalResultBadge(result, ptrDetails);
  const clauses = useMemo(
    () => toPTRClauseViewModels(result),
    [result],
  );
  const codexReviews = useMemo(
    () => result.check_results.flatMap((item) => normalizeCodexReviews(item.codex_reviews)),
    [result.check_results],
  );
  const issueCount = clauses.filter((item) => item.status !== "pass" && item.status !== "skip").length;

  return (
    <section className="panel-stack">
      <header className="page-header compact">
        <div>
          <p className="eyebrow">PTR RESULT</p>
          <h1>PTR 条款核对结果</h1>
          <p className="muted">任务 ID: {task.task_id}</p>
        </div>
        <Badge variant={resultBadge.variant}>{resultBadge.label}</Badge>
      </header>

      {ptrDetails && ptrOcrRequired ? <PtrOcrRequiredNotice details={ptrDetails} /> : null}

      {ptrDetails && !ptrOcrRequired ? (
        <div className="metric-grid">
          {ptrDetails.scope_consistency ? (
            <StatusMetric
              label="报告检验范围核对"
              reason={ptrDetails.scope_consistency.reason}
              tone={scopeStatusTone(ptrDetails.scope_consistency.status)}
              value={scopeStatusLabel(ptrDetails.scope_consistency.status)}
            />
          ) : null}
          <Metric label="技术要求条款数" value={ptrDetails.requirements_count} />
          <Metric label="已覆盖" value={ptrDetails.covered_count} />
          <Metric label="排除项" value={ptrDetails.excluded_items?.length ?? ptrDetails.scope_consistency?.excluded_topics?.length ?? 0} />
          <Metric label="未覆盖" value={ptrDetails.missing_count} tone={ptrDetails.missing_count > 0 ? "warn" : "info"} />
          <Metric label="结果不一致" value={ptrDetails.mismatch_count} tone={ptrDetails.mismatch_count > 0 ? "warn" : "info"} />
          <Metric label="需复核" value={ptrDetails.needs_review_count} tone={ptrDetails.needs_review_count > 0 ? "warn" : "info"} />
          <Metric label="确认问题" value={ptrDetails.confirmed_errors_count} tone={ptrDetails.confirmed_errors_count > 0 ? "danger" : "info"} />
          <Metric label="候选已排除" value={ptrDetails.refuted_findings_count} />
        </div>
      ) : (
        <div className="metric-grid">
          <Metric label="候选错误" value={result.summary.candidate_errors_count} tone="warn" />
          <Metric label="确认错误" value={result.summary.confirmed_errors_count} tone="danger" />
          <Metric label="人工复核" value={result.summary.manual_review_required_count} tone="warn" />
          <Metric label="已反驳候选" value={result.summary.refuted_findings_count} />
          {result.summary.out_of_scope_findings_count > 0 ? (
            <Metric label="本次未覆盖" value={result.summary.out_of_scope_findings_count} />
          ) : null}
        </div>
      )}

      <CodexAuditScopeNotice metadata={result.metadata} />

      {ptrDetails && !ptrOcrRequired ? <ModelTableContextNotice details={ptrDetails} /> : null}

      <CodexReviewOverview reviews={codexReviews} />

      <GlassCard className="result-card">
        <div className="row-head">
          <div className="filter-row" role="group" aria-label="PTR 结果筛选">
            <Button onClick={() => setFilter("issues")} variant={filter === "issues" ? "primary" : "secondary"}>
              仅显示不一致 ({issueCount})
            </Button>
            <Button onClick={() => setFilter("all")} variant={filter === "all" ? "primary" : "secondary"}>
              全部 ({clauses.length})
            </Button>
          </div>
          <ExportButtonGroup onError={setExportError} taskId={task.task_id} />
        </div>
        {exportError ? <p className="form-error">{exportError}</p> : null}
      </GlassCard>

      <ClauseList clauses={clauses} filter={filter} />

      <div className="button-row">
        <Button onClick={onBack} variant="secondary">
          返回首页
        </Button>
        <Button onClick={onReupload} variant="primary">
          重新上传
        </Button>
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

function StatusMetric({
  label,
  value,
  reason,
  tone = "info",
}: {
  label: string;
  value: string;
  reason?: string | null;
  tone?: "info" | "danger" | "warn";
}) {
  return (
    <GlassCard className={`metric-card ${tone === "danger" ? "issue-danger" : tone === "warn" ? "issue-warn" : ""}`}>
      <p className="muted">{label}</p>
      <p className="metric-value">{value}</p>
      {reason ? <p className="muted">{reason}</p> : null}
    </GlassCard>
  );
}

function PtrOcrRequiredNotice({ details }: { details: PTRComparisonDetails }) {
  const pages = details.ptr_pages_need_ocr ?? [];
  return (
    <GlassCard className="result-card issue-warn">
      <div className="row-head">
        <div>
          <p className="row-title">PTR 文档需要 OCR</p>
          <p className="muted">该技术要求 PDF 无文本层，系统未能解析第 2 章，尚未完成 PTR/report 比对。</p>
          <p className="muted">请启用 OCR/视觉增强，或上传可检索文本 PDF。</p>
          {pages.length > 0 ? <p className="muted">需 OCR 页码：{pages.join("、")}</p> : null}
        </div>
        <Badge variant="warn">需处理</Badge>
      </div>
    </GlassCard>
  );
}

function ModelTableContextNotice({ details }: { details: PTRComparisonDetails }) {
  const modelContext = details.report_model_context;
  const primaryModel = modelContext?.primary_model?.trim();
  const candidates = modelContext?.model_candidates ?? [];
  const modelTables = (details.ptr_table_registry ?? []).filter((entry) =>
    entry.column_axes?.some((axis) => axis.axis_type === "model"),
  );

  if (!primaryModel && candidates.length === 0 && modelTables.length === 0) return null;

  const primaryCandidate = primaryModel ? candidates.find((candidate) => candidate.value === primaryModel) : undefined;

  return (
    <GlassCard className="result-card">
      <div className="row-head">
        <div>
          <p className="row-title">型号与 PTR 表格依据</p>
          <div className="comparison-source-list">
            <span className="comparison-source">
              报告型号 · {primaryModel || "待确认"}
              {primaryCandidate?.source ? ` · ${modelCandidateSourceLabel(primaryCandidate.source)}` : ""}
              {primaryCandidate?.page ? ` · 第 ${primaryCandidate.page} 页` : ""}
            </span>
            {modelTables.map((entry) => {
              const modelAxis = entry.column_axes?.find((axis) => axis.axis_type === "model");
              const applicableColumn =
                primaryModel && modelAxis?.labels.some((label) => sameDisplayLabel(label, primaryModel)) ? primaryModel : "待确认";
              return (
                <span className="comparison-source" key={`${entry.table_id ?? entry.table_number}-${entry.parent_clause ?? "parent"}`}>
                  PTR 表格 · 父级条款 {entry.parent_clause || "未标注"} · 表 {entry.table_number}
                  {entry.table_title ? ` ${entry.table_title}` : ""} · 适用列 {applicableColumn}
                  {entry.row_labels?.length ? ` · ${entry.row_labels.length} 行` : ""}
                  {entry.source_page ? ` · PTR 第 ${entry.source_page} 页` : ""}
                </span>
              );
            })}
          </div>
        </div>
        <Badge variant={primaryModel ? "info" : "warn"}>{primaryModel ? "已识别" : "待复核"}</Badge>
      </div>
    </GlassCard>
  );
}

function modelCandidateSourceLabel(source: string): string {
  if (source === "report_homepage") return "报告首页";
  if (source === "sample_description") return "样品描述";
  if (source === "model_specification") return "型号规格字段";
  return source;
}

function sameDisplayLabel(left: string, right: string): boolean {
  return left.replace(/\s+/g, "").toUpperCase() === right.replace(/\s+/g, "").toUpperCase();
}

function scopeStatusLabel(status: string): string {
  if (status === "passed") return "通过";
  if (status === "failed") return "不一致";
  if (status === "needs_review") return "需复核";
  return status;
}

function scopeStatusTone(status: string): "info" | "danger" | "warn" {
  if (status === "passed") return "info";
  if (status === "failed") return "danger";
  return "warn";
}

function finalResultBadge(result: TaskResult, ptrDetails?: PTRComparisonDetails): { label: string; variant: "success" | "danger" | "warn" | "info" } {
  if (isPtrOcrRequired(ptrDetails)) {
    return { label: "PTR 文档需要 OCR", variant: "warn" };
  }
  if (ptrDetails?.overall_status === "passed") {
    return { label: "最终结论：通过", variant: "success" };
  }
  if (ptrDetails?.overall_status === "needs_review") {
    return { label: "最终结论：需复核", variant: "warn" };
  }
  if (ptrDetails?.overall_status === "failed") {
    return { label: "最终结论：不通过", variant: "danger" };
  }
  if (ptrDetails?.overall_status === "audit_incomplete") {
    return { label: "最终结论：复审未完成", variant: "danger" };
  }
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

function isPtrOcrRequired(ptrDetails?: PTRComparisonDetails): boolean {
  return ptrDetails?.ptr_ocr_required === true || ptrDetails?.ptr_extraction_status === "ocr_required";
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
