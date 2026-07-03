from __future__ import annotations

import re
from typing import Any


_LOCAL_PATH_PATTERN = re.compile(r"/Users/[^\s,;，；)）\]]+")


def explanation_details(
    *,
    check_goal: str,
    user_question: str,
    overall_reason: str,
    source_sections: list[dict[str, Any]] | None = None,
    comparison_rows: list[dict[str, Any]] | None = None,
    evidence_groups: list[dict[str, Any]] | None = None,
    decision: dict[str, Any] | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    return _sanitize(
        {
            "check_goal": check_goal,
            "user_question": user_question,
            "overall_reason": overall_reason,
            "source_sections": source_sections or [],
            "comparison_rows": comparison_rows or [],
            "evidence_groups": evidence_groups or [],
            "decision": decision or decision_detail("passed", "通过", overall_reason),
            "next_action": next_action,
        }
    )


def source_section(
    *,
    label: str,
    page_number: int | None = None,
    display_page_label: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "page_number": page_number,
        "display_page_label": display_page_label or display_page(page_number),
        "description": description,
    }


def comparison_row(
    *,
    field: str,
    left_label: str | None = None,
    left_value: Any = None,
    right_label: str | None = None,
    right_value: Any = None,
    status: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "field": field,
        "left_label": left_label,
        "left_value": _value_text(left_value),
        "right_label": right_label,
        "right_value": _value_text(right_value),
        "status": status,
        "reason": reason,
    }


def evidence_group(title: str, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"title": title, "items": items or []}


def evidence_item(
    *,
    label: str,
    page_number: int | None = None,
    evidence_type: str,
    status: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "page_number": page_number,
        "display_page_label": display_page(page_number),
        "evidence_type": evidence_type,
        "status": status,
    }


def decision_detail(user_facing_status: str, label: str, reason: str) -> dict[str, str]:
    return {
        "user_facing_status": user_facing_status,
        "label": label,
        "reason": reason,
    }


def display_page(page_number: int | None) -> str | None:
    if page_number is None:
        return None
    return f"PDF 第 {page_number} 页"


def _value_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set)):
        return "，".join(_value_text(item) or "" for item in value)
    return str(value)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return _LOCAL_PATH_PATTERN.sub("[local path omitted]", value)
    return value
