from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[3] / "app"
FORBIDDEN_SAMPLE_TOKENS = (
    "1539",
    "0596",
    "2795",
    "4788",
    "5780",
    "QW2025-0596",
    "PM3562",
    "pm3562",
    "QW2025 第1540号",
    "QW2025-1539",
    "QW2025-2795",
    "QW2025-4788",
    "QW2025-5780",
)


def test_production_ptr_compare_code_has_no_sample_identifier_branches() -> None:
    offenders: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_SAMPLE_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(APP_ROOT)} contains {token!r}")

    assert offenders == []
