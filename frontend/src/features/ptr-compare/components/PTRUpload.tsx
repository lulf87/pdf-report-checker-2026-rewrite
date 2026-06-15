import { useState } from "react";

import type { TaskResult, TaskStatus } from "../../../entities/task/types";
import { Button } from "../../../shared/ui/Button";
import { FileUpload, type FileUploadFile } from "../../../shared/ui/FileUpload";
import { GlassCard } from "../../../shared/ui/GlassCard";
import { ProgressOverlay } from "../../../shared/ui/ProgressOverlay";
import { getPTRCompareResult, getPTRCompareTask, uploadPTRCompareFiles, waitForPTRCompareResult } from "../api";

export interface PTRUploadProps {
  onComplete: (task: TaskStatus, result: TaskResult) => void;
  onBack: () => void;
}

export function PTRUpload({ onComplete, onBack }: PTRUploadProps) {
  const [files, setFiles] = useState<FileUploadFile[]>([]);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [message, setMessage] = useState<string>("上传并创建任务");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      const createdTask = await uploadPTRCompareFiles(ptrFile, reportFile);
      setTask(createdTask);
      const result =
        createdTask.status === "completed"
          ? await getPTRCompareResult(createdTask.task_id)
          : await waitForPTRCompareResult(createdTask.task_id, setTask);
      const finalTask = createdTask.status === "completed" ? createdTask : await getPTRCompareTask(createdTask.task_id);
      onComplete(finalTask, result);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "PTR 核对失败");
    } finally {
      setBusy(false);
    }
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
