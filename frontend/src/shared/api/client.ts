import type { ExportFormat, TaskResult, TaskStatus } from "../../entities/task/types";

type UploadField = File | Blob | string | number | boolean | null | undefined;

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(
      options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
    );
    this.fetcher = options.fetcher ?? fetch.bind(globalThis);
  }

  async get<T>(path: string): Promise<T> {
    const response = await this.fetcher(this.url(path), {
      method: "GET",
    });
    return this.parseJson<T>(response);
  }

  async postForm<T>(path: string, fields: Record<string, UploadField>): Promise<T> {
    const formData = new FormData();
    for (const [key, value] of Object.entries(fields)) {
      if (value === null || value === undefined) continue;
      if (value instanceof Blob) {
        formData.append(key, value);
      } else {
        formData.append(key, String(value));
      }
    }

    const response = await this.fetcher(this.url(path), {
      method: "POST",
      body: formData,
    });
    return this.parseJson<T>(response);
  }

  async download(path: string, fallbackFileName: string): Promise<{ blob: Blob; fileName: string }> {
    const response = await this.fetcher(this.url(path), {
      method: "GET",
    });
    if (!response.ok) {
      throw await this.toApiError(response);
    }

    const blob = await response.blob();
    return {
      blob,
      fileName: getFileNameFromDisposition(response.headers.get("Content-Disposition")) ?? fallbackFileName,
    };
  }

  getTaskStatus(taskId: string): Promise<TaskStatus> {
    return this.get<TaskStatus>(`/api/tasks/${encodeURIComponent(taskId)}`);
  }

  getTaskResult(taskId: string): Promise<TaskResult> {
    return this.get<TaskResult>(`/api/tasks/${encodeURIComponent(taskId)}/result`);
  }

  exportTask(taskId: string, format: ExportFormat): Promise<{ blob: Blob; fileName: string }> {
    return this.download(
      `/api/tasks/${encodeURIComponent(taskId)}/export?format=${encodeURIComponent(format)}`,
      `${taskId}.${format}`,
    );
  }

  private url(path: string): string {
    if (/^https?:\/\//.test(path)) return path;
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  private async parseJson<T>(response: Response): Promise<T> {
    if (!response.ok) {
      throw await this.toApiError(response);
    }
    return (await response.json()) as T;
  }

  private async toApiError(response: Response): Promise<ApiError> {
    const detail = await parseErrorDetail(response);
    return new ApiError(detailToMessage(detail, response.status), response.status, detail);
  }
}

export const apiClient = new ApiClient();

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

async function parseErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => response.statusText);
  }
  return response.text().catch(() => response.statusText);
}

function detailToMessage(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (isRecord(detail)) {
    const inner = detail.detail;
    if (typeof inner === "string" && inner.trim()) return inner;
    if (Array.isArray(inner)) {
      const messages = inner
        .map((item) => (isRecord(item) && typeof item.msg === "string" ? item.msg : null))
        .filter((item): item is string => Boolean(item));
      if (messages.length > 0) return messages.join("; ");
    }
  }
  return `Request failed with status ${status}`;
}

function getFileNameFromDisposition(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null;
  const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
  return match?.[1]?.replace(/['"]/g, "").trim() || null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
