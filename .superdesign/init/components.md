# Shared UI Components

## AnimatedCounter

- File: `frontend/src/shared/ui/AnimatedCounter.tsx`
- Description: Animates numeric values with the shared tabular-number presentation.
- Key props: `value`, `className`, `formatValue`

```tsx
import { useEffect, useState } from "react";

export interface AnimatedCounterProps {
  value: number;
  className?: string;
  formatValue?: (value: number) => string;
}

export function AnimatedCounter({
  value,
  className = "",
  formatValue = (item) => item.toString(),
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const startValue = displayValue;
    const delta = value - startValue;
    if (delta === 0) return;

    const startedAt = performance.now();
    const duration = 360;
    let frame = 0;

    const tick = (time: number) => {
      const progress = Math.min((time - startedAt) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.round(startValue + delta * eased));
      if (progress < 1) frame = window.requestAnimationFrame(tick);
    };

    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [value]);

  return <span className={`tabular ${className}`.trim()}>{formatValue(displayValue)}</span>;
}
```

## Badge

- File: `frontend/src/shared/ui/Badge.tsx`
- Description: Semantic status badge with optional pulse animation.
- Key props: `children`, `variant`, `pulse`, `className`

```tsx
import type { ReactNode } from "react";

export type BadgeVariant = "success" | "danger" | "info" | "warn" | "accent";

export interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  pulse?: boolean;
  className?: string;
}

export function Badge({ children, variant = "info", pulse = false, className = "" }: BadgeProps) {
  return (
    <span className={`badge badge-${variant} ${pulse ? "badge-pulse" : ""} ${className}`.trim()}>
      <span className="badge-dot" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
```

## Button

- File: `frontend/src/shared/ui/Button.tsx`
- Description: Shared button primitive with visual variants and sizes.
- Key props: `children`, `variant`, `size`, standard button attributes

```tsx
import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button className={`button button-${variant} button-${size} ${className}`.trim()} type={type} {...props}>
      {children}
    </button>
  );
}
```

## ExportButton / ExportButtonGroup

- File: `frontend/src/shared/ui/ExportButton.tsx`
- Description: Export controls for JSON, PDF, and XLSX task results.
- Key props: `taskId`, `format`, `label`, `variant`, `disabled`, `onError`

```tsx
import { useState } from "react";

import type { ExportFormat } from "../../entities/task/types";
import { apiClient } from "../api/client";
import { Button, type ButtonProps } from "./Button";

type ExportState = "idle" | "loading" | "success" | "error";

export interface ExportButtonProps {
  taskId: string;
  format?: ExportFormat;
  label?: string;
  variant?: ButtonProps["variant"];
  disabled?: boolean;
  onError?: (message: string) => void;
}

export function ExportButton({
  taskId,
  format = "pdf",
  label,
  variant = "secondary",
  disabled = false,
  onError,
}: ExportButtonProps) {
  const [state, setState] = useState<ExportState>("idle");

  async function handleExport() {
    setState("loading");
    try {
      const { blob, fileName } = await apiClient.exportTask(taskId, format);
      downloadBlob(blob, fileName);
      setState("success");
      window.setTimeout(() => setState("idle"), 1600);
    } catch (error) {
      const message = error instanceof Error ? error.message : "导出失败";
      setState("error");
      onError?.(message);
      window.setTimeout(() => setState("idle"), 2400);
    }
  }

  return (
    <Button disabled={disabled || state === "loading"} onClick={handleExport} variant={variant}>
      {buttonText(state, label ?? `导出 ${format.toUpperCase()}`)}
    </Button>
  );
}

export interface ExportButtonGroupProps {
  taskId: string;
  disabled?: boolean;
  onError?: (message: string) => void;
}

export function ExportButtonGroup({ taskId, disabled = false, onError }: ExportButtonGroupProps) {
  return (
    <div className="button-row">
      <ExportButton disabled={disabled} format="json" onError={onError} taskId={taskId} />
      <ExportButton disabled={disabled} format="pdf" onError={onError} taskId={taskId} />
      <ExportButton disabled={disabled} format="xlsx" onError={onError} taskId={taskId} />
    </div>
  );
}

function buttonText(state: ExportState, label: string): string {
  if (state === "loading") return "导出中...";
  if (state === "success") return "已导出";
  if (state === "error") return "导出失败";
  return label;
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
```

## FileUpload

- File: `frontend/src/shared/ui/FileUpload.tsx`
- Description: Single- or dual-PDF drag-and-drop upload control.
- Key props: `onFilesChange`, `accept`, `multiple`, `maxFiles`, `mode`, `labels`, `disabled`

```tsx
import { useId, useMemo, useState } from "react";

import { GlassCard } from "./GlassCard";

export interface FileUploadFile {
  id: string;
  name: string;
  size: number;
  file: File;
}

export interface FileUploadProps {
  onFilesChange: (files: FileUploadFile[]) => void;
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  mode?: "single" | "double";
  labels?: {
    primary?: string;
    secondary?: string;
  };
  disabled?: boolean;
}

export function FileUpload({
  onFilesChange,
  accept = ".pdf",
  multiple = false,
  maxFiles,
  mode = "single",
  labels,
  disabled = false,
}: FileUploadProps) {
  const inputId = useId();
  const [files, setFiles] = useState<Array<FileUploadFile | undefined>>([]);
  const [draggingSlot, setDraggingSlot] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const slotCount = mode === "double" ? 2 : 1;

  const slots = useMemo(() => Array.from({ length: slotCount }, (_, index) => index), [slotCount]);

  function updateSlot(slotIndex: number, selected: File[]) {
    setError(null);
    const pdfFiles = selected.filter(isAcceptedPdf);
    if (pdfFiles.length === 0) {
      setError("仅支持 PDF 文件");
      return;
    }

    const limit = maxFiles ?? (mode === "single" && !multiple ? 1 : slotCount);
    const nextFiles = [...files];
    const incoming = pdfFiles.slice(0, limit);

    if (mode === "single") {
      nextFiles.splice(0, nextFiles.length, ...incoming.map(toUploadFile));
    } else {
      nextFiles[slotIndex] = toUploadFile(incoming[0]);
    }

    setFiles(nextFiles);
    onFilesChange(nextFiles.filter((item): item is FileUploadFile => Boolean(item)));
  }

  function removeSlot(slotIndex: number) {
    const nextFiles = [...files];
    nextFiles[slotIndex] = undefined;
    setFiles(nextFiles);
    onFilesChange(nextFiles.filter((item): item is FileUploadFile => Boolean(item)));
  }

  return (
    <div className="file-upload">
      {slots.map((slotIndex) => {
        const file = files[slotIndex];
        const label =
          mode === "double"
            ? slotIndex === 0
              ? labels?.primary ?? "上传第一个 PDF"
              : labels?.secondary ?? "上传第二个 PDF"
            : labels?.primary ?? "上传 PDF";

        return (
          <div className="file-slot" key={slotIndex}>
            {file ? (
              <GlassCard className="file-preview">
                <div className="file-icon" aria-hidden="true">
                  PDF
                </div>
                <div className="file-meta">
                  <p className="file-name">{file.name}</p>
                  <p className="file-size">{formatFileSize(file.size)}</p>
                </div>
                <button
                  aria-label={`移除 ${file.name}`}
                  className="icon-button danger"
                  disabled={disabled}
                  onClick={() => removeSlot(slotIndex)}
                  type="button"
                >
                  x
                </button>
              </GlassCard>
            ) : (
              <label
                className={`drop-zone ${draggingSlot === slotIndex ? "dragging" : ""} ${disabled ? "disabled" : ""}`}
                htmlFor={`${inputId}-${slotIndex}`}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setDraggingSlot(null);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  if (!disabled) setDraggingSlot(slotIndex);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  setDraggingSlot(null);
                  if (!disabled) updateSlot(slotIndex, Array.from(event.dataTransfer.files));
                }}
              >
                <span className="drop-icon" aria-hidden="true">
                  +
                </span>
                <span className="drop-title">{label}</span>
                <span className="drop-hint">拖拽 PDF 到此处，或点击选择</span>
                <input
                  accept={accept}
                  disabled={disabled}
                  id={`${inputId}-${slotIndex}`}
                  multiple={multiple && mode === "single"}
                  onChange={(event) => updateSlot(slotIndex, Array.from(event.target.files ?? []))}
                  type="file"
                />
              </label>
            )}
          </div>
        );
      })}
      {error ? <p className="form-error">{error}</p> : null}
    </div>
  );
}

function toUploadFile(file: File): FileUploadFile {
  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    name: file.name,
    size: file.size,
    file,
  };
}

function isAcceptedPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
```

## GlassCard

- File: `frontend/src/shared/ui/GlassCard.tsx`
- Description: Shared glassmorphism surface with hover and glow options.
- Key props: `children`, `hover`, `glow`, `className`, standard div attributes

```tsx
import type { HTMLAttributes, ReactNode } from "react";

export interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  glow?: boolean;
}

export function GlassCard({ children, hover = false, glow = false, className = "", ...props }: GlassCardProps) {
  return (
    <div
      className={`glass-card ${hover ? "glass-card-hover" : ""} ${glow ? "glass-card-glow" : ""} ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
}
```

## ProgressOverlay

- File: `frontend/src/shared/ui/ProgressOverlay.tsx`
- Description: Full-screen task progress overlay with rule and Codex audit detail.
- Key props: `task`, `visible`, `message`, `error`, `onReset`, `resetLabel`

```tsx
import type {
  CodexAuditProgressStatus,
  TaskCheckProgress,
  TaskCheckProgressStatus,
  TaskProgressDetails,
  TaskProgressPhase,
  TaskStatus,
} from "../../entities/task/types";
import { taskStateLabel } from "../../entities/task/types";
import { Button } from "./Button";
import { GlassCard } from "./GlassCard";

export interface ProgressOverlayProps {
  task?: TaskStatus | null;
  visible?: boolean;
  message?: string;
  error?: string | null;
  onReset?: () => void;
  resetLabel?: string;
}

export function ProgressOverlay({ task, visible, message, error, onReset, resetLabel = "重新上传" }: ProgressOverlayProps) {
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
        {onReset ? (
          <div className="button-row progress-actions">
            <Button onClick={onReset} variant="secondary">
              {resetLabel}
            </Button>
          </div>
        ) : null}
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
    needs_policy_review: "标准版本政策待确认",
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
```

## StatusPill

- File: `frontend/src/shared/ui/StatusPill.tsx`
- Description: Legacy compact task-module status indicator.
- Key props: `state`, `label`

```tsx
import type { TaskModuleState } from "../../entities/task";

interface StatusPillProps {
  state: TaskModuleState;
  label: string;
}

export function StatusPill({ state, label }: StatusPillProps) {
  return <span className={`status-pill ${state}`}>{label}</span>;
}
```
