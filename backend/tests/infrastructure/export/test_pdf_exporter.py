import fitz

from app.infrastructure.export.pdf_exporter import export_check_results_to_pdf
from tests.fixtures.export_result_builder import sample_check_results


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in document)


def test_pdf_exporter_includes_task_summary_findings_and_evidence() -> None:
    pdf_bytes = export_check_results_to_pdf(
        sample_check_results(task_id="task-pdf"),
        task_id="task-pdf",
        title="报告自身核对报告",
        input_files=["report.pdf"],
        diagnostics=["中文字体缺失时不得崩溃"],
    )

    assert pdf_bytes[:4] == b"%PDF"
    text = _extract_pdf_text(pdf_bytes)
    assert "报告自身核对报告" in text
    assert "task-pdf" in text
    assert "C01" in text
    assert "ABC-1" in text
    assert "ABC-2" in text
    assert "candidate_errors_count" in text
    assert "confirmed_errors_count" in text
    assert "manual_review_required_count" in text
    assert "legacy_fail_count" in text
    assert "legacy_error_count" in text
    assert "user_facing_status" in text
    assert "\nerror_count:" not in text
    assert "\nfail_count:" not in text
    assert "\nwarn_count:" not in text
    assert "核对明细" in text
    assert "检查目的" in text
    assert "核对首页与报告首页字段是否一致" in text
    assert "型号规格" in text
    assert "两处摘录不一致" in text
    assert "第三页型号规格" in text
    assert "中文字体缺失时不得崩溃" in text


def test_pdf_exporter_handles_empty_findings_without_crashing() -> None:
    pdf_bytes = export_check_results_to_pdf([], task_id="task-empty", title="空结果导出")

    assert pdf_bytes[:4] == b"%PDF"
    assert "空结果导出" in _extract_pdf_text(pdf_bytes)


def test_pdf_exporter_includes_ptr_comparison_summary_and_clause_details() -> None:
    pdf_bytes = export_check_results_to_pdf(
        sample_check_results(task_id="task-ptr-pdf"),
        task_id="task-ptr-pdf",
        task_type="ptr_compare",
        title="PTR 比对导出",
        input_files=["ptr.pdf", "report.pdf"],
        metadata={"ptr_comparison_details": _ptr_comparison_details()},
    )

    text = _extract_pdf_text(pdf_bytes)
    compact_text = text.replace(" ", "")
    assert "技术要求与报告比对摘要" in text
    assert "本次共比对2条技术要求" in compact_text
    assert "PTR条款2.1输入功率" in compact_text
    assert "PTR摘录:输入功率应≤110%。" in compact_text
    assert "报告匹配项:序号11" in compact_text
    assert "条款覆盖对比:" in text
    assert "报告结果40%;46%;12%" in compact_text
    assert "比对结论:covered_passed" in compact_text
    assert "判断理由:报告序号11覆盖输入功率要求。" in compact_text


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
