"""Golden-file helpers for the rewritten backend.

The old project used this module to call router-level task globals. In the
new architecture it stays under ``app.testing`` and only provides deterministic
normalization plus expected-file inventory utilities for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class GoldenExpectedCase:
    sample_id: str
    kind: str
    expected_json_path: Path


def normalize_result(value: Any) -> Any:
    """Normalize nested values for deterministic golden JSON output."""
    if isinstance(value, BaseModel):
        return normalize_result(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_result(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [normalize_result(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


def collect_expected_cases(expected_root: str | Path) -> list[GoldenExpectedCase]:
    """Collect migrated legacy expected JSON files from a controlled fixture root."""
    root = Path(expected_root)
    if not root.exists():
        return []

    cases: list[GoldenExpectedCase] = []
    expected_names = {
        "report_check.expected.json": "report_check",
        "ptr_compare.expected.json": "ptr_compare",
    }
    for sample_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for file_name, kind in expected_names.items():
            expected_json = sample_dir / file_name
            if expected_json.is_file():
                cases.append(
                    GoldenExpectedCase(
                        sample_id=sample_dir.name,
                        kind=kind,
                        expected_json_path=expected_json,
                    )
                )
    return cases


__all__ = ["GoldenExpectedCase", "collect_expected_cases", "normalize_result"]
