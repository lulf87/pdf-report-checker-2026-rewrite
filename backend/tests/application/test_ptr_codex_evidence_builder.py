from __future__ import annotations

from app.application.ptr_codex_evidence_builder import PtrCodexEvidenceBuilder
from app.domain.codex_review import CodexReviewTargetType
from app.domain.common import Evidence, EvidenceMethod, SourceType
from app.domain.evidence_package import EvidencePackageKind, EvidenceSourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.report import InspectionItem, ReportDocument
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope, ReportScopeRange
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


def test_clause_mismatch_finding_includes_grouped_report_item_evidence() -> None:
    finding = _finding(
        code="PTR_CLAUSE_TEXT_MISMATCH",
        check_id="PTR_CLAUSE",
        metadata={"clause_number": "2.2.1"},
    )
    ptr_doc = PTRDocument(
        clauses=[
            PTRClause(
                clause_id="ptr-2.2.1",
                number=PTRClauseNumber.from_string("2.2.1"),
                title="心脏脉冲电场消融仪输出",
                body_text="心脏脉冲电场消融仪输出电压、电流应符合产品技术要求。",
            )
        ]
    )
    report_doc = ReportDocument(
        inspection_items=[
            InspectionItem(
                sequence_raw="157",
                sequence=157,
                standard_clause="2.2",
                standard_requirement="2.2.1 心脏脉冲电场消融仪输出\n电压：3333V（峰值）",
                test_result="3375",
                result_values=["3375"],
                conclusion="符合",
                source_page=99,
                row_index_in_page=3,
            ),
            InspectionItem(
                sequence_raw="电流：57A（峰值）\n单位：A",
                item_name="59",
                standard_clause="/",
                source_page=99,
                row_index_in_page=4,
            ),
            InspectionItem(
                sequence_raw="续\n157",
                sequence=157,
                is_continuation=True,
                standard_clause="2.2",
                standard_requirement="2.2.5 脉冲衰减应在 10%内。",
                test_result="1%",
                result_values=["1%"],
                conclusion="符合",
                source_page=101,
                row_index_in_page=1,
            ),
        ]
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=ptr_doc,
        report_doc=report_doc,
        check_results=[_check_result("PTR_CLAUSE", [finding])],
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    group_item = items_by_ref["report_inspection_group:157"]
    group = group_item.structured["inspection_item_group"]
    assert group["item_no"] == "157"
    assert group["pages"] == [99, 101]
    assert "3333V" in group["standard_requirement"]
    assert "57A" in group["standard_requirement"]
    assert "3375" in group["test_result"]
    assert "59" in group["test_result"]
    assert group["single_conclusion"] == "符合"


def test_table_value_mismatch_finding_builds_ptr_parameter_target() -> None:
    finding = _finding(
        code="PTR_TABLE_VALUE_MISMATCH",
        check_id="PTR_TABLE",
        metadata={
            "clause_number": "2.1",
            "table_number": "1",
            "parameter_name": "脉冲宽度",
            "atomic_id": "2.1:table1:脉冲宽度:pulse3",
        },
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
    assert bundle.request.targets[0].metadata["atomic_id"] == "2.1:table1:脉冲宽度:pulse3"
    assert bundle.evidence_package.targets[0].metadata["atomic_id"] == "2.1:table1:脉冲宽度:pulse3"


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


def test_report_scope_finding_builds_inspection_item_target_with_scope_evidence() -> None:
    finding = _finding(
        code="PTR_SCOPE_UNDECLARED_REPORT_ITEM",
        check_id="PTR_REPORT_SCOPE",
        metadata={"clause_number": "2.7", "item_no": "160"},
    )

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_scope_document(),
        check_results=[_check_result("PTR_REPORT_SCOPE", [finding])],
    )

    assert bundle is not None
    assert bundle.request.targets[0].target_type is CodexReviewTargetType.INSPECTION_ITEM
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    assert "report_scope:declaration" in items_by_ref
    assert items_by_ref["report_scope:declaration"].structured["declared_scope_items"] == ["2.2", "2.5", "2.6"]
    assert "report_scope:external_standard_ranges" in items_by_ref
    assert items_by_ref["report_scope:external_standard_ranges"].structured["external_standard_ranges"][0]["standard"] == "GB 9706.1-2020"
    assert "report_scope:inspection_items" in items_by_ref
    assert items_by_ref["report_scope:inspection_items"].structured["items"][-1]["item_no"] == "160"


def test_report_scope_finding_includes_full_pm3562_actual_scope_items_without_truncation() -> None:
    finding = _finding(
        code="PTR_SCOPE_DECLARED_ITEM_MISSING_IN_REPORT",
        check_id="PTR_REPORT_SCOPE",
        metadata={"clause_number": "2.8.2"},
    )

    bundle = PtrCodexEvidenceBuilder(max_table_records=5).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_pm3562_report_scope_document(),
        check_results=[_check_result("PTR_REPORT_SCOPE", [finding])],
    )

    assert bundle is not None
    items_by_ref = {item.ref_id: item for item in bundle.evidence_package.items}
    inspection_scope_items = items_by_ref["report_scope:inspection_items"].structured
    item_nos = [item["item_no"] for item in inspection_scope_items["items"]]
    assert item_nos == [str(item_no) for item_no in range(38, 55)]
    assert inspection_scope_items["item_count"] == 17
    assert inspection_scope_items["truncated"] is False
    assert inspection_scope_items["items"][12]["standard_clause"] == "2.2.2"
    assert inspection_scope_items["items"][13]["standard_clause"] == "2.3"
    assert inspection_scope_items["items"][14]["standard_clause"] == "2.6"
    assert inspection_scope_items["items"][15]["standard_clause"] == "2.7"
    assert inspection_scope_items["items"][16]["standard_clause"] == "2.8.2"


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


def test_ptr_codex_evidence_builder_defaults_to_five_targets_and_records_truncation_metadata() -> None:
    findings = [
        _finding(
            id_suffix=f"value-{index}",
            code="PTR_TABLE_VALUE_MISMATCH",
            check_id="PTR_TABLE",
            metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": f"参数{index}"},
        )
        for index in range(6)
    ]

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", findings)],
    )

    assert bundle is not None
    assert len(bundle.request.targets) == 5
    assert bundle.evidence_package.metadata["total_candidate_targets"] == 6
    assert bundle.evidence_package.metadata["emitted_targets"] == 5
    assert bundle.evidence_package.metadata["truncated"] is True
    assert bundle.evidence_package.metadata["omitted_targets_count"] == 1
    assert bundle.evidence_package.metadata["batch_index"] == 0
    assert bundle.evidence_package.metadata["batch_size"] == 5


def test_ptr_codex_evidence_builder_can_limit_batch_to_one_target() -> None:
    findings = [
        _finding(code="PTR_TABLE_VALUE_MISMATCH", check_id="PTR_TABLE", id_suffix="value"),
        _finding(code="PTR_TABLE_UNIT_MISMATCH", check_id="PTR_TABLE", id_suffix="unit"),
    ]

    bundle = PtrCodexEvidenceBuilder(max_targets_per_batch=1).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", findings)],
    )

    assert bundle is not None
    assert len(bundle.request.targets) == 1


def test_ptr_codex_evidence_builder_can_emit_later_batch_without_omitting_targets() -> None:
    findings = [
        _finding(
            id_suffix=f"value-{index}",
            code="PTR_TABLE_VALUE_MISMATCH",
            check_id="PTR_TABLE",
            metadata={"clause_number": "2.1", "table_number": "1", "parameter_name": f"参数{index}"},
        )
        for index in range(6)
    ]

    first = PtrCodexEvidenceBuilder(max_targets_per_batch=5).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", findings)],
        target_offset=0,
    )
    second = PtrCodexEvidenceBuilder(max_targets_per_batch=5).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", findings)],
        target_offset=5,
    )

    assert first is not None
    assert second is not None
    assert len(first.request.targets) == 5
    assert len(second.request.targets) == 1
    assert second.evidence_package.metadata["batch_index"] == 1
    assert second.evidence_package.metadata["omitted_targets_count"] == 0
    assert second.request.targets[0].finding_id.endswith("value-5")


def test_ptr_codex_evidence_builder_filters_by_check_id_and_finding_code() -> None:
    findings = [
        _finding(code="PTR_CLAUSE_TEXT_MISMATCH", check_id="PTR_CLAUSE", id_suffix="clause"),
        _finding(code="PTR_TABLE_VALUE_MISMATCH", check_id="PTR_TABLE", id_suffix="value"),
        _finding(code="PTR_TABLE_UNIT_MISMATCH", check_id="PTR_TABLE", id_suffix="unit"),
    ]

    bundle = PtrCodexEvidenceBuilder(
        included_check_ids="PTR_TABLE",
        included_finding_codes="PTR_TABLE_UNIT_MISMATCH",
    ).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[
            _check_result("PTR_CLAUSE", findings[:1]),
            _check_result("PTR_TABLE", findings[1:]),
        ],
    )

    assert bundle is not None
    assert [target.finding_code for target in bundle.request.targets] == ["PTR_TABLE_UNIT_MISMATCH"]


def test_ptr_codex_evidence_builder_excludes_check_id() -> None:
    findings = [
        _finding(code="PTR_CLAUSE_TEXT_MISMATCH", check_id="PTR_CLAUSE", id_suffix="clause"),
        _finding(code="PTR_TABLE_VALUE_MISMATCH", check_id="PTR_TABLE", id_suffix="value"),
    ]

    bundle = PtrCodexEvidenceBuilder(excluded_check_ids="PTR_CLAUSE").build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[
            _check_result("PTR_CLAUSE", findings[:1]),
            _check_result("PTR_TABLE", findings[1:]),
        ],
    )

    assert bundle is not None
    assert [target.check_id for target in bundle.request.targets] == ["PTR_TABLE"]


def test_ptr_codex_evidence_builder_sorts_by_ptr_finding_code_priority() -> None:
    findings = [
        _finding(code="PTR_TABLE_VALUE_MISMATCH", check_id="PTR_TABLE", id_suffix="value"),
        _finding(code="PTR_CLAUSE_TEXT_MISMATCH", check_id="PTR_CLAUSE", id_suffix="clause"),
        _finding(code="PTR_TABLE_CANDIDATE_AMBIGUOUS", check_id="PTR_TABLE", id_suffix="ambiguous"),
    ]

    bundle = PtrCodexEvidenceBuilder().build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[
            _check_result("PTR_TABLE", [findings[0], findings[2]]),
            _check_result("PTR_CLAUSE", [findings[1]]),
        ],
    )

    assert bundle is not None
    assert [target.finding_code for target in bundle.request.targets] == [
        "PTR_CLAUSE_TEXT_MISMATCH",
        "PTR_TABLE_CANDIDATE_AMBIGUOUS",
        "PTR_TABLE_VALUE_MISMATCH",
    ]


def test_ptr_codex_evidence_builder_zero_max_targets_returns_none() -> None:
    bundle = PtrCodexEvidenceBuilder(max_targets_per_batch=0).build(
        task_id="task-1",
        task_type=TaskType.PTR_COMPARE.value,
        ptr_doc=_ptr_document(),
        report_doc=_report_document(),
        check_results=[_check_result("PTR_TABLE", [_finding(code="PTR_TABLE_VALUE_MISMATCH", check_id="PTR_TABLE")])],
    )

    assert bundle is None


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


def _report_scope_document() -> ReportDocument:
    scope = ReportInspectionScope(
        declared_scope_items=["2.2", "2.5", "2.6"],
        excluded_topics=["生物相容性", "电磁兼容性"],
        source_page=3,
        source_text="2.2、2.5、2.6（除生物相容性、电磁兼容性）",
        external_standard_ranges=[
            ExternalStandardRange(
                start_item_no="1",
                end_item_no="118",
                standard="GB 9706.1-2020",
                source_page=5,
                source_text="序号 1～序号 118 为 GB 9706.1-2020 标准的内容",
            )
        ],
        ptr_direct_content_starts_after="118",
    )
    return ReportDocument(
        inspection_items=[
            InspectionItem(sequence_raw="157", sequence=157, standard_clause="2.2", standard_requirement="输出", test_result="符合要求", conclusion="符合", source_page=99),
            InspectionItem(sequence_raw="158", sequence=158, standard_clause="2.5", standard_requirement="电气安全", test_result="符合要求", conclusion="符合", source_page=99),
            InspectionItem(sequence_raw="159", sequence=159, standard_clause="2.6", standard_requirement="软件功能", test_result="符合要求", conclusion="符合", source_page=99),
            InspectionItem(sequence_raw="160", sequence=160, standard_clause="2.7", standard_requirement="额外项目", test_result="符合要求", conclusion="符合", source_page=100),
        ],
        metadata={"inspection_scope": scope.model_dump(mode="json")},
    )


def _pm3562_report_scope_document() -> ReportDocument:
    scope_text = (
        "2.1.1～2.1.12、2.2.2、2.3（仅检 PVC 反应）、2.6、2.7、"
        "2.8.2（除有源植入式医疗器械对外部除颤器造成损坏的防护、"
        "GB 16174.2-2024 中 21.2、有源植入式医疗器械对非电离电磁辐射的防护）"
    )
    scope = ReportInspectionScope(
        declared_scope_items=["2.2.2", "2.3", "2.6", "2.7", "2.8.2"],
        declared_scope_ranges=[ReportScopeRange(start="2.1.1", end="2.1.12", source_text=scope_text)],
        scope_modifiers=[{"clause": "2.3", "only": ["PVC 反应", "PVC Response"], "source_text": "仅检 PVC 反应"}],
        clause_exclusions=[
            {
                "clause": "2.8.2",
                "excluded_topics": [
                    "有源植入式医疗器械对外部除颤器造成损坏的防护",
                    "GB 16174.2-2024 中 21.2",
                    "有源植入式医疗器械对非电离电磁辐射的防护",
                ],
                "source_text": (
                    "除有源植入式医疗器械对外部除颤器造成损坏的防护、"
                    "GB 16174.2-2024 中 21.2、有源植入式医疗器械对非电离电磁辐射的防护"
                ),
            }
        ],
        excluded_topics=[
            "有源植入式医疗器械对外部除颤器造成损坏的防护",
            "GB 16174.2-2024 中 21.2",
            "有源植入式医疗器械对非电离电磁辐射的防护",
        ],
        source_page=1,
        source_text=scope_text,
        external_standard_ranges=[
            ExternalStandardRange(
                start_item_no="1",
                end_item_no="24",
                standard="GB 16174.1-2024",
                source_page=5,
                source_text="序号 1～24 为 GB 16174.1-2024 标准的内容",
            ),
            ExternalStandardRange(
                start_item_no="25",
                end_item_no="37",
                standard="GB 16174.2-2024",
                source_page=5,
                source_text="序号 25～37 为 GB 16174.2-2024 标准的内容",
            ),
        ],
        ptr_direct_content_starts_after="37",
    )
    inspection_items = [
        InspectionItem(
            sequence_raw=str(item_no),
            sequence=item_no,
            standard_clause=f"2.1.{item_no - 37}",
            standard_requirement=f"2.1.{item_no - 37} 项",
            test_result="符合要求",
            conclusion="符合",
            source_page=20,
        )
        for item_no in range(38, 50)
    ]
    inspection_items.extend(
        [
            InspectionItem(sequence_raw="50", sequence=50, standard_clause="2.2.2", standard_requirement="紧急起搏模式", test_result="符合要求", conclusion="符合", source_page=21),
            InspectionItem(sequence_raw="51", sequence=51, standard_clause="2.3", standard_requirement="PVC 反应 / PVC Response", test_result="符合要求", conclusion="符合", remark="仅检 PVC 反应", source_page=21),
            InspectionItem(sequence_raw="52", sequence=52, standard_clause="2.6", standard_requirement="通用要求，见序号 1～24", test_result="符合要求", conclusion="符合", source_page=21),
            InspectionItem(sequence_raw="53", sequence=53, standard_clause="2.7", standard_requirement="专用要求，见序号 25～37", test_result="符合要求", conclusion="符合", source_page=21),
            InspectionItem(sequence_raw="54", sequence=54, standard_clause="2.8.2", standard_requirement="扭矩扳手尺寸", test_result="A=0.884，B=0.993", conclusion="符合", source_page=22),
        ]
    )
    return ReportDocument(
        inspection_items=inspection_items,
        metadata={"inspection_scope": scope.model_dump(mode="json")},
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
