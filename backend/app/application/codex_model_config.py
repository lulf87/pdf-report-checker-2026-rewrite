from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re
from typing import Any


CODEX_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
CODEX_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
CODEX_RUNTIME_CONFIG_VERSION = "codex-runtime-v2"


@dataclass(frozen=True)
class CodexRuntimeProfile:
    profile_id: str
    model: str | None
    reasoning_effort: str | None
    timeout_seconds: int | None
    max_targets_per_batch: int | None
    max_parallel_jobs: int | None


CODEX_RUNTIME_PROFILES = (
    CodexRuntimeProfile(
        profile_id="balanced",
        model="gpt-5.6-terra",
        reasoning_effort="medium",
        timeout_seconds=600,
        max_targets_per_batch=3,
        max_parallel_jobs=2,
    ),
    CodexRuntimeProfile(
        profile_id="fast",
        model="gpt-5.6-luna",
        reasoning_effort="low",
        timeout_seconds=360,
        max_targets_per_batch=5,
        max_parallel_jobs=2,
    ),
    CodexRuntimeProfile(
        profile_id="deep",
        model="gpt-5.6-sol",
        reasoning_effort="high",
        timeout_seconds=900,
        max_targets_per_batch=2,
        max_parallel_jobs=1,
    ),
    CodexRuntimeProfile(
        profile_id="custom",
        model=None,
        reasoning_effort=None,
        timeout_seconds=None,
        max_targets_per_batch=None,
        max_parallel_jobs=None,
    ),
)
_CODEX_RUNTIME_PROFILES_BY_ID = {profile.profile_id: profile for profile in CODEX_RUNTIME_PROFILES}


def normalize_codex_model(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if CODEX_MODEL_PATTERN.fullmatch(text) is None:
        raise ValueError(
            "Codex model must be 1-128 ASCII characters using letters, numbers, '.', '_', '-', '/', or ':'."
        )
    return text


def parse_codex_model_options(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    raw_values: Iterable[Any]
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, Iterable):
        raw_values = value
    else:
        raw_values = (value,)

    result: list[str] = []
    for raw_value in raw_values:
        model = normalize_codex_model(raw_value)
        if model and model not in result:
            result.append(model)
    return tuple(result)


def normalize_codex_reasoning_effort(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text not in CODEX_REASONING_EFFORTS:
        allowed = ", ".join(CODEX_REASONING_EFFORTS)
        raise ValueError(f"Codex reasoning effort must be one of: {allowed}.")
    return text


def parse_codex_reasoning_effort_options(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    raw_values: Iterable[Any]
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, Iterable):
        raw_values = value
    else:
        raw_values = (value,)

    result: list[str] = []
    for raw_value in raw_values:
        effort = normalize_codex_reasoning_effort(raw_value)
        if effort and effort not in result:
            result.append(effort)
    return tuple(result)


def normalize_codex_profile(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text not in _CODEX_RUNTIME_PROFILES_BY_ID:
        allowed = ", ".join(_CODEX_RUNTIME_PROFILES_BY_ID)
        raise ValueError(f"Codex runtime profile must be one of: {allowed}.")
    return text


def get_codex_runtime_profile(profile_id: str | None) -> CodexRuntimeProfile | None:
    return _CODEX_RUNTIME_PROFILES_BY_ID.get(profile_id or "")


__all__ = [
    "CODEX_REASONING_EFFORTS",
    "CODEX_RUNTIME_CONFIG_VERSION",
    "CODEX_RUNTIME_PROFILES",
    "CodexRuntimeProfile",
    "get_codex_runtime_profile",
    "normalize_codex_model",
    "normalize_codex_profile",
    "normalize_codex_reasoning_effort",
    "parse_codex_model_options",
    "parse_codex_reasoning_effort_options",
]
