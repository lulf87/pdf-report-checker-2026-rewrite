import { useEffect, useRef, useState } from "react";

import { formatCodexRuntimeError } from "../../../entities/codexReview/types";
import type { AuditOptions, TaskResult, TaskStatus } from "../../../entities/task/types";
import {
  CodexModelSelector,
  DEFAULT_CODEX_RUNTIME_SELECTION,
} from "../../codex-review/components/CodexModelSelector";
import { Button } from "../../../shared/ui/Button";
import { FileUpload, type FileUploadFile } from "../../../shared/ui/FileUpload";
import { GlassCard } from "../../../shared/ui/GlassCard";
import { ProgressOverlay } from "../../../shared/ui/ProgressOverlay";
import { clearTaskSession, loadTaskSession, saveTaskSession } from "../../../shared/lib/taskSessionStorage";
import { getPTRCompareResult, getPTRCompareTask, uploadPTRCompareFiles, waitForPTRCompareResult } from "../api";

export interface PTRUploadProps {
  onComplete: (task: TaskStatus, result: TaskResult) => void;
  onBack: () => void;
}

export function PTRUpload({ onComplete, onBack }: PTRUploadProps) {
  const [files, setFiles] = useState<FileUploadFile[]>([]);
  const [auditOptions, setAuditOptions] = useState({
    ...DEFAULT_CODEX_RUNTIME_SELECTION,
    included_check_ids: "",
    included_finding_codes: "",
    excluded_check_ids: "",
  });
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [message, setMessage] = useState<string>("上传并创建任务");
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lastTaskRef = useRef<TaskStatus | null>(null);
  const activeRunIdRef = useRef(0);

  useEffect(() => {
    const storedSession = loadTaskSession("ptr_compare");
    if (!storedSession) return;

    if (storedSession.task.status === "error") {
      lastTaskRef.current = storedSession.task;
      setTask(storedSession.task);
      setMessage(storedSession.message ?? "上次任务失败");
      showTaskError(storedSession.task.error_message ?? storedSession.error ?? "上次 PTR 核对失败");
      return;
    }

    let cancelled = false;
    const restoreTask = async () => {
      const runId = ++activeRunIdRef.current;
      setBusy(true);
      clearError();
      setTask(storedSession.task);
      setMessage("正在恢复上次 PTR 核对任务...");

      try {
        const latestTask = await getPTRCompareTask(storedSession.task.task_id);
        if (cancelled || !isActiveRun(runId)) return;
        rememberTask(latestTask, "正在恢复上次 PTR 核对任务...");

        if (latestTask.status === "error") {
          const nextError = latestTask.error_message || "上次 PTR 核对失败";
          rememberTask(latestTask, "上次任务失败", nextError);
          showTaskError(nextError);
          setBusy(false);
          return;
        }

        const result =
          latestTask.status === "completed"
            ? await getPTRCompareResult(latestTask.task_id)
            : await waitForPTRCompareResult(latestTask.task_id, (nextTask) => {
                if (!cancelled && isActiveRun(runId)) rememberTask(nextTask, "正在恢复上次 PTR 核对任务...");
              });
        if (cancelled || !isActiveRun(runId)) return;
        const finalTask = latestTask.status === "completed" ? latestTask : await getPTRCompareTask(latestTask.task_id);
        if (cancelled || !isActiveRun(runId)) return;
        rememberTask(finalTask, "PTR 核对已完成");
        onComplete(finalTask, result);
      } catch (restoreError) {
        if (cancelled || !isActiveRun(runId)) return;
        const nextError = restoreError instanceof Error ? restoreError.message : "无法恢复上次 PTR 核对任务";
        clearRestoredTask(nextError);
      }
    };

    void restoreTask();
    return () => {
      cancelled = true;
    };
  }, []);

  function isActiveRun(runId: number): boolean {
    return activeRunIdRef.current === runId;
  }

  function clearRestoredTask(nextError: string) {
    clearTaskSession("ptr_compare");
    lastTaskRef.current = null;
    setTask(null);
    setMessage("上传并创建任务");
    showTaskError(nextError);
    setBusy(false);
  }

  async function handleUpload() {
    const ptrFile = files[0]?.file;
    const reportFile = files[1]?.file;
    if (!ptrFile || !reportFile) {
      setError("请同时上传 PTR PDF 和检验报告 PDF");
      setErrorDetail(null);
      return;
    }

    const runId = ++activeRunIdRef.current;
    setBusy(true);
    clearError();
    setMessage("正在上传文件...");

    try {
      const createdTask = await uploadPTRCompareFiles(ptrFile, reportFile, compactAuditOptions(auditOptions));
      if (!isActiveRun(runId)) return;
      rememberTask(createdTask, "正在处理 PTR 核对任务...");
      const result =
        createdTask.status === "completed"
          ? await getPTRCompareResult(createdTask.task_id)
          : await waitForPTRCompareResult(createdTask.task_id, (nextTask) =>
              isActiveRun(runId) ? rememberTask(nextTask, "正在处理 PTR 核对任务...") : undefined,
            );
      if (!isActiveRun(runId)) return;
      const finalTask = createdTask.status === "completed" ? createdTask : await getPTRCompareTask(createdTask.task_id);
      if (!isActiveRun(runId)) return;
      rememberTask(finalTask, "PTR 核对已完成");
      onComplete(finalTask, result);
    } catch (uploadError) {
      if (!isActiveRun(runId)) return;
      const rawError = lastTaskRef.current?.error_message ?? (uploadError instanceof Error ? uploadError.message : "PTR 核对失败");
      if (lastTaskRef.current) rememberTask(lastTaskRef.current, "PTR 核对失败", rawError);
      showTaskError(rawError);
    } finally {
      if (isActiveRun(runId)) setBusy(false);
    }
  }

  function resetForReupload() {
    activeRunIdRef.current += 1;
    clearTaskSession("ptr_compare");
    lastTaskRef.current = null;
    setTask(null);
    setFiles([]);
    setMessage("上传并创建任务");
    clearError();
    setBusy(false);
  }

  function rememberTask(nextTask: TaskStatus, nextMessage: string, nextError: string | null = null) {
    lastTaskRef.current = nextTask;
    setTask(nextTask);
    setMessage(nextMessage);
    saveTaskSession("ptr_compare", nextTask, { message: nextMessage, error: nextError });
  }

  function clearError() {
    setError(null);
    setErrorDetail(null);
  }

  function showTaskError(rawError: string) {
    const formatted = formatCodexRuntimeError(rawError, "ptr_compare");
    setError(formatted.message);
    setErrorDetail(formatted.detail ?? null);
  }

  return (
    <>
      <section className="form-panel">
        <header className="page-header compact">
          <div>
            <p className="eyebrow">PTR COMPARE</p>
            <h1>PTR 条款核对</h1>
            <p className="muted">上传 PTR PDF 与检验报告 PDF，前端仅展示后端返回的结果和证据。</p>
          </div>
        </header>

        <GlassCard className="upload-card">
          <FileUpload
            disabled={busy}
            labels={{
              primary: "上传 PTR PDF",
              secondary: "上传检验报告 PDF",
            }}
            mode="double"
            onFilesChange={setFiles}
          />
          <details className="advanced-audit-settings">
            <summary>高级审核设置</summary>
            <div className="advanced-audit-grid">
              <CodexModelSelector
                disabled={busy}
                onChange={(runtimeOptions) =>
                  setAuditOptions((value) => ({ ...value, ...runtimeOptions }))
                }
                value={auditOptions}
              />
              <label>
                <span>包含规则</span>
                <input
                  disabled={busy}
                  onChange={(event) => setAuditOptions((value) => ({ ...value, included_check_ids: event.target.value }))}
                  placeholder="PTR_TABLE"
                  value={auditOptions.included_check_ids}
                />
              </label>
              <label>
                <span>包含代码</span>
                <input
                  disabled={busy}
                  onChange={(event) =>
                    setAuditOptions((value) => ({ ...value, included_finding_codes: event.target.value }))
                  }
                  placeholder="PTR_TABLE_VALUE_MISMATCH"
                  value={auditOptions.included_finding_codes}
                />
              </label>
              <label>
                <span>排除规则</span>
                <input
                  disabled={busy}
                  onChange={(event) => setAuditOptions((value) => ({ ...value, excluded_check_ids: event.target.value }))}
                  placeholder="PTR_SCOPE"
                  value={auditOptions.excluded_check_ids}
                />
              </label>
              <label>
                <span>Batch</span>
                <input
                  disabled={busy}
                  min={1}
                  onChange={(event) =>
                    setAuditOptions((value) => ({
                      ...value,
                      profile: "custom",
                      max_targets_per_batch: event.target.value,
                    }))
                  }
                  placeholder="3"
                  type="number"
                  value={auditOptions.max_targets_per_batch}
                />
              </label>
              <label>
                <span>并发</span>
                <input
                  disabled={busy}
                  min={1}
                  onChange={(event) =>
                    setAuditOptions((value) => ({
                      ...value,
                      profile: "custom",
                      max_parallel_jobs: event.target.value,
                    }))
                  }
                  placeholder="2"
                  type="number"
                  value={auditOptions.max_parallel_jobs}
                />
              </label>
              <label>
                <span>超时（秒）</span>
                <input
                  disabled={busy}
                  min={1}
                  onChange={(event) =>
                    setAuditOptions((value) => ({
                      ...value,
                      profile: "custom",
                      timeout_seconds: event.target.value,
                    }))
                  }
                  placeholder="600"
                  type="number"
                  value={auditOptions.timeout_seconds}
                />
              </label>
            </div>
          </details>
          {error ? <p className="form-error">{error}</p> : null}
          {errorDetail ? (
            <details className="advanced-audit-settings">
              <summary>高级详情</summary>
              <pre>{errorDetail}</pre>
            </details>
          ) : null}
          <div className="button-row">
            <Button disabled={busy} onClick={onBack} variant="secondary">
              返回
            </Button>
            <Button disabled={busy || files.length < 2} onClick={handleUpload}>
              {busy ? "处理中..." : "开始核对"}
            </Button>
          </div>
        </GlassCard>
      </section>

      <ProgressOverlay
        error={error}
        message={message}
        onReset={resetForReupload}
        resetLabel="重新上传"
        task={task}
        visible={busy}
      />
    </>
  );
}

function compactAuditOptions(value: {
  profile: string;
  included_check_ids: string;
  included_finding_codes: string;
  excluded_check_ids: string;
  max_targets_per_batch: string;
  max_parallel_jobs: string;
  timeout_seconds: string;
  model: string;
  reasoning_effort: string;
}): AuditOptions | undefined {
  const options: AuditOptions = {};
  if (value.profile.trim()) options.profile = value.profile.trim();
  if (value.included_check_ids.trim()) options.included_check_ids = value.included_check_ids.trim();
  if (value.included_finding_codes.trim()) options.included_finding_codes = value.included_finding_codes.trim();
  if (value.excluded_check_ids.trim()) options.excluded_check_ids = value.excluded_check_ids.trim();
  const batch = positiveNumber(value.max_targets_per_batch);
  const parallel = positiveNumber(value.max_parallel_jobs);
  const timeout = positiveNumber(value.timeout_seconds);
  if (batch !== undefined) options.max_targets_per_batch = batch;
  if (parallel !== undefined) options.max_parallel_jobs = parallel;
  if (timeout !== undefined) options.timeout_seconds = timeout;
  if (value.model.trim()) options.model = value.model.trim();
  if (isReasoningEffort(value.reasoning_effort)) options.reasoning_effort = value.reasoning_effort;
  return Object.keys(options).length > 0 ? options : undefined;
}

function positiveNumber(value: string): number | undefined {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function isReasoningEffort(value: string): value is NonNullable<AuditOptions["reasoning_effort"]> {
  return ["low", "medium", "high", "xhigh", "max"].includes(value);
}
