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
        ["fail_count", summary["fail_count"]],
        ["review_count", summary["review_count"]],
        ["skip_count", summary["skip_count"]],
        ["system_error_count", summary["system_error_count"]],
        ["error_count", summary["error_count"]],
        ["warn_count", summary["warn_count"]],
        ["info_count", summary["info_count"]],
        ["diagnostics", " | ".join(payload["diagnostics"])],
    ]


def _check_result_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["check_id", "check_name", "status", "severity", "summary", "finding_count"]]
    for result in payload["check_results"]:
        rows.append(
            [
                result["check_id"],
                result["check_name"],
                result["status"],
                result.get("severity") or "",
                result.get("summary") or "",
                len(result.get("findings") or []),
            ]
        )
    return rows


def _finding_rows(payload: dict[str, Any]) -> list[list[Any]]:
    rows = [["finding_id", "check_id", "severity", "code", "message", "expected", "actual", "page"]]
    for finding in payload["findings"]:
        location = finding.get("location") or {}
        if not location:
            evidence = finding.get("evidence") or []
            location = (evidence[0].get("location") or {}) if evidence else {}
        rows.append(
            [
                finding["id"],
                finding["check_id"],
                finding["severity"],
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
