from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.result import CheckResult


@dataclass(frozen=True)
class CheckContext:
    task_id: str = "local"
    on_check_start: Callable[[str, str], None] | None = None
    on_check_complete: Callable[[CheckResult], None] | None = None


__all__ = ["CheckContext"]
