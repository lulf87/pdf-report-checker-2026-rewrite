from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckContext:
    task_id: str = "local"


__all__ = ["CheckContext"]
