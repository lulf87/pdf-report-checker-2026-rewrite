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
        <Badge variant={issueCount > 0 ? "warn" : "success"}>{issueCount > 0 ? "需处理" : "无问题"}</Badge>
      </header>

      <div className="metric-grid three">
        <GlassCard className="metric-card">
          <p className="muted">总检查</p>
          <p className="metric-value">
            <AnimatedCounter value={result.summary.total_checks} />
          </p>
        </GlassCard>
        <GlassCard className="metric-card">
          <p className="muted">失败</p>
          <p className="metric-value">
            <AnimatedCounter value={result.summary.fail_count} />
          </p>
        </GlassCard>
        <GlassCard className="metric-card">
          <p className="muted">复核</p>
          <p className="metric-value">
            <AnimatedCounter value={result.summary.review_count} />
          </p>
        </GlassCard>
      </div>

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
