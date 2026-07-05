from __future__ import annotations

import io
from collections.abc import Sequence
from html import escape
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from app.domain.result import CheckResult
from app.infrastructure.export.common import build_export_payload


def export_check_results_to_xlsx(
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
    sheets = [
        ("Summary", _summary_rows(payload)),
        ("CheckResults", _check_result_rows(payload)),
        ("Findings", _finding_rows(payload)),
        ("Evidence", _evidence_rows(payload)),
        ("ComparisonDetails", _comparison_detail_rows(payload)),
        ("check_explanations", _explanation_detail_rows(payload)),
        ("ptr_comparison_summary", _ptr_comparison_summary_rows(payload)),
        ("ptr_comparison_details", _ptr_comparison_detail_rows(payload)),
    ]

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml([name for name, _ in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(len(sheets)))
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))
    return buffer.getvalue()


def _summary_rows(payload: dict[str, Any]) -> list[list[Any]]:
    task = payload["task"]
    summary = payload["summary"]
    return [
        ["Field", "Value"],
        ["task_id", task.get("task_id") or ""],
        ["task_type", task.get("task_type") or ""],
        ["input_files", ", ".join(task.get("input_files") or [])],
        ["total_checks", summary["total_checks"]],
        ["pass_count", summary["pass_count"]],
        ["review_count", summary["review_count"]],
        ["skip_count", summary["skip_count"]],
        ["system_error_count", summary["system_error_count"]],
        ["candidate_errors_count", summary["candidate_errors_count"]],
        ["confirmed_errors_count", summary["confirmed_errors_count"]],
        ["manual_review_required_count", summary["manual_review_required_count"]],
        ["refuted_findings_count", summary["refuted_findings_count"]],
        ["legacy_fail_count", summary["fail_count"]],
        ["legacy_error_count", summary["error_count"]],
        ["legacy_warn_count", summary["warn_count"]],
        ["info_count", summary["info_count"]],
        ["diagnostics", " | ".join(payload["diagnostics"])],
    ]


def _check_result_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["check_id", "check_name", "user_facing_status", "deterministic_status", "severity", "summary", "finding_count"]]
    for result in payload["check_results"]:
        metadata = result.get("metadata") or {}
        rows.append(
            [
                result["check_id"],
                result["check_name"],
                metadata.get("user_facing_status") or "",
                result["status"],
                result.get("severity") or "",
                result.get("summary") or "",
                len(result.get("findings") or []),
            ]
        )
    return rows


def _finding_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["finding_id", "check_id", "severity", "user_facing_status", "code", "message", "expected", "actual", "page"]]
    for finding in payload["findings"]:
        location = finding.get("location") or {}
        if not location:
            evidence = finding.get("evidence") or []
            location = (evidence[0].get("location") or {}) if evidence else {}
        metadata = finding.get("metadata") or {}
        rows.append(
            [
                finding["id"],
                finding["check_id"],
                finding["severity"],
                metadata.get("user_facing_status") or "",
                finding["code"],
                finding["message"],
                _cell_value(finding.get("expected")),
                _cell_value(finding.get("actual")),
                location.get("page_number") or "",
            ]
        )
    return rows


def _evidence_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["evidence_id", "source_type", "page", "raw_text", "value", "method"]]
    for evidence in payload["evidence"]:
        location = evidence.get("location") or {}
        rows.append(
            [
                evidence["id"],
                evidence["source_type"],
                location.get("page_number") or "",
                evidence.get("raw_text") or "",
                evidence.get("value") or "",
                evidence.get("method") or "",
            ]
        )
    return rows


def _comparison_detail_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [
        [
            "check_id",
            "field_label",
            "left_source",
            "left_page",
            "left_text",
            "right_source",
            "right_page",
            "right_text",
            "status",
            "reason",
        ]
    ]
    for result in payload["check_results"]:
        details = (result.get("metadata") or {}).get("comparison_details")
        if not isinstance(details, dict):
            continue
        fields = details.get("fields") or []
        if not isinstance(fields, list):
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            left = field.get("left") if isinstance(field.get("left"), dict) else {}
            right = field.get("right") if isinstance(field.get("right"), dict) else {}
            rows.append(
                [
                    result["check_id"],
                    field.get("field_label") or "",
                    left.get("label") or left.get("source_key") or "",
                    left.get("display_page_label") or left.get("page_number") or "",
                    left.get("raw_text") or left.get("normalized_text") or "",
                    right.get("label") or right.get("source_key") or "",
                    right.get("display_page_label") or right.get("page_number") or "",
                    right.get("raw_text") or right.get("normalized_text") or "",
                    field.get("status") or "",
                    field.get("reason") or "",
                ]
            )
    return rows


def _explanation_detail_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [
        [
            "check_id",
            "check_name",
            "field",
            "left_label",
            "left_value",
            "right_label",
            "right_value",
            "status",
            "reason",
            "page_numbers",
            "next_action",
        ]
    ]
    for result in payload["check_results"]:
        details = (result.get("metadata") or {}).get("explanation_details")
        if not isinstance(details, dict):
            continue
        page_numbers = _explanation_page_numbers(details)
        rows.append(
            [
                result["check_id"],
                result["check_name"],
                "overall",
                "检查目的",
                details.get("check_goal") or "",
                "判断理由",
                details.get("overall_reason") or "",
                ((details.get("decision") or {}).get("user_facing_status") if isinstance(details.get("decision"), dict) else "")
                or "",
                ((details.get("decision") or {}).get("reason") if isinstance(details.get("decision"), dict) else "")
                or "",
                page_numbers,
                details.get("next_action") or "",
            ]
        )
        comparison_rows = details.get("comparison_rows") or []
        if not isinstance(comparison_rows, list):
            continue
        for row in comparison_rows:
            if not isinstance(row, dict):
                continue
            rows.append(
                [
                    result["check_id"],
                    result["check_name"],
                    row.get("field") or "",
                    row.get("left_label") or "",
                    row.get("left_value") or "",
                    row.get("right_label") or "",
                    row.get("right_value") or "",
                    row.get("status") or "",
                    row.get("reason") or "",
                    page_numbers,
                    details.get("next_action") or "",
                ]
            )
    return rows


def _explanation_page_numbers(details: dict[str, Any]) -> str:
    pages: list[str] = []
    for source in details.get("source_sections") or []:
        if isinstance(source, dict) and source.get("page_number") is not None:
            pages.append(str(source["page_number"]))
    for group in details.get("evidence_groups") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if isinstance(item, dict) and item.get("page_number") is not None:
                pages.append(str(item["page_number"]))
    return ", ".join(dict.fromkeys(pages))


def _ptr_comparison_summary_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["field", "value"]]
    details = _ptr_comparison_details(payload)
    if not isinstance(details, dict):
        return rows
    for key in (
        "overall_status",
        "overall_summary",
        "requirements_count",
        "covered_count",
        "missing_count",
        "mismatch_count",
        "needs_review_count",
        "confirmed_errors_count",
        "manual_review_required_count",
        "refuted_findings_count",
    ):
        rows.append([key, details.get(key) or 0 if key.endswith("_count") else details.get(key) or ""])
    return rows


def _ptr_comparison_detail_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [
        [
            "ptr_clause_id",
            "ptr_title",
            "ptr_page",
            "ptr_requirement_text",
            "report_item_no",
            "report_page",
            "report_standard_clause",
            "report_test_result",
            "report_conclusion",
            "expected",
            "actual",
            "status",
            "reason",
            "user_facing_status",
            "final_status",
        ]
    ]
    details = _ptr_comparison_details(payload)
    if not isinstance(details, dict):
        return rows
    items = details.get("items") or []
    if not isinstance(items, list):
        return rows
    for item in items:
        if not isinstance(item, dict):
            continue
        matches = item.get("report_matches") if isinstance(item.get("report_matches"), list) else []
        if not matches:
            rows.append(_ptr_comparison_detail_row(item, {}))
            continue
        for match in matches:
            if isinstance(match, dict):
                rows.append(_ptr_comparison_detail_row(item, match))
    return rows


def _ptr_comparison_detail_row(item: dict[str, Any], match: dict[str, Any]) -> list[Any]:
    comparison = item.get("normalized_comparison") if isinstance(item.get("normalized_comparison"), dict) else {}
    return [
        item.get("ptr_clause_id") or "",
        item.get("ptr_title") or "",
        item.get("ptr_page") or "",
        item.get("ptr_requirement_text") or "",
        match.get("item_no") or "",
        match.get("report_page") or "",
        match.get("standard_clause") or "",
        match.get("test_result") or "",
        match.get("single_conclusion") or "",
        comparison.get("expected") or "",
        comparison.get("actual") or "",
        comparison.get("status") or "",
        item.get("reason") or "",
        item.get("user_facing_status") or "",
        item.get("final_status") or "",
    ]


def _ptr_comparison_details(payload: dict[str, Any]) -> dict[str, Any] | None:
    metadata = payload.get("metadata") or {}
    details = metadata.get("ptr_comparison_details") if isinstance(metadata, dict) else None
    if isinstance(details, dict):
        return details
    for result in payload.get("check_results") or []:
        if not isinstance(result, dict):
            continue
        result_metadata = result.get("metadata") or {}
        details = result_metadata.get("ptr_comparison_details") if isinstance(result_metadata, dict) else None
        if isinstance(details, dict):
            return details
    return None


def _cell_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _content_types_xml(sheet_count: int) -> str:
    overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  {overrides}
</Types>"""


def _root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "\n".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheets}</sheets>
</workbook>"""


def _workbook_rels_xml(sheet_count: int) -> str:
    rels = "\n".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {rels}
</Relationships>"""


def _worksheet_xml(rows: list[list[Any]]) -> str:
    row_xml = "\n".join(_row_xml(row_index, row) for row_index, row in enumerate(rows, start=1))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{row_xml}</sheetData>
</worksheet>"""


def _row_xml(row_index: int, row: list[Any]) -> str:
    cells = "".join(_cell_xml(row_index, column_index, value) for column_index, value in enumerate(row, start=1))
    return f'<row r="{row_index}">{cells}</row>'


def _cell_xml(row_index: int, column_index: int, value: Any) -> str:
    ref = f"{_column_letter(column_index)}{row_index}"
    text = escape(_cell_value(value))
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


__all__ = ["export_check_results_to_xlsx"]
