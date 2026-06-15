import { useState } from "react";

import type { TaskResult, TaskStatus } from "../../../entities/task/types";
import { Button } from "../../../shared/ui/Button";
import { FileUpload, type FileUploadFile } from "../../../shared/ui/FileUpload";
import { GlassCard } from "../../../shared/ui/GlassCard";
import { ProgressOverlay } from "../../../shared/ui/ProgressOverlay";
import { getReportCheckResult, getReportCheckTask, uploadReportCheckFile, waitForReportCheckResult } from "../api";

export interface ReportUploadProps {
  onComplete: (task: TaskStatus, result: TaskResult) => void;
  onBack: () => void;
}

export function ReportUpload({ onComplete, onBack }: ReportUploadProps) {
  const [files, setFiles] = useState<FileUploadFile[]>([]);
  const [enableLlm, setEnableLlm] = useState(false);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [message, setMessage] = useState("上传并创建任务");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleUpload() {
    const reportFile = files[0]?.file;
    if (!reportFile) {
      setError("请先上传检验报告 PDF");
      return;
    }

    setBusy(true);
    setError(null);
    setMessage("正在上传文件...");

    try {
      const createdTask = await uploadReportCheckFile(reportFile, { enableLlm });
      setTask(createdTask);
      const result =
        createdTask.status === "completed"
          ? await getReportCheckResult(createdTask.task_id)
          : await waitForReportCheckResult(createdTask.task_id, setTask);
      const finalTask = createdTask.status === "completed" ? createdTask : await getReportCheckTask(createdTask.task_id);
      onComplete(finalTask, result);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "报告自检失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="form-panel">
        <header className="page-header compact">
          <div>
            <p className="eyebrow">REPORT CHECK</p>
            <h1>报告自身核对</h1>
            <p className="muted">上传检验报告 PDF，页面只展示后端 C01-C11 输出。</p>
          </div>
        </header>

        <GlassCard className="upload-card">
          <FileUpload
            disabled={busy}
            labels={{ primary: "上传检验报告 PDF" }}
            mode="single"
            onFilesChange={setFiles}
          />
          <label className="toggle-row">
            <input
              checked={enableLlm}
              disabled={busy}
              onChange={(event) => setEnableLlm(event.target.checked)}
              type="checkbox"
            />
            <span>启用 LLM 增强识别</span>
          </label>
          <p className="form-help">该开关只作为上传参数传递，最终核对结论仍以后端规则结果为准。</p>
          {error ? <p className="form-error">{error}</p> : null}
          <div className="button-row">
            <Button disabled={busy} onClick={onBack} variant="secondary">
              返回
            </Button>
            <Button disabled={busy || files.length === 0} onClick={handleUpload}>
              {busy ? "处理中..." : "开始核对"}
            </Button>
          </div>
        </GlassCard>
      </section>

      <ProgressOverlay error={error} message={message} task={task} visible={busy} />
    </>
  );
}
