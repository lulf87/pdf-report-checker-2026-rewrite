from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME = "codex_review_output.schema.json"


def get_codex_review_output_schema_path() -> Path:
    return Path(__file__).with_name(CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME)


def load_codex_review_output_schema() -> dict[str, Any]:
    schema_path = get_codex_review_output_schema_path()
    return json.loads(schema_path.read_text(encoding="utf-8"))


__all__ = [
    "CODEX_REVIEW_OUTPUT_SCHEMA_FILENAME",
    "get_codex_review_output_schema_path",
    "load_codex_review_output_schema",
]
