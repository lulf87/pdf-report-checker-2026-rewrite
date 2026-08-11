import type { CodexRuntimeConfig } from "../../entities/task/types";
import { apiClient } from "../../shared/api/client";


export function getCodexRuntimeConfig(): Promise<CodexRuntimeConfig> {
  return apiClient.get<CodexRuntimeConfig>("/api/runtime-config/codex");
}
