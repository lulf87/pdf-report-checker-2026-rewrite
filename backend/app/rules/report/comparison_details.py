from __future__ import annotations

import re
from typing import Any

from app.domain.report import ReportField
from app.rules.report.common import field_value


_LOCAL_PATH_PATTERN = re.compile(r"/Users/[^\s,;，；)）\]]+")


def comparison_source(
    *,
    source_key: str,
    label: str,
    page_number: int | None = None,
    display_page_label: str | None = None,
    section: str | None = None,
) -> dict[str, Any]:
    return {
        "source_key": source_key,
        "label": label,
        "page_number": page_number,
        "display_page_label": display_page_label or _display_page_label(page_number),
        "section": section,
    }


def field_extract(
    *,
    source_key: str,
    label: str,
    page_number: int | None = None,
    display_page_label: str | None = None,
    raw_text: Any = None,
    normalized_text: Any = None,
) -> dict[str, Any]:
    return {
        "source_key": source_key,
        "label": label,
        "page_number": page_number,
        "display_page_label": display_page_label or _display_page_label(page_number),
        "raw_text": _safe_text(raw_text),
        "normalized_text": _safe_text(normalized_text),
    }


def field_extract_from_report_field(
    field: ReportField | None,
    *,
    source_key: str,
    label: str,
    fallback_page_number: int | None = None,
    display_page_label: str | None = None,
    raw_text: Any = None,
    normalized_text: Any = None,
) -> dict[str, Any]:
    page_number = field.location.page_number if field and field.location else fallback_page_number
    raw = _field_raw_text(field) if raw_text is None else raw_text
    normalized = _field_normalized_text(field) if normalized_text is None else normalized_text
    return field_extract(
        source_key=source_key,
        label=label,
        page_number=page_number,
        display_page_label=display_page_label,
        raw_text=raw,
        normalized_text=normalized,
    )


def comparison_field(
    *,
    field_key: str,
    field_label: str,
    status: str,
    reason: str,
    left: dict[str, Any] | None = None,
    right: dict[str, Any] | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "field_key": field_key,
        "field_label": field_label,
        "status": status,
        "reason": reason,
        "evidence_ids": evidence_ids or [],
    }
    if left is not None:
        data["left"] = left
    if right is not None:
        data["right"] = right
    return data


def evidence_ids_for_fields(*fields: ReportField | None) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for field in fields:
        if field is None:
            continue
        for evidence in field.evidence:
            if evidence.id in seen:
                continue
            seen.add(evidence.id)
            ids.append(evidence.id)
    return ids


def _field_raw_text(field: ReportField | None) -> str | None:
    return _safe_text(field_value(field))


def _field_normalized_text(field: ReportField | None) -> str | None:
    if field is None:
        return None
    return _safe_text(field.normalized_value or field.value or field.raw_value)


def _display_page_label(page_number: int | None) -> str | None:
    if page_number is None:
        return None
    return f"PDF 第 {page_number} 页"


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    return _LOCAL_PATH_PATTERN.sub("[local path omitted]", str(value))
