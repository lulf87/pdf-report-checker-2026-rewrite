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
    assert "第三页型号规格" in text
    assert "中文字体缺失时不得崩溃" in text


def test_pdf_exporter_handles_empty_findings_without_crashing() -> None:
    pdf_bytes = export_check_results_to_pdf([], task_id="task-empty", title="空结果导出")

    assert pdf_bytes[:4] == b"%PDF"
    assert "空结果导出" in _extract_pdf_text(pdf_bytes)
