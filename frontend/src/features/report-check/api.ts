import { apiClient } from "../../shared/api/client";
import type { ExportFormat, TaskResult, TaskStatus } from "../../entities/task/types";

export interface ReportCheckUploadOptions {
  enableLlm?: boolean;
}

export async function uploadReportCheckFile(
  reportFile: File,
  options: ReportCheckUploadOptions = {},
): Promise<TaskStatus> {
  const query = options.enableLlm ? "?enable_llm=true" : "";
  return apiClient.postForm<TaskStatus>(`/api/tasks/report-check${query}`, {
    report_file: reportFile,
  });
}

export function getReportCheckTask(taskId: string): Promise<TaskStatus> {
  return apiClient.getTaskStatus(taskId);
}

export function getReportCheckResult(taskId: string): Promise<TaskResult> {
  return apiClient.getTaskResult(taskId);
}

export function exportReportCheckResult(taskId: string, format: ExportFormat) {
  return apiClient.exportTask(taskId, format);
}

export async function waitForReportCheckResult(
  taskId: string,
  onStatus: (task: TaskStatus) => void,
  intervalMs = 1000,
  timeoutMs = 60000,
): Promise<TaskResult> {
  const startedAt = Date.now();

  while (Date.now() - startedAt <= timeoutMs) {
    const task = await getReportCheckTask(taskId);
    onStatus(task);
    if (task.status === "completed") return getReportCheckResult(taskId);
    if (task.status === "error") throw new Error(task.error_message || "报告自检失败");
    await delay(intervalMs);
  }

  throw new Error("报告自检超时");
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
