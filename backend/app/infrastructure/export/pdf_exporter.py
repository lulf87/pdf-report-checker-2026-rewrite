from __future__ import annotations

from collections.abc import Sequence
from textwrap import wrap
from typing import Any

import fitz

from app.domain.result import CheckResult
from app.infrastructure.export.common import build_export_payload


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 44
LINE_HEIGHT = 15


def export_check_results_to_pdf(
    results: Sequence[CheckResult],
    *,
    task_id: str | None = None,
    task_type: str | None = None,
    title: str = "报告核对结果导出",
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
    lines = _payload_to_lines(payload, title)
    document = fitz.open()
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN

    for raw_line in lines:
        for line in _wrap_line(raw_line):
            if y > PAGE_HEIGHT - MARGIN:
                page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
                y = MARGIN
            page.insert_text(
                (MARGIN, y),
                line or " ",
                fontsize=10 if line != title else 15,
                fontname=_font_name_for_line(line),
            )
            y += LINE_HEIGHT if line != title else 22
        if raw_line == "":
            y += 4

    return document.tobytes()


def _payload_to_lines(payload: dict[str, Any], title: str) -> list[str]:
    summary = payload["summary"]
    task = payload["task"]
    lines = [
        title,
        "",
        "Task",
        f"task_id: {task.get('task_id') or ''}",
        f"task_type: {task.get('task_type') or ''}",
        f"input_files: {', '.join(task.get('input_files') or [])}",
        "",
        "Summary",
        f"total_checks: {summary['total_checks']}",
        f"pass_count: {summary['pass_count']}",
        f"review_count: {summary['review_count']}",
        f"candidate_errors_count: {summary['candidate_errors_count']}",
        f"confirmed_errors_count: {summary['confirmed_errors_count']}",
        f"manual_review_required_count: {summary['manual_review_required_count']}",
        f"refuted_findings_count: {summary['refuted_findings_count']}",
        f"legacy_fail_count: {summary['fail_count']}",
        f"legacy_error_count: {summary['error_count']}",
        f"legacy_warn_count: {summary['warn_count']}",
        "",
        "Check Results",
    ]

    for result in payload["check_results"]:
        lines.extend(
            [
                f"check_id: {result['check_id']}",
                f"check_name: {result['check_name']}",
                f"user_facing_status: {((result.get('metadata') or {}).get('user_facing_status')) or ''}",
                f"deterministic_status: {result['status']}",
                f"severity: {result.get('severity') or ''}",
                f"summary: {result.get('summary') or ''}",
            ]
        )
        lines.extend(_comparison_detail_lines(result))

    lines.extend(["", "Findings"])
    if not payload["findings"]:
        lines.append("No findings")
    for finding in payload["findings"]:
        lines.extend(
            [
                f"finding_id: {finding['id']}",
                f"check_id: {finding['check_id']}",
                f"severity: {finding['severity']}",
                f"user_facing_status: {((finding.get('metadata') or {}).get('user_facing_status')) or ''}",
                f"code: {finding['code']}",
                f"message: {finding['message']}",
                f"expected: {_stringify(finding.get('expected'))}",
                f"actual: {_stringify(finding.get('actual'))}",
            ]
        )
        for evidence in finding.get("evidence") or []:
            page = ((evidence.get("location") or {}).get("page_number")) or ""
            lines.extend(
                [
                    f"evidence_id: {evidence.get('id') or ''}",
                    f"evidence_page: {page}",
                    f"evidence_value: {evidence.get('value') or ''}",
                    f"evidence_raw_text: {evidence.get('raw_text') or ''}",
                ]
            )

    if payload["diagnostics"]:
        lines.extend(["", "Diagnostics"])
        lines.extend(str(item) for item in payload["diagnostics"])
    return lines


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _comparison_detail_lines(result: dict[str, Any]) -> list[str]:
    explanation = (result.get("metadata") or {}).get("explanation_details")
    if isinstance(explanation, dict):
        return _explanation_detail_lines(explanation)

    details = (result.get("metadata") or {}).get("comparison_details")
    if not isinstance(details, dict):
        return []

    lines = [
        "核对明细",
        f"detail_title: {details.get('title') or ''}",
        f"overall_status: {details.get('overall_status') or ''}",
        f"通过原因: {details.get('overall_reason') or ''}",
    ]
    fields = details.get("fields") or []
    if not isinstance(fields, list):
        return lines
    for field in fields:
        if not isinstance(field, dict):
            continue
        left = field.get("left") if isinstance(field.get("left"), dict) else {}
        right = field.get("right") if isinstance(field.get("right"), dict) else {}
        lines.append(
            "detail_field: "
            f"{field.get('field_label') or ''} | "
            f"left={_extract_label(left)} {_extract_page(left)} {_extract_text(left)} | "
            f"right={_extract_label(right)} {_extract_page(right)} {_extract_text(right)} | "
            f"status={field.get('status') or ''} | "
            f"reason={field.get('reason') or ''}"
        )
    return lines


def _explanation_detail_lines(details: dict[str, Any]) -> list[str]:
    lines = [
        "核对明细",
        f"检查目的: {details.get('check_goal') or ''}",
        f"用户问题: {details.get('user_question') or ''}",
        f"判断理由: {details.get('overall_reason') or ''}",
    ]
    decision = details.get("decision") if isinstance(details.get("decision"), dict) else {}
    if decision:
        lines.append(
            "decision: "
            f"{decision.get('label') or ''} | "
            f"status={decision.get('user_facing_status') or ''} | "
            f"reason={decision.get('reason') or ''}"
        )
    for source in details.get("source_sections") or []:
        if not isinstance(source, dict):
            continue
        lines.append(
            "source_section: "
            f"{source.get('label') or ''} | "
            f"{source.get('display_page_label') or source.get('page_number') or ''} | "
            f"{source.get('description') or ''}"
        )
    for row in details.get("comparison_rows") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            "detail_field: "
            f"{row.get('field') or ''} | "
            f"left={row.get('left_label') or ''} {row.get('left_value') or ''} | "
            f"right={row.get('right_label') or ''} {row.get('right_value') or ''} | "
            f"status={row.get('status') or ''} | "
            f"reason={row.get('reason') or ''}"
        )
    for group in details.get("evidence_groups") or []:
        if not isinstance(group, dict):
            continue
        lines.append(f"evidence_group: {group.get('title') or ''}")
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            lines.append(
                "evidence_item: "
                f"{item.get('label') or ''} | "
                f"{item.get('display_page_label') or item.get('page_number') or ''} | "
                f"type={item.get('evidence_type') or ''} | "
                f"status={item.get('status') or ''}"
            )
    if details.get("next_action"):
        lines.append(f"下一步建议: {details.get('next_action')}")
    return lines


def _extract_label(value: dict[str, Any]) -> str:
    return str(value.get("label") or "")


def _extract_page(value: dict[str, Any]) -> str:
    return str(value.get("display_page_label") or value.get("page_number") or "")


def _extract_text(value: dict[str, Any]) -> str:
    return str(value.get("raw_text") or value.get("normalized_text") or "")


def _wrap_line(line: str) -> list[str]:
    if line == "":
        return [""]
    chunks: list[str] = []
    for piece in wrap(line, width=86, break_long_words=False, replace_whitespace=False):
        if len(piece) <= 86:
            chunks.append(piece)
        else:
            chunks.extend(piece[index : index + 86] for index in range(0, len(piece), 86))
    return chunks or [line]


def _font_name_for_line(line: str) -> str:
    # PyMuPDF's built-in china-s font keeps Chinese text readable without
    # embedding a platform-specific TTC file; pure ASCII stays more searchable
    # with Helvetica.
    if any(ord(char) > 127 for char in line):
        return "china-s"
    return "helv"


__all__ = ["export_check_results_to_pdf"]
