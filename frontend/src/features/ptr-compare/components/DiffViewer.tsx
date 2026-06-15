import type { DiffFragment } from "../../../entities/finding/types";

export interface DiffViewerProps {
  diffs: DiffFragment[];
  fallbackText?: string | null;
}

export function DiffViewer({ diffs, fallbackText }: DiffViewerProps) {
  if (diffs.length === 0) {
    return <p className="evidence-text">{fallbackText?.trim() || "暂无差异片段"}</p>;
  }

  return (
    <div className="diff-viewer">
      {diffs.map((fragment, index) => (
        <span className={`diff-fragment diff-${fragment.kind}`} key={`${fragment.kind}-${index}`}>
          {fragment.text}
        </span>
      ))}
    </div>
  );
}
