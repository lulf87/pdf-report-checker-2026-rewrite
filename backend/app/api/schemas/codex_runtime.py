from __future__ import annotations

from pydantic import BaseModel, Field


class CodexRuntimeProfileResponse(BaseModel):
    profile_id: str
    label: str
    model: str | None = None
    reasoning_effort: str | None = None
    timeout_seconds: int | None = None
    max_targets_per_batch: int | None = None
    max_parallel_jobs: int | None = None


class CodexRuntimeConfigResponse(BaseModel):
    default_model: str | None = None
    model_options: list[str] = Field(default_factory=list)
    default_reasoning_effort: str
    reasoning_effort_options: list[str] = Field(default_factory=list)
    default_profile: str
    profiles: list[CodexRuntimeProfileResponse] = Field(default_factory=list)
    runtime_config_version: str


__all__ = ["CodexRuntimeConfigResponse", "CodexRuntimeProfileResponse"]
