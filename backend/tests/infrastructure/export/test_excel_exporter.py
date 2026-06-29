import io
from xml.etree import ElementTree
from zipfile import ZipFile

from app.infrastructure.export.excel_exporter import export_check_results_to_xlsx
from tests.fixtures.export_result_builder import sample_check_results


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _workbook_sheet_names(xlsx_bytes: bytes) -> list[str]:
    with ZipFile(io.BytesIO(xlsx_bytes)) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    return [sheet.attrib["name"] for sheet in workbook.findall("main:sheets/main:sheet", NS)]


def _worksheet_text(xlsx_bytes: bytes, sheet_path: str) -> str:
    with ZipFile(io.BytesIO(xlsx_bytes)) as archive:
        xml = ElementTree.fromstring(archive.read(sheet_path))
    return "\n".join(node.text or "" for node in xml.iter())


def test_excel_exporter_creates_summary_and_findings_sheets() -> None:
    xlsx_bytes = export_check_results_to_xlsx(
        sample_check_results(task_id="task-xlsx"),
        task_id="task-xlsx",
        task_type="ptr_compare",
        input_files=["ptr.pdf", "report.pdf"],
    )

    assert xlsx_bytes[:2] == b"PK"
    assert _workbook_sheet_names(xlsx_bytes) == ["Summary", "CheckResults", "Findings", "Evidence"]
    summary_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet1.xml")
    findings_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet3.xml")

    assert "task-xlsx" in summary_text
    assert "ptr_compare" in summary_text
    assert "candidate_errors_count" in summary_text
    assert "confirmed_errors_count" in summary_text
    assert "legacy_fail_count" in summary_text
    assert "legacy_error_count" in summary_text
    assert "C01_FIELD_MISMATCH" in findings_text
    assert "candidate_issue" in findings_text
    assert "ABC-1" in findings_text
    assert "ABC-2" in findings_text


def test_excel_exporter_handles_empty_results() -> None:
    xlsx_bytes = export_check_results_to_xlsx([], task_id="task-empty")

    assert xlsx_bytes[:2] == b"PK"
    assert _workbook_sheet_names(xlsx_bytes) == ["Summary", "CheckResults", "Findings", "Evidence"]
