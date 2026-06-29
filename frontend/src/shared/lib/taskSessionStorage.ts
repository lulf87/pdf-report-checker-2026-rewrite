import type { TaskStatus, TaskType } from "../../entities/task/types";

const SESSION_VERSION = 2;

const SESSION_KEYS: Record<TaskType, string> = {
  ptr_compare: "report-checker:last-ptr-compare-task",
  report_check: "report-checker:last-report-check-task",
};

export interface StoredTaskSession {
  version: typeof SESSION_VERSION;
  taskType: TaskType;
  task: TaskStatus;
  message?: string;
  error?: string | null;
  savedAt: string;
}

export function saveTaskSession(
  taskType: TaskType,
  task: TaskStatus,
  options: { message?: string; error?: string | null } = {},
): void {
  const storage = getLocalStorage();
  if (!storage) return;
  const payload: StoredTaskSession = {
    version: SESSION_VERSION,
    taskType,
    task,
    message: options.message,
    error: options.error,
    savedAt: new Date().toISOString(),
  };
  try {
    storage.setItem(SESSION_KEYS[taskType], JSON.stringify(payload));
  } catch {
    // Storage can fail in private mode or when quota is full; task execution should continue.
  }
}

export function loadTaskSession(taskType: TaskType): StoredTaskSession | null {
  const storage = getLocalStorage();
  if (!storage) return null;
  const key = SESSION_KEYS[taskType];
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredTaskSession>;
    if (!isValidSession(parsed, taskType)) {
      storage.removeItem(key);
      return null;
    }
    return parsed;
  } catch {
    storage.removeItem(key);
    return null;
  }
}

export function clearTaskSession(taskType: TaskType): void {
  const storage = getLocalStorage();
  if (!storage) return;
  try {
    storage.removeItem(SESSION_KEYS[taskType]);
  } catch {
    // Ignore storage cleanup failures; the next successful save will overwrite the snapshot.
  }
}

function isValidSession(value: Partial<StoredTaskSession>, taskType: TaskType): value is StoredTaskSession {
  return (
    value.version === SESSION_VERSION &&
    value.taskType === taskType &&
    typeof value.savedAt === "string" &&
    isTaskStatus(value.task) &&
    value.task.task_type === taskType
  );
}

function isTaskStatus(value: unknown): value is TaskStatus {
  if (!value || typeof value !== "object") return false;
  const task = value as Partial<TaskStatus>;
  return (
    typeof task.task_id === "string" &&
    typeof task.task_type === "string" &&
    typeof task.status === "string" &&
    typeof task.progress === "number" &&
    Array.isArray(task.input_files)
  );
}

function getLocalStorage(): Storage | null {
  try {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}
