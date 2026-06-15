import type { TaskStatus } from "../../entities/task/types";
import { taskStateLabel } from "../../entities/task/types";
import { GlassCard } from "./GlassCard";

export interface ProgressOverlayProps {
  task?: TaskStatus | null;
  visible?: boolean;
  message?: string;
  error?: string | null;
}

export function ProgressOverlay({ task, visible, message, error }: ProgressOverlayProps) {
  const isVisible = visible ?? Boolean(task && task.status !== "completed");
  if (!isVisible) return null;

  const progress = Math.max(0, Math.min(100, task?.progress ?? 0));
  const failed = task?.status === "error" || Boolean(error);

  return (
    <div className="overlay" role="status" aria-live="polite">
      <GlassCard className="progress-card">
        <div className={`progress-mark ${failed ? "danger" : ""}`}>{failed ? "!" : "..."}</div>
        <h2>{task ? taskStateLabel(task.status) : "处理中"}</h2>
        <p className="muted">{error ?? task?.error_message ?? message ?? task?.current_step ?? "任务处理中"}</p>
        <div className="progress-track" aria-label="处理进度">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <p className="progress-number">{Math.round(progress)}%</p>
      </GlassCard>
    </div>
  );
}
