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
    assert _workbook_sheet_names(xlsx_bytes) == [
        "Summary",
        "CheckResults",
        "Findings",
        "Evidence",
        "ComparisonDetails",
        "check_explanations",
        "ptr_comparison_summary",
        "ptr_comparison_details",
    ]
    summary_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet1.xml")
    findings_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet3.xml")
    details_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet5.xml")
    explanation_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet6.xml")

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
    assert "field_label" in details_text
    assert "left_source" in details_text
    assert "right_text" in details_text
    assert "两处摘录不一致" in details_text
    assert "check_name" in explanation_text
    assert "left_value" in explanation_text
    assert "next_action" in explanation_text
    assert "核对首页与报告首页字段是否一致" in explanation_text
    assert "查看型号规格两处摘录。" in explanation_text


def test_excel_exporter_handles_empty_results() -> None:
    xlsx_bytes = export_check_results_to_xlsx([], task_id="task-empty")

    assert xlsx_bytes[:2] == b"PK"
    assert _workbook_sheet_names(xlsx_bytes) == [
        "Summary",
        "CheckResults",
        "Findings",
        "Evidence",
        "ComparisonDetails",
        "check_explanations",
        "ptr_comparison_summary",
        "ptr_comparison_details",
    ]


def test_excel_exporter_includes_ptr_comparison_summary_and_details_sheets() -> None:
    xlsx_bytes = export_check_results_to_xlsx(
        sample_check_results(task_id="task-ptr-xlsx"),
        task_id="task-ptr-xlsx",
        task_type="ptr_compare",
        input_files=["ptr.pdf", "report.pdf"],
        metadata={"ptr_comparison_details": _ptr_comparison_details()},
    )

    assert _workbook_sheet_names(xlsx_bytes)[-2:] == ["ptr_comparison_summary", "ptr_comparison_details"]
    summary_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet7.xml")
    details_text = _worksheet_text(xlsx_bytes, "xl/worksheets/sheet8.xml")
    assert "requirements_count" in summary_text
    assert "covered_count" in summary_text
    assert "ptr_clause_id" in details_text
    assert "report_item_no" in details_text
    assert "ptr_requirement" in details_text
    assert "report_requirement_excerpt" in details_text
    assert "report_result" in details_text
    assert "2.1" in details_text
    assert "输入功率应≤110%。" in details_text
    assert "输入功率 @240Ω" in details_text
    assert "≤110%" in details_text
    assert "40%" in details_text
    assert "报告序号 11 参数级结果满足 PTR 要求。" in details_text
    assert "报告序号 11 覆盖输入功率要求。" not in details_text
    assert "covered_passed" in details_text


def _ptr_comparison_details() -> dict:
    return {
        "overall_status": "needs_review",
        "overall_summary": "本次共比对 2 条技术要求，其中 1 条已覆盖，1 条需复核，1 条未覆盖。",
        "requirements_count": 2,
        "covered_count": 1,
        "missing_count": 1,
        "mismatch_count": 0,
        "needs_review_count": 1,
        "confirmed_errors_count": 0,
        "manual_review_required_count": 1,
        "refuted_findings_count": 0,
        "items": [
            {
                "ptr_clause_id": "2.1",
                "ptr_title": "输入功率",
                "ptr_page": 12,
                "ptr_requirement_text": "输入功率应≤110%。",
                "report_matches": [
                    {
                        "item_no": "11",
                        "report_page": 19,
                        "standard_clause": "4.11",
                        "item_name": "输入功率",
                        "standard_requirement": "输入功率应≤110%。",
                        "test_result": "40%; 46%; 12%",
                        "single_conclusion": "符合",
                        "remark": "",
                    }
                ],
                "coverage_comparison_rows": [
                    {
                        "ptr_clause_id": "2.1",
                        "ptr_title": "输入功率",
                        "ptr_requirement": "输入功率应≤110%。",
                        "report_item_no": "11",
                        "report_page": 19,
                        "report_standard_clause": "4.11",
                        "report_requirement_excerpt": "输入功率应≤110%。",
                        "report_result": "40%; 46%; 12%",
                        "report_conclusion": "符合",
                        "status": "covered_passed",
                        "reason": "报告序号 11 覆盖输入功率要求。",
                    }
                ],
                "atomic_comparison_rows": [
                    {
                        "atomic_id": "2.1:input_power:240ohm",
                        "clause_id": "2.1",
                        "label": "输入功率",
                        "preset": "@240Ω",
                        "expected": "≤110%",
                        "actual": "40%",
                        "unit": "%",
                        "status": "match",
                        "reason": "报告序号 11 参数级结果满足 PTR 要求。",
                        "report_page": 19,
                        "report_item_no": "11",
                        "source": "ptr_table",
                    }
                ],
                "normalized_comparison": {
                    "requirement_type": "numeric_limit",
                    "expected": "≤110%",
                    "actual": "40%, 46%, 12%",
                    "unit": "%",
                    "operator": "≤",
                    "status": "match",
                },
                "rule_status": "covered_passed",
                "user_facing_status": "covered_passed",
                "final_status": "passed",
                "reason": "报告序号 11 覆盖输入功率要求。",
                "next_action": None,
                "evidence_refs": [],
            }
        ],
    }
