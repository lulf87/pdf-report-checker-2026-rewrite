from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from app.domain.result import CheckResult
from app.infrastructure.export.common import build_export_payload


def export_check_results_to_json(
    results: Sequence[CheckResult],
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    input_files: Sequence[str] | None = None,
    diagnostics: Sequence[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bytes:
    payload = build_export_payload(
        results,
        task_id=task_id,
        task_type=task_type,
        input_files=input_files,
        diagnostics=diagnostics,
        metadata=metadata,
    )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


__all__ = ["export_check_results_to_json"]
