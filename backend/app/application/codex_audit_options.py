from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.codex_audit_targeting import parse_csv_values
from app.application.codex_model_config import (
    get_codex_runtime_profile,
    normalize_codex_model,
    normalize_codex_profile,
    normalize_codex_reasoning_effort,
)


@dataclass(frozen=True)
class CodexAuditOptions:
    profile: str | None = None
    included_check_ids: tuple[str, ...] = ()
    included_finding_codes: tuple[str, ...] = ()
    excluded_check_ids: tuple[str, ...] = ()
    max_targets_per_batch: int | None = None
    max_parallel_jobs: int | None = None
    timeout_seconds: int | None = None
    model: str | None = None
    reasoning_effort: str | None = None

    @classmethod
    def from_raw(cls, value: "CodexAuditOptions | dict[str, Any] | None") -> "CodexAuditOptions":
        if isinstance(value, CodexAuditOptions):
            return value
        if not isinstance(value, dict):
            return cls()
        profile_id = normalize_codex_profile(value.get("profile"))
        profile = get_codex_runtime_profile(profile_id)
        return cls(
            profile=profile_id,
            included_check_ids=parse_csv_values(value.get("included_check_ids")),
            included_finding_codes=parse_csv_values(value.get("included_finding_codes")),
            excluded_check_ids=parse_csv_values(value.get("excluded_check_ids")),
            max_targets_per_batch=_positive_int_or_none(value.get("max_targets_per_batch"))
            or (profile.max_targets_per_batch if profile else None),
            max_parallel_jobs=_positive_int_or_none(value.get("max_parallel_jobs"))
            or (profile.max_parallel_jobs if profile else None),
            timeout_seconds=_positive_int_or_none(value.get("timeout_seconds"))
            or (profile.timeout_seconds if profile else None),
            model=normalize_codex_model(value.get("model")) or (profile.model if profile else None),
            reasoning_effort=normalize_codex_reasoning_effort(value.get("reasoning_effort"))
            or (profile.reasoning_effort if profile else None),
        )

    @property
    def has_user_override(self) -> bool:
        return any(
            (
                self.profile is not None,
                self.included_check_ids,
                self.included_finding_codes,
                self.excluded_check_ids,
                self.max_targets_per_batch is not None,
                self.max_parallel_jobs is not None,
                self.timeout_seconds is not None,
                self.model is not None,
                self.reasoning_effort is not None,
            )
        )

    def to_metadata(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "included_check_ids": list(self.included_check_ids),
            "included_finding_codes": list(self.included_finding_codes),
            "excluded_check_ids": list(self.excluded_check_ids),
            "max_targets_per_batch": self.max_targets_per_batch,
            "max_parallel_jobs": self.max_parallel_jobs,
            "timeout_seconds": self.timeout_seconds,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
        }


def compact_audit_options_dict(value: dict[str, Any]) -> dict[str, Any] | None:
    options = CodexAuditOptions.from_raw(value)
    if not options.has_user_override:
        return None
    metadata = options.to_metadata()
    return {key: item for key, item in metadata.items() if item not in (None, [], "")}


def _positive_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


__all__ = ["CodexAuditOptions", "compact_audit_options_dict"]
