from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.codex_audit_targeting import parse_csv_values


@dataclass(frozen=True)
class CodexAuditOptions:
    included_check_ids: tuple[str, ...] = ()
    included_finding_codes: tuple[str, ...] = ()
    excluded_check_ids: tuple[str, ...] = ()
    max_targets_per_batch: int | None = None
    max_parallel_jobs: int | None = None

    @classmethod
    def from_raw(cls, value: "CodexAuditOptions | dict[str, Any] | None") -> "CodexAuditOptions":
        if isinstance(value, CodexAuditOptions):
            return value
        if not isinstance(value, dict):
            return cls()
        return cls(
            included_check_ids=parse_csv_values(value.get("included_check_ids")),
            included_finding_codes=parse_csv_values(value.get("included_finding_codes")),
            excluded_check_ids=parse_csv_values(value.get("excluded_check_ids")),
            max_targets_per_batch=_positive_int_or_none(value.get("max_targets_per_batch")),
            max_parallel_jobs=_positive_int_or_none(value.get("max_parallel_jobs")),
        )

    @property
    def has_user_override(self) -> bool:
        return any(
            (
                self.included_check_ids,
                self.included_finding_codes,
                self.excluded_check_ids,
                self.max_targets_per_batch is not None,
                self.max_parallel_jobs is not None,
            )
        )

    def to_metadata(self) -> dict[str, Any]:
        return {
            "included_check_ids": list(self.included_check_ids),
            "included_finding_codes": list(self.included_finding_codes),
            "excluded_check_ids": list(self.excluded_check_ids),
            "max_targets_per_batch": self.max_targets_per_batch,
            "max_parallel_jobs": self.max_parallel_jobs,
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
