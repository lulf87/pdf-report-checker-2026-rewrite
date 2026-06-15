import type { PTRClauseViewModel, PTRFilterMode } from "../../../entities/ptr/types";
import { isPTRIssue } from "../../../entities/ptr/types";
import { ClauseCard } from "./ClauseCard";

export interface ClauseListProps {
  clauses: PTRClauseViewModel[];
  filter: PTRFilterMode;
}

export function ClauseList({ clauses, filter }: ClauseListProps) {
  const visibleClauses = filter === "issues" ? clauses.filter(isPTRIssue) : clauses;

  if (visibleClauses.length === 0) {
    return (
      <div className="glass-card result-card">
        <p className="muted">{filter === "issues" ? "没有需要处理的 PTR 条款。" : "暂无 PTR 条款结果。"}</p>
      </div>
    );
  }

  return (
    <div className="result-list">
      {visibleClauses.map((clause) => (
        <ClauseCard clause={clause} key={clause.id} />
      ))}
    </div>
  );
}
