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
