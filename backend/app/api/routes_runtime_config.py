from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.routes_tasks import get_app_settings
from app.api.schemas.codex_runtime import CodexRuntimeConfigResponse, CodexRuntimeProfileResponse
from app.application.codex_model_config import (
    CODEX_RUNTIME_CONFIG_VERSION,
    CODEX_RUNTIME_PROFILES,
    parse_codex_model_options,
    parse_codex_reasoning_effort_options,
)
from app.core.config import Settings


router = APIRouter(prefix="/api/runtime-config", tags=["runtime-config"])


@router.get("/codex", response_model=CodexRuntimeConfigResponse)
def get_codex_runtime_config(
    settings: Settings = Depends(get_app_settings),
) -> CodexRuntimeConfigResponse:
    options = list(parse_codex_model_options(settings.codex_audit_model_options))
    for profile in CODEX_RUNTIME_PROFILES:
        if profile.model and profile.model not in options:
            options.append(profile.model)
    if settings.codex_audit_model:
        options = [settings.codex_audit_model, *[item for item in options if item != settings.codex_audit_model]]
    reasoning_options = list(
        parse_codex_reasoning_effort_options(settings.codex_audit_reasoning_effort_options)
    )
    if settings.codex_audit_reasoning_effort not in reasoning_options:
        reasoning_options.insert(0, settings.codex_audit_reasoning_effort)
    return CodexRuntimeConfigResponse(
        default_model=settings.codex_audit_model,
        model_options=options,
        default_reasoning_effort=settings.codex_audit_reasoning_effort,
        reasoning_effort_options=reasoning_options,
        default_profile=_default_profile_id(settings),
        profiles=[
            CodexRuntimeProfileResponse(
                profile_id=profile.profile_id,
                label=_PROFILE_LABELS[profile.profile_id],
                model=profile.model,
                reasoning_effort=profile.reasoning_effort,
                timeout_seconds=profile.timeout_seconds,
                max_targets_per_batch=profile.max_targets_per_batch,
                max_parallel_jobs=profile.max_parallel_jobs,
            )
            for profile in CODEX_RUNTIME_PROFILES
        ],
        runtime_config_version=CODEX_RUNTIME_CONFIG_VERSION,
    )


_PROFILE_LABELS = {
    "balanced": "平衡",
    "fast": "快速",
    "deep": "深度",
    "custom": "自定义",
}


def _default_profile_id(settings: Settings) -> str:
    for profile in CODEX_RUNTIME_PROFILES:
        if profile.profile_id == "custom":
            continue
        if (
            profile.model == settings.codex_audit_model
            and profile.reasoning_effort == settings.codex_audit_reasoning_effort
            and profile.timeout_seconds == settings.codex_audit_timeout_seconds
            and profile.max_targets_per_batch == settings.codex_audit_max_targets_per_batch
            and profile.max_parallel_jobs == settings.codex_audit_max_parallel_jobs
        ):
            return profile.profile_id
    return "custom"


__all__ = ["router"]
