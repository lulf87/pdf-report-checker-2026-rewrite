from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.ptr_compare_usecase import PTRCompareUseCase
from app.application.task_service import TaskService
from app.domain.codex_review import CodexReviewVerdict
from app.domain.task import TaskState
from app.infrastructure.pdf.pymupdf_parser import PyMuPDFParser
from app.infrastructure.ptr.ptr_extractor import PTRExtractor
from app.infrastructure.report.field_extractor import FieldExtractor
from app.infrastructure.report.inspection_scope_extractor import ReportInspectionScopeExtractor
from app.infrastructure.report.inspection_table_extractor import InspectionTableExtractor
from app.infrastructure.report.parameter_table_extractor import ReportParameterTableExtractor
from app.infrastructure.storage.local_file_store import LocalFileStore
from tests.application.test_ptr_compare_usecase import FakePtrCodexAuditService


OLD_MATERIAL_DIR = Path("/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13/素材")
PM3562_PTR_PATH = OLD_MATERIAL_DIR / "ptr/4788/CH3.4.1QuadraAllure3TMP技术要求_PM3562-1-0506最终.pdf"
PM3562_REPORT_PATH = OLD_MATERIAL_DIR / "report/4788/4788draft.pdf"


def test_ptr_compare_pm3562_real_sample_scope_and_direct_items(tmp_path: Path) -> None:
    if not PM3562_PTR_PATH.exists() or not PM3562_REPORT_PATH.exists():
        pytest.skip("PM3562/4788 real sample PDFs are not available on this machine.")

    result = _run_real_pm3562(tmp_path)
    details = result.metadata["ptr_comparison_details"]
    items = {item["ptr_clause_id"]: item for item in details["items"]}
    expected_clause_ids = [
        *(f"2.1.{index}" for index in range(1, 13)),
        "2.2.2",
        "2.3",
        "2.6",
        "2.7",
        "2.8.2",
    ]

    ptr_scope = _check_result(result, "PTR_SCOPE")
    included_ids = set(ptr_scope.metadata["included_clause_ids"])
    assert {f"ptr-{clause_id}" for clause_id in expected_clause_ids} <= included_ids
    assert "ptr-2.1" not in included_ids
    assert set(expected_clause_ids) <= set(items)
    assert "2.1" not in items
    coverage_rows = [row for item in items.values() for row in item["coverage_comparison_rows"]]
    assert len(coverage_rows) >= 17

    scope_metadata = _check_result(result, "PTR_REPORT_SCOPE").metadata["scope_consistency"]
    assert scope_metadata["status"] == "passed"
    assert scope_metadata["actual_report_scope"] == [
        *(f"2.1.{index}" for index in range(1, 13)),
        "2.2.2",
        "2.3",
        "2.6",
        "2.7",
        "2.8.2",
    ]
    assert "2.2" not in scope_metadata["actual_report_scope"]
    assert "2.8" not in scope_metadata["actual_report_scope"]
    assert scope_metadata["scope_modifiers"] == [
        {"clause": "2.3", "only": ["PVC 反应", "PVC Response"], "source_text": "仅检 PVC 反应"}
    ]
    assert scope_metadata["excluded_topics"] == [
        "有源植入式医疗器械对外部除颤器造成损坏的防护",
        "GB 16174.2-2024 中 21.2",
        "有源植入式医疗器械对非电离电磁辐射的防护",
    ]

    for index in range(1, 13):
        item = items[f"2.1.{index}"]
        assert item["coverage_status"] == "covered_passed"
        assert item["report_matches"][0]["item_no"] == str(index + 37)
        assert item["report_matches"][0]["single_conclusion"] in {"符合", "/"}
    assert not _has_finding(result, "PTR_TABLE_MISSING", clause_number_prefix="2.1", table_number="2-1")

    item_222 = items["2.2.2"]
    assert item_222["final_status"] == "passed"
    assert item_222["coverage_comparison_rows"][0]["report_item_no"] == "50"
    assert item_222["report_matches"][0]["item_no"] == "50"
    for token in ("VVI", "70", "7.5", "0.6", "325"):
        assert token in _compact(item_222["report_matches"][0]["test_result"])

    item_23 = items["2.3"]
    assert item_23["final_status"] == "passed"
    assert item_23["coverage_comparison_rows"][0]["report_item_no"] == "51"
    assert "PVC" in item_23["coverage_comparison_rows"][0]["reason"]
    assert item_23["report_matches"][0]["item_no"] == "51"
    assert "PVC" in item_23["ptr_requirement_text"]
    assert "PVC" in item_23["report_matches"][0]["standard_requirement"]
    assert "仅检PVC反应" in _compact(item_23["report_matches"][0]["remark"])
    assert not _has_finding(result, "PTR_TABLE_MISSING", clause_number="2.3", table_number="2-2")

    assert items["2.6"]["report_matches"][0]["item_no"] == "52"
    assert items["2.6"]["external_standard_coverages"][0]["standard"] == "GB 16174.1-2024"
    assert items["2.6"]["external_standard_coverages"][0]["start_item_no"] == "1"
    assert items["2.6"]["external_standard_coverages"][0]["end_item_no"] == "24"
    assert items["2.7"]["report_matches"][0]["item_no"] == "53"
    assert items["2.7"]["external_standard_coverages"][0]["standard"] == "GB 16174.2-2024"
    assert items["2.7"]["external_standard_coverages"][0]["start_item_no"] == "25"
    assert items["2.7"]["external_standard_coverages"][0]["end_item_no"] == "37"

    item_282 = items["2.8.2"]
    assert item_282["final_status"] == "passed"
    assert item_282["coverage_comparison_rows"][0]["report_item_no"] == "54"
    assert "0.884" in item_282["coverage_comparison_rows"][0]["report_result"]
    assert "0.993" in item_282["coverage_comparison_rows"][0]["report_result"]
    assert item_282["report_matches"][0]["item_no"] == "54"
    assert "0.884" in item_282["report_matches"][0]["test_result"]
    assert "0.993" in item_282["report_matches"][0]["test_result"]

    assert not _has_finding(result, "PTR_CLAUSE_TEXT_MISMATCH", clause_number="2.3")
    assert result.summary.confirmed_errors_count == 0
    assert result.summary.manual_review_required_count == 0
    assert details["confirmed_errors_count"] == 0
    assert details["manual_review_required_count"] == 0
    assert "/Users/" not in json.dumps(details, ensure_ascii=False)


def _run_real_pm3562(tmp_path: Path):
    task_service = TaskService()
    usecase = PTRCompareUseCase(
        task_service=task_service,
        file_store=LocalFileStore(tmp_path),
        pdf_parser=PyMuPDFParser(),
        ptr_extractor=PTRExtractor(),
        report_extractor=FieldExtractor(),
        inspection_table_extractor=InspectionTableExtractor(),
        inspection_scope_extractor=ReportInspectionScopeExtractor(),
        parameter_table_extractor=ReportParameterTableExtractor(),
        codex_audit_service=FakePtrCodexAuditService(verdict=CodexReviewVerdict.UNCERTAIN),
    )
    status = usecase.run(
        ptr_file_name=PM3562_PTR_PATH.name,
        ptr_content=PM3562_PTR_PATH.read_bytes(),
        report_file_name=PM3562_REPORT_PATH.name,
        report_content=PM3562_REPORT_PATH.read_bytes(),
        audit_options={"run_codex": True},
    )

    assert status.status == TaskState.COMPLETED, status.error_message
    return task_service.get_result(status.task_id)


def _check_result(result, check_id: str):
    return next(check_result for check_result in result.check_results if check_result.check_id == check_id)


def _has_finding(
    result,
    code: str,
    *,
    clause_number: str | None = None,
    clause_number_prefix: str | None = None,
    table_number: str | None = None,
) -> bool:
    for finding in result.findings:
        if finding.code != code:
            continue
        finding_clause = str(finding.metadata.get("clause_number") or "")
        if clause_number is not None and finding_clause != clause_number:
            continue
        if clause_number_prefix is not None and not finding_clause.startswith(clause_number_prefix):
            continue
        if table_number is not None and finding.metadata.get("table_number") != table_number:
            continue
        return True
    return False


def _compact(value: str) -> str:
    return "".join(str(value or "").split())
