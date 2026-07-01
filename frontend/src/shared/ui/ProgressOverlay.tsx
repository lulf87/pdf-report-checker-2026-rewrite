import type {
  CodexAuditProgressStatus,
  TaskCheckProgress,
  TaskCheckProgressStatus,
  TaskProgressDetails,
  TaskProgressPhase,
  TaskStatus,
} from "../../entities/task/types";
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
  const progressDetails = task ? taskProgressDetails(task) : null;
  const phaseLabel = progressDetails?.phase_label ?? (progressDetails ? phaseFallbackLabel(progressDetails.phase) : null);
  const codexProgress = progressDetails?.codex_audit;

  return (
    <div className="overlay" role="status" aria-live="polite">
      <GlassCard className="progress-card">
        <div className={`progress-mark ${failed ? "danger" : ""}`}>{failed ? "!" : "..."}</div>
        <h2>{task ? taskStateLabel(task.status) : "处理中"}</h2>
        <p className="muted">{error ?? task?.error_message ?? progressDetails?.error_message ?? task?.current_step ?? message ?? "任务处理中"}</p>
        <div className="progress-track" aria-label="处理进度">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="progress-headline">
          <span>{phaseLabel ?? task?.current_step ?? message ?? "任务处理中"}</span>
          <strong>{Math.round(progress)}%</strong>
        </div>

        {progressDetails?.checks?.length ? <ProgressChecklist checks={progressDetails.checks} /> : null}
        {codexProgress?.enabled ? <CodexProgressSummary codex={codexProgress} /> : null}
      </GlassCard>
    </div>
  );
}

function ProgressChecklist({ checks }: { checks: TaskCheckProgress[] }) {
  return (
    <div className="progress-checklist" aria-label="C01-C11 检查进度">
      {checks.map((check) => (
        <div className={`progress-check progress-check-${check.status}`} key={check.check_id}>
          <span className="progress-check-id">{check.check_id}</span>
          <span className="progress-check-name">{check.check_name}</span>
          <span className="progress-check-status">{checkStatusProgressLabel(check.status)}</span>
        </div>
      ))}
    </div>
  );
}

function CodexProgressSummary({ codex }: { codex: NonNullable<TaskProgressDetails["codex_audit"]> }) {
  return (
    <div className={`codex-progress codex-progress-${codex.status}`}>
      <div className="progress-headline compact">
        <span>{codexStatusLabel(codex.status)}</span>
        <strong>
          {codex.completed_reviews_count} / {codex.total_reviews_count}
        </strong>
      </div>
      <div className="codex-progress-grid">
        <span>当前复核项目</span>
        <strong>{[codex.current_check_id, targetTypeLabel(codex.current_target_type)].filter(Boolean).join(" ") || "待开始"}</strong>
        <span>批次进度</span>
        <strong>
          {codex.completed_batches_count} / {codex.total_batches_count}
        </strong>
        {codex.retry_count > 0 ? (
          <>
            <span>重试</span>
            <strong>{retryReasonLabel(codex.last_retry_reason)}</strong>
          </>
        ) : null}
        {codex.error_code ? (
          <>
            <span>错误</span>
            <strong>{codex.error_code}</strong>
          </>
        ) : null}
      </div>
    </div>
  );
}

function taskProgressDetails(task: TaskStatus): TaskProgressDetails | null {
  if (task.progress_details) return task.progress_details;
  const metadataProgress = task.metadata.progress_details;
  return isProgressDetails(metadataProgress) ? metadataProgress : null;
}

function isProgressDetails(value: unknown): value is TaskProgressDetails {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  return typeof record.phase === "string";
}

function phaseFallbackLabel(phase: TaskProgressPhase): string {
  const labels: Record<TaskProgressPhase, string> = {
    upload: "上传任务",
    parse: "PDF解析",
    extract: "结构化抽取",
    rules: "规则初筛",
    evidence: "证据准备",
    codex_audit: "LLM/Codex复核",
    finalize: "结果整理",
    completed: "已完成",
    error: "失败",
  };
  return labels[phase];
}

function checkStatusProgressLabel(status: TaskCheckProgressStatus): string {
  const labels: Record<TaskCheckProgressStatus, string> = {
    pending: "待处理",
    running: "进行中",
    passed: "通过",
    failed: "候选问题",
    skipped: "跳过",
    needs_review: "需复核",
    error: "异常",
  };
  return labels[status];
}

function codexStatusLabel(status: CodexAuditProgressStatus): string {
  const labels: Record<CodexAuditProgressStatus, string> = {
    pending: "LLM/Codex 复核待开始",
    running: "LLM/Codex 复核中",
    retrying: "LLM/Codex 正在重试缺失复核项",
    completed: "LLM/Codex 复核完成",
    failed: "LLM/Codex 复核未完成",
  };
  return labels[status];
}

function retryReasonLabel(reason?: string | null): string {
  if (reason === "CODEX_OUTPUT_MISSING_TARGET") return "正在重试缺失复核项";
  if (reason === "CODEX_TIMEOUT") return "正在重试超时批次";
  return "正在重试";
}

function targetTypeLabel(targetType?: string | null): string | null {
  if (!targetType) return null;
  if (targetType === "label_ocr") return "标签证据";
  if (targetType === "inspection_item") return "检验项目";
  if (targetType === "photo_caption") return "照片证据";
  if (targetType === "check_result") return "规则摘要";
  return targetType;
}
