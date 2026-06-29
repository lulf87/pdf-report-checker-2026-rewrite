import { apiClient } from "../../shared/api/client";
import type { AuditOptions, ExportFormat, TaskResult, TaskStatus } from "../../entities/task/types";

export async function uploadPTRCompareFiles(
  ptrFile: File,
  reportFile: File,
  auditOptions?: AuditOptions,
): Promise<TaskStatus> {
  return apiClient.postForm<TaskStatus>("/api/tasks/ptr-compare", {
    ptr_file: ptrFile,
    report_file: reportFile,
    included_check_ids: auditOptions?.included_check_ids,
    included_finding_codes: auditOptions?.included_finding_codes,
    excluded_check_ids: auditOptions?.excluded_check_ids,
    max_targets_per_batch: auditOptions?.max_targets_per_batch,
    max_parallel_jobs: auditOptions?.max_parallel_jobs,
  });
}

export function getPTRCompareTask(taskId: string): Promise<TaskStatus> {
  return apiClient.getTaskStatus(taskId);
}

export function getPTRCompareResult(taskId: string): Promise<TaskResult> {
  return apiClient.getTaskResult(taskId);
}

export function exportPTRCompareResult(taskId: string, format: ExportFormat) {
  return apiClient.exportTask(taskId, format);
}

export async function waitForPTRCompareResult(
  taskId: string,
  onStatus: (task: TaskStatus) => void,
  intervalMs = 1000,
  timeoutMs = 60000,
): Promise<TaskResult> {
  const startedAt = Date.now();

  while (Date.now() - startedAt <= timeoutMs) {
    const task = await getPTRCompareTask(taskId);
    onStatus(task);
    if (task.status === "completed") return getPTRCompareResult(taskId);
    if (task.status === "error") throw new Error(task.error_message || "PTR 核对失败");
    await delay(intervalMs);
  }

  throw new Error("PTR 核对超时");
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
