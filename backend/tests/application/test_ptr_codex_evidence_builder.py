from __future__ import annotations

from app.application.ptr_codex_evidence_builder import PtrCodexEvidenceBuilder
from app.domain.codex_review import CodexReviewTargetType
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.evidence_package import EvidencePackageKind, EvidenceSourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.report import ReportDocument
from app.domain.result import CheckResult, CheckStatus
from app.domain.table import CanonicalTable, ParameterRecord
from app.domain.task import TaskType


OLD_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.4.13"
NEW_PROJECT_ROOT = "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.6.3"


def test_clause_mismatch_finding_builds_ptr_clause_target() -> None:
    finding = _finding(code="PTR_CLAUSE_TEXT_MISMATCH", check_id="PTR_CLAUSE", metadata={"clause_number": "2.1"})

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_CLAUSE", [finding])],
    )

    assert bundle is not None
    assert bundle.evidence_package.kind is EvidencePackageKind.PTR_CLAUSE_REVIEW
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.PTR_CLAUSE
    assert bundle.request.targets[0].finding_id == finding.id


def test_table_value_mismatch_finding_builds_ptr_parameter_target() -> None:
    finding = _finding(
        code="PTR_TABLE_VALUE_MISMATCH",
        check_id="PTR_TABLE",
        metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": "脉冲宽度"},
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", [finding])],
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.PTR_PARAMETER


def test_scope_finding_builds_ptr_clause_target_when_scope_rule_outputs_finding() -> None:
    finding = _finding(
        code="PTR_SCOPE_FILTER_REVIEW",
        check_id="PTR_SCOPE",
        metadata={"clause_number": "2.1", "scope": True},
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_SCOPE", [finding])],
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.PTR_CLAUSE
    assert bundle.evidence_package.targets[0].metadata["source"] == "ptr_compare_usecase"


def test_package_contains_finding_clause_ptr_table_and_report_table_evidence() -> None:
    finding = _finding(
        code="PTR_TABLE_VALUE_MISMATCH",
        check_id="PTR_TABLE",
        metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": "脉冲宽度"},
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", [finding])],
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    assert f"finding:{finding.id}" in items_by_ref
    assert items_by_ref[f"finding:{finding.id}"].source_type is EvidenceSourceType.FINDING
    assert "ptr_clause:ptr-2.1" in items_by_ref
    assert items_by_ref["ptr_clause:ptr-2.1"].source_type is EvidenceSourceType.PTR_CLAUSE
    assert "ptr_table:ptr-table-1" in items_by_ref
    assert "report_table:report-table-1" in items_by_ref
    assert "rule_context:task-1:PTR_TABLE:2.1:table-1:脉冲宽度:value" in items_by_ref


def test_target_evidence_refs_all_exist_in_package_items() -> None:
    finding = _finding(code="PTR_CLAUSE_MISSING", check_id="PTR_CLAUSE", metadata={"clause_number": "2.1"})

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_CLAUSE", [finding])],
    )

    assert bundle is not None
    item_refs = {item.ref_id for item in bundle.evidence_package.items}
    for target in bundle.evidence_package.targets:
        assert set(target.evidence_refs) <= item_refs
    for target in bundle.request.targets:
        assert {ref.ref_id for ref in target.evidence_refs} <= item_refs


def test_package_does_not_contain_old_or_new_project_absolute_paths() -> None:
    finding = _finding(
        code="PTR_CLAUSE_TEXT_MISMATCH",
        check_id="PTR_CLAUSE",
        message=f"旧项目 {OLD_PROJECT_ROOT}/x；新项目 {NEW_PROJECT_ROOT}/y",
        metadata={
            "clause_number": "2.1",
            "source": f"{OLD_PROJECT_ROOT}/services/report_self_check_service.py",
        },
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_CLAUSE", [finding])],
    )

    dumped = bundle.evidence_package.model_dump_json() if bundle else ""
    assert OLD_PROJECT_ROOT not in dumped
    assert NEW_PROJECT_ROOT not in dumped
    assert "/Users/" not in dumped


def test_no_findings_returns_none() -> None:
    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", [])],
    )

    assert bundle is None


def test_duplicate_related_evidence_refs_are_not_duplicated() -> None:
    first = _finding(
        id_suffix="value",
        code="PTR_TABLE_VALUE_MISMATCH",
        check_id="PTR_TABLE",
        metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": "脉冲宽度"},
    )
    second = _finding(
        id_suffix="unit",
        code="PTR_TABLE_UNIT_MISMATCH",
        check_id="PTR_TABLE",
        metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": "脉冲宽度"},
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", [first, second])],
    )

    assert bundle is not None
    refs = [item.ref_id for item in bundle.evidence_package.items]
    assert len(refs) == len(set(refs))
    assert refs.count("ptr_clause:ptr-2.1") == 1
    assert refs.count("ptr_table:ptr-table-1") == 1
    assert refs.count("report_table:report-table-1") == 1


def test_large_table_evidence_is_compacted_to_record_summary() -> None:
    records = [_record(f"参数{i}", str(i)) for i in range(30)]
    ptr_doc = _ptr_document(ptr_table=_canonical_table("ptr-table-1", "1", records))
    report_doc = _report_document(report_tables=[_canonical_table("report-table-1", "1", records)])
    finding = _finding(
        code="PTR_TABLE_VALUE_MISMATCH",
        check_id="PTR_TABLE",
        metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": "参数0"},
    )

    bundle = PtrCodexEvidenceBuilder(max_table_records=5).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=ptr_doc,
        report_doc=report_doc,
        check_results=[_check_result("PTR_TABLE", [finding])],
    )

    assert bundle is not None
    table_item = next(item for item in bundle.evidence_package.items if item.ref_id == "ptr_table:ptr-table-1")
    assert table_item.structured["parameter_record_count"] == 30
    assert len(table_item.structured["parameter_records"]) == 5
    assert "cells" not in table_item.structured


def _check_result(check_id: str, findings: list[Finding]) -> CheckResult:
    return CheckResult(
        task_id="task-1",
        check_id=check_id,
        check_name=check_id,
        status=CheckStatus.FAIL if findings else CheckStatus.PASS,
        findings=findings,
    )


def _finding(
    *,
    code: str,
    check_id: str,
    metadata: dict | None = None,
    message: str = "PTR finding needs Codex review.",
    id_suffix: str = "value",
) -> Finding:
    return Finding(
        id=f"task-1:{check_id}:2.1:table-1:脉冲宽度:{id_suffix}",
        task_id="task-1",
        check_id=check_id,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        expected="expected",
        actual="actual",
        evidence=[
            Evidence(
                id=f"ev-{id_suffix}",
                source_type=SourceType.PTR if check_id == "PTR_CLAUSE" else SourceType.REPORT,
                raw_text="evidence text",
                method=EvidenceMethod.PDF_TEXT,
            )
        ],
        metadata=metadata or {},
    )


def _ptr_document(ptr_table: CanonicalTable | None = None) -> PTRDocument:
    table = ptr_table or _canonical_table("ptr-table-1", "1", [_record("脉冲宽度", "0.4")])
    return PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.1",
                number=PTRClauseNumber.from_string("2.1"),
                title="脉冲参数",
                body_text="脉冲参数应符合表1。",
                table_references=[TableReference(table_number="1", reference_text="表1", clause_id="ptr-2.1")],
            )
        ],
        tables=[
            PTRTable(
                table_id=table.table_id,
                table_number=table.table_number,
                title=table.caption,
                canonical_table=table,
            )
        ],
    )


def _report_document(report_tables: list[CanonicalTable] | None = None) -> ReportDocument:
    return ReportDocument(
        metadata={
            "canonical_tables": report_tables
            or [_canonical_table("report-table-1", "1", [_record("脉冲宽度", "0.5")])]
        }
    )


def _canonical_table(table_id: str, table_number: str, records: list[ParameterRecord]) -> CanonicalTable:
    return CanonicalTable(
        table_id=table_id,
        table_number=table_number,
        caption=f"表 {table_number} 参数",
        parameter_records=records,
        parameter_name_column="参数",
        value_columns=["标准设置"],
        condition_columns=["型号"],
    )


def _record(name: str, value: str) -> ParameterRecord:
    return ParameterRecord(
        parameter_name=name,
        dimensions={"型号": "全部型号"},
        values={"标准设置": value},
    )
