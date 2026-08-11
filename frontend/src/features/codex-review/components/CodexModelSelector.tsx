import { useEffect, useState } from "react";

import type {
  CodexReasoningEffort,
  CodexRuntimeConfig,
  CodexRuntimeProfile,
} from "../../../entities/task/types";
import { getCodexRuntimeConfig } from "../api";


const CUSTOM_MODEL = "__custom__";
const FALLBACK_PROFILES: CodexRuntimeProfile[] = [
  {
    profile_id: "balanced",
    label: "平衡",
    model: "gpt-5.6-terra",
    reasoning_effort: "medium",
    timeout_seconds: 600,
    max_targets_per_batch: 3,
    max_parallel_jobs: 2,
  },
  {
    profile_id: "fast",
    label: "快速",
    model: "gpt-5.6-luna",
    reasoning_effort: "low",
    timeout_seconds: 360,
    max_targets_per_batch: 5,
    max_parallel_jobs: 2,
  },
  {
    profile_id: "deep",
    label: "深度",
    model: "gpt-5.6-sol",
    reasoning_effort: "high",
    timeout_seconds: 900,
    max_targets_per_batch: 2,
    max_parallel_jobs: 1,
  },
  {
    profile_id: "custom",
    label: "自定义",
    model: null,
    reasoning_effort: null,
    timeout_seconds: null,
    max_targets_per_batch: null,
    max_parallel_jobs: null,
  },
];
const FALLBACK_CONFIG: CodexRuntimeConfig = {
  default_model: "gpt-5.6-terra",
  model_options: ["gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.6-sol"],
  default_reasoning_effort: "medium",
  reasoning_effort_options: ["low", "medium", "high", "xhigh", "max"],
  default_profile: "balanced",
  profiles: FALLBACK_PROFILES,
  runtime_config_version: "codex-runtime-v2",
};

export interface CodexRuntimeFormSelection {
  profile: string;
  model: string;
  reasoning_effort: string;
  max_targets_per_batch: string;
  max_parallel_jobs: string;
  timeout_seconds: string;
}

export const DEFAULT_CODEX_RUNTIME_SELECTION: CodexRuntimeFormSelection = {
  profile: "balanced",
  model: "gpt-5.6-terra",
  reasoning_effort: "medium",
  max_targets_per_batch: "3",
  max_parallel_jobs: "2",
  timeout_seconds: "600",
};

export interface CodexModelSelectorProps {
  value: CodexRuntimeFormSelection;
  onChange: (selection: CodexRuntimeFormSelection) => void;
  disabled?: boolean;
}

export function CodexModelSelector({ value, onChange, disabled = false }: CodexModelSelectorProps) {
  const [config, setConfig] = useState<CodexRuntimeConfig>(FALLBACK_CONFIG);
  const [modelMode, setModelMode] = useState(
    FALLBACK_CONFIG.model_options.includes(value.model) ? value.model : CUSTOM_MODEL,
  );

  useEffect(() => {
    let cancelled = false;
    getCodexRuntimeConfig()
      .then((nextConfig) => {
        if (cancelled) return;
        setConfig(nextConfig);
        setModelMode(nextConfig.model_options.includes(value.model) ? value.model : CUSTOM_MODEL);
      })
      .catch(() => {
        if (!cancelled) setConfig(FALLBACK_CONFIG);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleProfileChange(profileId: string) {
    const profile = config.profiles.find((item) => item.profile_id === profileId);
    if (!profile || profile.profile_id === "custom") {
      onChange({ ...value, profile: "custom" });
      return;
    }
    const nextModel = profile.model ?? value.model;
    setModelMode(config.model_options.includes(nextModel) ? nextModel : CUSTOM_MODEL);
    onChange({
      profile: profile.profile_id,
      model: nextModel,
      reasoning_effort: profile.reasoning_effort ?? value.reasoning_effort,
      max_targets_per_batch: numberText(profile.max_targets_per_batch),
      max_parallel_jobs: numberText(profile.max_parallel_jobs),
      timeout_seconds: numberText(profile.timeout_seconds),
    });
  }

  function handleModelModeChange(nextMode: string) {
    setModelMode(nextMode);
    if (nextMode === CUSTOM_MODEL) {
      onChange({ ...value, profile: "custom" });
      return;
    }
    onChange({ ...value, profile: "custom", model: nextMode });
  }

  function handleCustomModelChange(nextModel: string) {
    onChange({ ...value, profile: "custom", model: nextModel });
  }

  function handleReasoningEffortChange(nextEffort: CodexReasoningEffort) {
    onChange({ ...value, profile: "custom", reasoning_effort: nextEffort });
  }

  return (
    <>
      <label>
        <span>审核方案</span>
        <select
          disabled={disabled}
          onChange={(event) => handleProfileChange(event.target.value)}
          value={value.profile}
        >
          {config.profiles.map((profile) => (
            <option key={profile.profile_id} value={profile.profile_id}>
              {profile.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Codex 模型</span>
        <select
          disabled={disabled}
          onChange={(event) => handleModelModeChange(event.target.value)}
          value={modelMode}
        >
          {config.model_options.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
          <option value={CUSTOM_MODEL}>自定义模型</option>
        </select>
      </label>
      {modelMode === CUSTOM_MODEL ? (
        <label>
          <span>自定义模型 ID</span>
          <input
            autoComplete="off"
            disabled={disabled}
            maxLength={128}
            onChange={(event) => handleCustomModelChange(event.target.value)}
            pattern="[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}"
            placeholder="gpt-5.6-terra"
            spellCheck={false}
            value={value.model}
          />
        </label>
      ) : null}
      <label>
        <span>推理强度</span>
        <select
          disabled={disabled}
          onChange={(event) => handleReasoningEffortChange(event.target.value as CodexReasoningEffort)}
          value={value.reasoning_effort}
        >
          {config.reasoning_effort_options.map((effort) => (
            <option key={effort} value={effort}>
              {reasoningEffortLabel(effort)}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}

function numberText(value: number | null): string {
  return value === null ? "" : String(value);
}

function reasoningEffortLabel(value: CodexReasoningEffort): string {
  const labels: Record<CodexReasoningEffort, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    xhigh: "XHigh（疑难单项）",
    max: "Max（疑难单项）",
  };
  return labels[value];
}
