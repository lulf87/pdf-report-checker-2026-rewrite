import { useEffect, useRef, useState } from "react";

import type { AuditOptions, TaskResult, TaskStatus } from "../../../entities/task/types";
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
    included_check_ids: "",
    included_finding_codes: "",
    excluded_check_ids: "",
    max_targets_per_batch: "",
    max_parallel_jobs: "",
  });
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [message, setMessage] = useState<string>("上传并创建任务");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const didRestoreTask = useRef(false);
  const lastTaskRef = useRef<TaskStatus | null>(null);

  useEffect(() => {
    if (didRestoreTask.current) return;
    didRestoreTask.current = true;

    const storedSession = loadTaskSession("ptr_compare");
    if (!storedSession) return;

    if (storedSession.task.status === "error") {
      lastTaskRef.current = storedSession.task;
      setTask(storedSession.task);
      setMessage(storedSession.message ?? "上次任务失败");
      setError(storedSession.error ?? storedSession.task.error_message ?? "上次 PTR 核对失败");
      return;
    }

    let cancelled = false;
    const restoreTask = async () => {
      setBusy(true);
      setError(null);
      setTask(storedSession.task);
      setMessage("正在恢复上次 PTR 核对任务...");

      try {
        const latestTask = await getPTRCompareTask(storedSession.task.task_id);
        if (cancelled) return;
        rememberTask(latestTask, "正在恢复上次 PTR 核对任务...");

        if (latestTask.status === "error") {
          const nextError = latestTask.error_message || "上次 PTR 核对失败";
          rememberTask(latestTask, "上次任务失败", nextError);
          setError(nextError);
          setBusy(false);
          return;
        }

        const result =
          latestTask.status === "completed"
            ? await getPTRCompareResult(latestTask.task_id)
            : await waitForPTRCompareResult(latestTask.task_id, (nextTask) => {
                if (!cancelled) rememberTask(nextTask, "正在恢复上次 PTR 核对任务...");
              });
        if (cancelled) return;
        const finalTask = latestTask.status === "completed" ? latestTask : await getPTRCompareTask(latestTask.task_id);
        rememberTask(finalTask, "PTR 核对已完成");
        onComplete(finalTask, result);
      } catch (restoreError) {
        if (cancelled) return;
        const nextError = restoreError instanceof Error ? restoreError.message : "无法恢复上次 PTR 核对任务";
        clearRestoredTask(nextError);
      }
    };

    void restoreTask();
    return () => {
      cancelled = true;
    };
  }, []);

  function clearRestoredTask(nextError: string) {
    clearTaskSession("ptr_compare");
    lastTaskRef.current = null;
    setTask(null);
    setMessage("上传并创建任务");
    setError(nextError);
    setBusy(false);
  }

  async function handleUpload() {
    const ptrFile = files[0]?.file;
    const reportFile = files[1]?.file;
    if (!ptrFile || !reportFile) {
      setError("请同时上传 PTR PDF 和检验报告 PDF");
      return;
    }

    setBusy(true);
    setError(null);
    setMessage("正在上传文件...");

    try {
      const createdTask = await uploadPTRCompareFiles(ptrFile, reportFile, compactAuditOptions(auditOptions));
      rememberTask(createdTask, "正在处理 PTR 核对任务...");
      const result =
        createdTask.status === "completed"
          ? await getPTRCompareResult(createdTask.task_id)
          : await waitForPTRCompareResult(createdTask.task_id, (nextTask) =>
              rememberTask(nextTask, "正在处理 PTR 核对任务..."),
            );
      const finalTask = createdTask.status === "completed" ? createdTask : await getPTRCompareTask(createdTask.task_id);
      rememberTask(finalTask, "PTR 核对已完成");
      onComplete(finalTask, result);
    } catch (uploadError) {
      const nextError = uploadError instanceof Error ? uploadError.message : "PTR 核对失败";
      if (lastTaskRef.current) rememberTask(lastTaskRef.current, "PTR 核对失败", nextError);
      setError(nextError);
    } finally {
      setBusy(false);
    }
  }

  function rememberTask(nextTask: TaskStatus, nextMessage: string, nextError: string | null = null) {
    lastTaskRef.current = nextTask;
    setTask(nextTask);
    setMessage(nextMessage);
    saveTaskSession("ptr_compare", nextTask, { message: nextMessage, error: nextError });
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
                    setAuditOptions((value) => ({ ...value, max_targets_per_batch: event.target.value }))
                  }
                  placeholder="5"
                  type="number"
                  value={auditOptions.max_targets_per_batch}
                />
              </label>
              <label>
                <span>并发</span>
                <input
                  disabled={busy}
                  min={1}
                  onChange={(event) => setAuditOptions((value) => ({ ...value, max_parallel_jobs: event.target.value }))}
                  placeholder="1"
                  type="number"
                  value={auditOptions.max_parallel_jobs}
                />
              </label>
            </div>
          </details>
          {error ? <p className="form-error">{error}</p> : null}
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

      <ProgressOverlay error={error} message={message} task={task} visible={busy} />
    </>
  );
}

function compactAuditOptions(value: {
  included_check_ids: string;
  included_finding_codes: string;
  excluded_check_ids: string;
  max_targets_per_batch: string;
  max_parallel_jobs: string;
}): AuditOptions | undefined {
  const options: AuditOptions = {};
  if (value.included_check_ids.trim()) options.included_check_ids = value.included_check_ids.trim();
  if (value.included_finding_codes.trim()) options.included_finding_codes = value.included_finding_codes.trim();
  if (value.excluded_check_ids.trim()) options.excluded_check_ids = value.excluded_check_ids.trim();
  const batch = positiveNumber(value.max_targets_per_batch);
  const parallel = positiveNumber(value.max_parallel_jobs);
  if (batch !== undefined) options.max_targets_per_batch = batch;
  if (parallel !== undefined) options.max_parallel_jobs = parallel;
  return Object.keys(options).length > 0 ? options : undefined;
}

function positiveNumber(value: string): number | undefined {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}
