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
