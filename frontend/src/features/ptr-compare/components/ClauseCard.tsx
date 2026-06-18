import { useState } from "react";

import { groupCodexReviewsByFinding } from "../../../entities/codexReview/types";
import { severityLabel, severityTone } from "../../../entities/finding/types";
import type { PTRClauseViewModel } from "../../../entities/ptr/types";
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
  const tone = severityTone(clause.severity);
  const hasIssue = tone === "danger" || tone === "warn";
  const firstFinding = clause.findings[0];
  const groupedCodexReviews = groupCodexReviewsByFinding(clause.findings, clause.codexReviews);

  return (
    <article className={`clause-card ${tone === "danger" ? "issue-danger" : tone === "warn" ? "issue-warn" : ""}`}>
      <div className="row-head">
        <div>
          <p className="row-title">
            {clause.checkId}: {clause.title}
          </p>
          <p className="row-summary">{clause.summary || firstFinding?.message || "后端未返回摘要"}</p>
        </div>
        <div className="button-row">
          {clause.codexReviews.length > 0 ? <Badge variant="accent">Codex {clause.codexReviews.length}</Badge> : null}
          <Badge pulse={hasIssue} variant={tone}>
            {clause.severity ? severityLabel(clause.severity) : checkStatusLabel(clause.status)}
          </Badge>
          <Button onClick={() => setExpanded((value) => !value)} size="sm" variant="ghost">
            {expanded ? "收起" : "展开"}
          </Button>
        </div>
      </div>

      {expanded ? (
        <div className="details">
          <DiffViewer diffs={clause.diffs} fallbackText={firstFinding?.message ?? clause.summary} />
          {clause.findings.length > 0 ? (
            <div className="panel-stack">
              {clause.findings.map((finding) => (
                <div className="evidence-text" key={finding.id}>
                  <strong>{finding.code}</strong>: {finding.message}
                  {finding.location?.page_number ? `（第 ${finding.location.page_number} 页）` : ""}
                  <FindingCodexReviewSummary reviews={groupedCodexReviews.byFindingId[finding.id]} />
                </div>
              ))}
              <CodexReviewList reviews={groupedCodexReviews.unassociated} title="其他 Codex 审核意见" />
            </div>
          ) : clause.codexReviews.length > 0 ? (
            <CodexReviewList reviews={clause.codexReviews} title="Codex 审核意见" />
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
