from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.finding import Finding


DEFAULT_CODEX_AUDIT_MAX_TARGETS = 5
DEFAULT_REPORT_PRIORITY_CHECK_IDS = ("C02", "C03", "C07", "C04", "C05", "C06")
DEFAULT_PTR_PRIORITY_FINDING_CODES = (
    "PTR_CLAUSE_TEXT_MISMATCH",
    "PTR_TABLE_CANDIDATE_AMBIGUOUS",
    "PTR_TABLE_VALUE_MISMATCH",
    "PTR_TABLE_UNIT_MISMATCH",
    "PTR_TABLE_PARAM_MISSING",
    "PTR_TABLE_CONDITION_MISMATCH",
    "PTR_TABLE_TOLERANCE_MISMATCH",
)


@dataclass(frozen=True)
class CodexAuditTargetSelection:
    max_targets_per_task: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS
    max_targets_per_batch: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS
    included_check_ids: frozenset[str] = frozenset()
    included_finding_codes: frozenset[str] = frozenset()
    excluded_check_ids: frozenset[str] = frozenset()
    priority_check_ids: tuple[str, ...] = DEFAULT_REPORT_PRIORITY_CHECK_IDS

    @classmethod
    def from_raw(
        cls,
        *,
        max_targets_per_task: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        max_targets_per_batch: int = DEFAULT_CODEX_AUDIT_MAX_TARGETS,
        included_check_ids: str | Iterable[str] | None = None,
        included_finding_codes: str | Iterable[str] | None = None,
        excluded_check_ids: str | Iterable[str] | None = None,
        priority_check_ids: str | Iterable[str] | None = DEFAULT_REPORT_PRIORITY_CHECK_IDS,
    ) -> "CodexAuditTargetSelection":
        return cls(
            max_targets_per_task=max_targets_per_task,
            max_targets_per_batch=max_targets_per_batch,
            included_check_ids=frozenset(parse_csv_values(included_check_ids)),
            included_finding_codes=frozenset(parse_csv_values(included_finding_codes)),
            excluded_check_ids=frozenset(parse_csv_values(excluded_check_ids)),
            priority_check_ids=tuple(parse_csv_values(priority_check_ids)),
        )

    def effective_limit(self, *, override: int | None = None) -> int:
        limits = [self.max_targets_per_task, self.max_targets_per_batch]
        if override is not None:
            limits.append(override)
        if any(limit <= 0 for limit in limits):
            return 0
        return min(limits)

    def allows(self, finding: Finding) -> bool:
        if self.included_check_ids and finding.check_id not in self.included_check_ids:
            return False
        if self.excluded_check_ids and finding.check_id in self.excluded_check_ids:
            return False
        if self.included_finding_codes and finding.code not in self.included_finding_codes:
            return False
        return True

    def selection_metadata(
        self,
        *,
        total_candidate_targets: int,
        emitted_targets: int,
        target_offset: int = 0,
    ) -> dict[str, object]:
        omitted = max(0, total_candidate_targets - target_offset - emitted_targets)
        batch_limit = self.max_targets_per_batch if self.max_targets_per_batch > 0 else 1
        return {
            "total_candidate_targets": total_candidate_targets,
            "emitted_targets": emitted_targets,
            "truncated": omitted > 0,
            "omitted_targets_count": omitted,
            "target_offset": target_offset,
            "batch_index": target_offset // batch_limit,
            "batch_size": emitted_targets,
            "max_targets_per_task": self.max_targets_per_task,
            "max_targets_per_batch": self.max_targets_per_batch,
        }


def parse_csv_values(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values = value.split(",")
    else:
        raw_values = [str(item) for item in value]
    return tuple(item.strip() for item in raw_values if item and item.strip())


def priority_index(values: Iterable[str]) -> dict[str, int]:
    return {value: index for index, value in enumerate(values)}


__all__ = [
    "CodexAuditTargetSelection",
    "DEFAULT_CODEX_AUDIT_MAX_TARGETS",
    "DEFAULT_PTR_PRIORITY_FINDING_CODES",
    "DEFAULT_REPORT_PRIORITY_CHECK_IDS",
    "parse_csv_values",
    "priority_index",
]
