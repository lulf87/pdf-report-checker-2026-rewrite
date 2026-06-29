import { apiClient } from "../../shared/api/client";
import type { AuditOptions, ExportFormat, TaskResult, TaskStatus } from "../../entities/task/types";

export interface ReportCheckUploadOptions {
  enableLlm?: boolean;
  auditOptions?: AuditOptions;
}

export async function uploadReportCheckFile(
  reportFile: File,
  options: ReportCheckUploadOptions = {},
): Promise<TaskStatus> {
  const query = options.enableLlm ? "?enable_llm=true" : "";
  return apiClient.postForm<TaskStatus>(`/api/tasks/report-check${query}`, {
    report_file: reportFile,
    ...formFieldsFromAuditOptions(options.auditOptions),
  });
}

function formFieldsFromAuditOptions(options?: AuditOptions): Record<string, string | number | undefined> {
  return {
    included_check_ids: options?.included_check_ids,
    included_finding_codes: options?.included_finding_codes,
    excluded_check_ids: options?.excluded_check_ids,
    max_targets_per_batch: options?.max_targets_per_batch,
    max_parallel_jobs: options?.max_parallel_jobs,
  };
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
  timeoutMs = 60 * 60 * 1000,
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
