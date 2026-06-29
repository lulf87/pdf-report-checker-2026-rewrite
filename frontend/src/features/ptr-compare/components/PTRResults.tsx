import { useMemo, useState } from "react";

import type { PTRFilterMode } from "../../../entities/ptr/types";
import { toPTRClauseViewModel } from "../../../entities/ptr/types";
import type { TaskResult, TaskStatus } from "../../../entities/task/types";
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
  const resultBadge = finalResultBadge(result);
  const clauses = useMemo(
    () => result.check_results.map((item, index) => toPTRClauseViewModel(item, index)),
    [result.check_results],
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
