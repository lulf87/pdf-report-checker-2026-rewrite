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
        f"fail_count: {summary['fail_count']}",
        f"review_count: {summary['review_count']}",
        f"error_count: {summary['error_count']}",
        f"warn_count: {summary['warn_count']}",
        "",
        "Check Results",
    ]

    for result in payload["check_results"]:
        lines.extend(
            [
                f"check_id: {result['check_id']}",
                f"check_name: {result['check_name']}",
                f"status: {result['status']}",
                f"severity: {result.get('severity') or ''}",
                f"summary: {result.get('summary') or ''}",
            ]
        )

    lines.extend(["", "Findings"])
    if not payload["findings"]:
        lines.append("No findings")
    for finding in payload["findings"]:
        lines.extend(
            [
                f"finding_id: {finding['id']}",
                f"check_id: {finding['check_id']}",
                f"severity: {finding['severity']}",
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
