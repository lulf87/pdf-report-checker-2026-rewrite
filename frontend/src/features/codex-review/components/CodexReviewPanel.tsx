import type { CodexReviewResult } from "../../../entities/codexReview/types";
import {
  CODEX_CONFIDENCE_LABELS,
  CODEX_STATUS_LABELS,
  codexReviewPrimaryLabel,
  codexReviewTone,
  formatCodexReviewError,
  normalizeCodexReviews,
  summarizeCodexReviews,
} from "../../../entities/codexReview/types";
import { Badge } from "../../../shared/ui/Badge";
import { GlassCard } from "../../../shared/ui/GlassCard";

export interface CodexReviewOverviewProps {
  reviews?: readonly CodexReviewResult[] | null;
}

export function CodexReviewOverview({ reviews }: CodexReviewOverviewProps) {
  const items = normalizeCodexReviews(reviews);
  if (items.length === 0) return null;

  const summary = summarizeCodexReviews(items);

  return (
    <GlassCard className="codex-overview">
      <div className="row-head">
        <div>
          <p className="eyebrow">CODEX REVIEW</p>
          <h2>Codex 审核意见</h2>
        </div>
        <Badge variant={summary.failed_or_skipped > 0 ? "warn" : "accent"}>{summary.total} 条</Badge>
      </div>
      <div className="codex-summary-grid" aria-label="Codex 审核统计">
        <CodexSummaryItem label="确认" value={summary.confirm} />
        <CodexSummaryItem label="可能误报" value={summary.refute} />
        <CodexSummaryItem label="人工复核" value={summary.uncertain} />
        <CodexSummaryItem label="新增建议" value={summary.add_finding} />
        <CodexSummaryItem label="失败/跳过" value={summary.failed_or_skipped} />
      </div>
    </GlassCard>
  );
}

export interface CodexReviewListProps {
  reviews?: readonly CodexReviewResult[] | null;
  title?: string;
}

export function CodexReviewList({ reviews, title = "Codex 审核意见" }: CodexReviewListProps) {
  const items = normalizeCodexReviews(reviews);
  if (items.length === 0) return null;

  return (
    <div className="codex-review-list" aria-label={title}>
      <p className="codex-review-list-title">{title}</p>
      {items.map((review) => (
        <CodexReviewItem key={review.review_id} review={review} />
      ))}
    </div>
  );
}

export interface FindingCodexReviewSummaryProps {
  reviews?: readonly CodexReviewResult[] | null;
}

export function FindingCodexReviewSummary({ reviews }: FindingCodexReviewSummaryProps) {
  return <CodexReviewList reviews={reviews} title="关联 Codex 审核" />;
}

function CodexSummaryItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="codex-summary-item">
      <span className="codex-summary-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CodexReviewItem({ review }: { review: CodexReviewResult }) {
  const confidence = review.confidence ? CODEX_CONFIDENCE_LABELS[review.confidence] : null;
  const formattedError = review.error ? formatCodexReviewError(review.error) : null;

  return (
    <article className={`codex-review-item codex-review-${codexReviewTone(review)}`}>
      <div className="row-head">
        <div>
          <p className="codex-review-title">{codexReviewPrimaryLabel(review)}</p>
          <p className="codex-review-target">
            {review.target.check_id ? `${review.target.check_id} · ` : ""}
            {review.target.finding_code ?? review.target.target_type}
          </p>
        </div>
        <Badge variant={codexReviewTone(review)}>{CODEX_STATUS_LABELS[review.status]}</Badge>
      </div>

      {review.reasoning_summary ? <p className="codex-review-summary">{review.reasoning_summary}</p> : null}

      <div className="codex-review-meta">
        {confidence ? <span>置信度: {confidence}</span> : null}
        {review.suggested_severity ? <span>Codex 建议级别: {review.suggested_severity}</span> : null}
        {review.target.summary ? <span>目标: {review.target.summary}</span> : null}
      </div>

      {review.evidence_refs.length > 0 ? (
        <p className="codex-review-refs">证据: {review.evidence_refs.join(", ")}</p>
      ) : null}

      {review.suggested_finding ? (
        <div className="codex-suggested-finding">
          <strong>{review.suggested_finding.code ?? "Codex 建议"}</strong>: {review.suggested_finding.message}
          {review.suggested_finding.severity ? `（${review.suggested_finding.severity}）` : ""}
        </div>
      ) : null}

      {formattedError ? (
        <div className="codex-error">
          <strong>LLM 复核提示</strong>: {formattedError.message}
          {formattedError.detail ? (
            <details className="advanced-audit-settings">
              <summary>高级详情</summary>
              <pre>{formattedError.detail}</pre>
            </details>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
