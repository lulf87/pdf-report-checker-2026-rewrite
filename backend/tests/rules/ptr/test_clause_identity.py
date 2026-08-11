from __future__ import annotations

from app.domain.ptr_comparison import (
    ClauseIdentityAlignment,
    PTRAtomicComparisonRow,
    PTRClauseIdentity,
    ReportClauseIdentity,
    ReportSubclauseIndex,
)
from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRClauseNumber
from app.domain.report import InspectionItem
from app.rules.ptr.clause_identity import (
    align_clause_identity,
    build_clause_sequence_offset_aggregation,
    build_clause_identity_findings,
    build_ptr_clause_identity,
    build_report_subclause_index,
    gate_atomic_rows_by_clause_identity,
)


def _ptr_identity(
    number: str,
    title: str,
    *,
    table_rows: list[str] | None = None,
    units: list[str] | None = None,
) -> PTRClauseIdentity:
    return PTRClauseIdentity(
        clause_id=f"ptr-{number}",
        clause_number=number,
        title=title,
        normalized_title=title,
        local_text=f"{title}应符合要求。",
        parent_clause=".".join(number.split(".")[:-1]),
        referenced_tables=["3"],
        table_row_labels=table_rows or [title],
        parameter_terms=[title],
        units=units or [],
        source_page=4,
    )


def _report_identity(
    number: str,
    title: str,
    *,
    item_no: str = "38",
    source_row: int = 8,
    units: list[str] | None = None,
) -> ReportClauseIdentity:
    return ReportClauseIdentity(
        identity_id=f"report:{item_no}:{number}:{source_row}",
        item_no=item_no,
        group_id=f"inspection-item-{item_no}",
        clause_number=number,
        title=title,
        normalized_title=title,
        standard_requirement_text=f"{title}应符合表3的要求。",
        row_label=title,
        parent_clause=".".join(number.split(".")[:-1]),
        referenced_tables=["3"],
        parameter_terms=[title],
        units=units or [],
        test_result="符合要求",
        conclusion="符合",
        source_page=30,
        source_row=source_row,
    )


def test_exact_number_and_exact_title_is_exact_match() -> None:
    alignment = align_clause_identity(
        _ptr_identity("2.1.8", "输入阻抗", units=["kΩ"]),
        ReportSubclauseIndex(identities=[_report_identity("2.1.8", "输入阻抗", units=["kΩ"])]),
    )

    assert alignment.status == "exact_match"
    assert alignment.selected_report_clause_number == "2.1.8"
    assert alignment.number_matches is True
    assert alignment.title_matches is True


def test_exact_number_with_conflicting_title_is_identity_mismatch() -> None:
    alignment = align_clause_identity(
        _ptr_identity("2.1.8", "输入阻抗", units=["kΩ"]),
        ReportSubclauseIndex(identities=[_report_identity("2.1.8", "房室间期", units=["ms"])]),
    )

    assert alignment.status == "identity_mismatch"
    assert alignment.selected_report_identity is None
    assert alignment.candidates[0].rejected_reason == "exact_number_semantic_conflict"
    assert "输入阻抗" in alignment.reason
    assert "房室间期" in alignment.reason


def test_number_mismatch_with_exact_semantic_title_is_selected_for_review() -> None:
    alignment = align_clause_identity(
        _ptr_identity("2.1.9", "房室间期", units=["ms"]),
        ReportSubclauseIndex(identities=[_report_identity("2.1.8", "房室间期", units=["ms"])]),
    )

    assert alignment.status == "semantic_match_number_mismatch"
    assert alignment.selected_report_clause_number == "2.1.8"
    assert alignment.number_matches is False
    assert alignment.title_matches is True
    assert alignment.parameter_matches is True


def test_exact_number_conflict_is_rejected_in_favor_of_semantic_candidate() -> None:
    alignment = align_clause_identity(
        _ptr_identity("2.1.8", "输入阻抗", units=["kΩ"]),
        ReportSubclauseIndex(
            identities=[
                _report_identity("2.1.8", "房室间期", units=["ms"]),
                _report_identity("2.1.7", "输入阻抗", source_row=12, units=["kΩ"]),
            ]
        ),
    )

    assert alignment.status == "semantic_match_number_mismatch"
    assert alignment.selected_report_clause_number == "2.1.7"
    rejected = next(candidate for candidate in alignment.candidates if candidate.report_clause_number == "2.1.8")
    assert rejected.rejected_reason == "exact_number_semantic_conflict"


def test_equally_strong_semantic_candidates_are_ambiguous() -> None:
    alignment = align_clause_identity(
        _ptr_identity("2.1.9", "房室间期", units=["ms"]),
        ReportSubclauseIndex(
            identities=[
                _report_identity("2.1.7", "房室间期", source_row=7, units=["ms"]),
                _report_identity("2.1.8", "房室间期", source_row=8, units=["ms"]),
            ]
        ),
    )

    assert alignment.status == "ambiguous"
    assert alignment.selected_report_identity is None
    assert alignment.candidate_count == 2


def test_duplicate_fragments_for_same_report_subclause_are_not_ambiguous() -> None:
    ptr_identity = _ptr_identity("2.4.1.1", "心脏脉冲电场消融仪")
    short_fragment = _report_identity(
        "2.4.1.1",
        "心脏脉冲电场消融仪应该验证授权用",
        item_no="160",
        source_row=1,
    )
    complete_fragment = _report_identity(
        "2.4.1.1",
        "心脏脉冲电场消融仪应该验证授权用户和临床用户的访问权限",
        item_no="160",
        source_row=2,
    )

    alignment = align_clause_identity(
        ptr_identity,
        ReportSubclauseIndex(identities=[short_fragment, complete_fragment]),
    )

    assert alignment.status == "exact_match"
    assert alignment.selected_report_clause_number == "2.4.1.1"
    assert alignment.selected_report_item_no == "160"


def test_identity_mismatch_removes_sibling_actual_even_when_atomic_row_matches() -> None:
    alignment = ClauseIdentityAlignment(
        status="identity_mismatch",
        ptr_clause_number="2.1.8",
        ptr_title="输入阻抗",
        number_matches=False,
        title_matches=False,
        parameter_matches=False,
        table_row_matches=False,
        confidence="high",
        reason="同编号报告条款为房室间期。",
    )
    rows = [
        PTRAtomicComparisonRow(
            atomic_id="2.1.8:input_impedance",
            clause_id="2.1.8",
            label="输入阻抗",
            expected="≥40kΩ",
            actual="-1～+0",
            unit="ms",
            status="match",
            report_clause_number="2.1.8",
            report_item_no="38",
        )
    ]

    gated = gate_atomic_rows_by_clause_identity(rows, alignment)

    assert gated[0].actual is None
    assert gated[0].status == "needs_review"
    assert gated[0].report_clause_number is None
    assert "条款身份" in str(gated[0].reason)


def test_semantic_selection_rejects_result_from_non_selected_sibling() -> None:
    selected = _report_identity("2.1.7", "输入阻抗", units=["kΩ"])
    alignment = ClauseIdentityAlignment(
        status="semantic_match_number_mismatch",
        ptr_clause_number="2.1.8",
        ptr_title="输入阻抗",
        selected_report_clause_number="2.1.7",
        selected_report_title="输入阻抗",
        selected_report_identity=selected,
        number_matches=False,
        title_matches=True,
        parameter_matches=True,
        table_row_matches=True,
        confidence="high",
        reason="内容对应但编号不一致。",
    )
    rows = [
        PTRAtomicComparisonRow(
            atomic_id="2.1.8:input_impedance",
            clause_id="2.1.8",
            label="输入阻抗",
            expected="≥40kΩ",
            actual="-1～+0",
            unit="ms",
            status="match",
            report_clause_number="2.1.8",
            report_item_no="38",
        )
    ]

    gated = gate_atomic_rows_by_clause_identity(rows, alignment)

    assert gated[0].actual is None
    assert gated[0].status == "needs_review"
    assert "非选中报告子条款" in str(gated[0].reason)


def test_semantic_selection_keeps_unnumbered_result_with_selected_parameter_label() -> None:
    selected = _report_identity("2.2.7", "保护功能")
    selected = selected.model_copy(
        update={
            "standard_requirement_text": "温度超限保护和过流保护功能符合要求。",
            "parameter_terms": ["保护功能", "温度超限保护", "过流保护"],
        }
    )
    alignment = ClauseIdentityAlignment(
        status="semantic_match_number_mismatch",
        ptr_clause_number="2.2.7.1",
        ptr_title="温度超限保护",
        selected_report_clause_number="2.2.7",
        selected_report_title="保护功能",
        selected_report_identity=selected,
        number_matches=False,
        title_matches=True,
        parameter_matches=True,
        confidence="high",
        reason="报告父级功能行明确包含该子功能。",
    )
    row = PTRAtomicComparisonRow(
        atomic_id="2.2.7.1:temperature_limit_protection",
        clause_id="2.2.7.1",
        label="温度超限保护",
        expected="具备",
        actual="符合要求",
        status="match",
        report_item_no="157",
        source_text="2.2.7 保护功能 温度超限保护和过流保护功能符合要求。",
    )

    gated = gate_atomic_rows_by_clause_identity([row], alignment)

    assert gated[0].actual == "符合要求"
    assert gated[0].status == "match"


def test_ptr_identity_uses_local_clause_text_and_selected_table_row_only() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.8",
        number=PTRClauseNumber.from_string("2.1.8"),
        title="输入阻抗",
        body_text="输入阻抗\n心脏起搏器的输入阻抗的数值应符合表3的要求。\n表3 功能参数\n房室间期 155ms",
        full_text="2.1.8 输入阻抗\n完整父级表3：房室间期、灵敏度、输入阻抗",
        table_refs=["3"],
        metadata={"referenced_table_text_attached": True},
    )
    requirements = [
        PTRAtomicComparisonRow(
            atomic_id="2.1.8:table3:input_impedance:6232",
            clause_id="2.1.8",
            label="输入阻抗",
            table_row_label="输入阻抗",
            expected="≥40kΩ",
            unit="kΩ",
            source="ptr_table",
            table_number="3",
            parent_clause="2.1",
        )
    ]

    identity = build_ptr_clause_identity(clause, requirements)

    assert identity.local_text == "心脏起搏器的输入阻抗的数值应符合表3的要求。"
    assert "房室间期" not in identity.local_text
    assert identity.table_row_labels == ["输入阻抗"]
    assert identity.parameter_terms == ["输入阻抗"]
    assert identity.units == ["kΩ"]


def test_report_subclause_index_splits_child_rows_inside_parent_group() -> None:
    group = InspectionItemGroup(
        item_no="38",
        display_item_no="38",
        pages=[30],
        effective_single_conclusion="符合",
        rows=[
            InspectionItem(
                sequence_raw="38",
                sequence=38,
                standard_clause="2.1",
                standard_requirement="基本电性能指标",
                conclusion="符合",
                source_page=30,
                row_index_in_page=0,
            ),
            InspectionItem(
                sequence_raw="2.1.7 逸搏间期",
                item_name="",
                source_page=30,
                row_index_in_page=7,
            ),
            InspectionItem(
                sequence_raw="允许误差：±2min⁻¹",
                item_name="-1～+1",
                source_page=30,
                row_index_in_page=8,
            ),
            InspectionItem(
                sequence_raw="2.1.8 房室间期（只适用于双腔起搏器）",
                item_name="",
                source_page=30,
                row_index_in_page=9,
            ),
            InspectionItem(
                sequence_raw="起搏 允许误差：-10/+15ms",
                item_name="-1～+0",
                source_page=30,
                row_index_in_page=10,
            ),
        ],
    )

    index = build_report_subclause_index([group])

    identities = {(identity.clause_number, identity.normalized_title): identity for identity in index.identities}
    assert ("2.1.7", "逸搏间期") in identities
    assert ("2.1.8", "房室间期") in identities
    assert identities[("2.1.8", "房室间期")].test_result == "-1～+0"
    assert identities[("2.1.8", "房室间期")].item_no == "38"
    assert identities[("2.1.8", "房室间期")].source_page == 30


def test_report_subclause_index_keeps_header_identity_without_result_payload() -> None:
    group = InspectionItemGroup(
        item_no="38",
        display_item_no="38",
        pages=[30],
        effective_single_conclusion="符合",
        rows=[
            InspectionItem(
                sequence_raw="38",
                sequence=38,
                standard_clause="2.1",
                standard_requirement="基本电性能指标",
                conclusion="符合",
                source_page=30,
                row_index_in_page=0,
            ),
            InspectionItem(
                sequence_raw="2.1.8 房室间期（只适用于双腔起搏器）",
                source_page=30,
                row_index_in_page=9,
            ),
        ],
    )

    index = build_report_subclause_index([group])

    identity = next(
        item
        for item in index.identities
        if item.clause_number == "2.1.8" and item.normalized_title == "房室间期"
    )
    assert identity.test_result is None
    assert identity.conclusion is None
    assert identity.source_page == 30
    assert identity.source_row == 9


def test_report_subclause_index_accepts_result_row_without_requirement_text() -> None:
    group = InspectionItemGroup(
        item_no="38",
        display_item_no="38",
        pages=[30],
        effective_single_conclusion="符合",
        rows=[
            InspectionItem(
                sequence_raw="2.1.1 起搏模式",
                source_page=30,
                row_index_in_page=1,
            ),
            InspectionItem(
                test_result="符合要求",
                source_page=30,
                row_index_in_page=2,
            ),
        ],
    )

    index = build_report_subclause_index([group])

    identity = next(item for item in index.identities if item.clause_number == "2.1.1")
    assert identity.normalized_title == "起搏模式"
    assert identity.test_result == "符合要求"
    assert identity.units == []


def test_report_subclause_index_ignores_clause_number_mentioned_by_unrelated_standard_row() -> None:
    group = InspectionItemGroup(
        item_no="52",
        display_item_no="52",
        pages=[60],
        effective_single_conclusion="符合",
        rows=[
            InspectionItem(
                sequence_raw="52",
                sequence=52,
                standard_clause="7.9",
                item_name="随附文件",
                standard_requirement="外部标准随附文件中引用 2.2.3 脉冲上升时间。",
                test_result="符合要求",
                conclusion="符合",
                source_page=60,
                row_index_in_page=1,
            )
        ],
    )

    index = build_report_subclause_index([group])

    assert not any(identity.clause_number == "2.2.3" for identity in index.identities)


def test_report_subclause_index_keeps_page_header_when_result_line_is_compact() -> None:
    group = InspectionItemGroup(
        item_no="157",
        display_item_no="157",
        pages=[100],
        effective_single_conclusion="符合",
        rows=[
            InspectionItem(
                sequence_raw="157",
                sequence=157,
                standard_clause="2.2",
                source_page=100,
            )
        ],
    )

    index = build_report_subclause_index(
        [group],
        page_text_by_page={
            100: "续 157\n2.2.4 脉冲下降时间\n260 PULSE3 预设\n205 PF Reversible 预设",
        },
    )

    identity = next(item for item in index.identities if item.clause_number == "2.2.4")
    assert identity.normalized_title == "脉冲下降时间"
    assert identity.source_page == 100
    assert identity.test_result is None


def test_number_mismatch_finding_is_warn_and_keeps_selected_semantic_candidate() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.9",
        number=PTRClauseNumber.from_string("2.1.9"),
        title="房室间期",
        body_text="房室间期应符合表3的要求。",
    )
    report_identity = _report_identity("2.1.8", "房室间期", units=["ms"])
    alignment = align_clause_identity(
        _ptr_identity("2.1.9", "房室间期", units=["ms"]),
        ReportSubclauseIndex(identities=[report_identity]),
    )

    findings = build_clause_identity_findings(clause, alignment, task_id="task-identity")

    assert [finding.code for finding in findings] == ["PTR_REPORT_CLAUSE_NUMBER_MISMATCH"]
    assert findings[0].severity.value == "warn"
    assert findings[0].metadata["codex_required"] is True
    assert findings[0].metadata["selected_report_clause_number"] == "2.1.8"


def test_consecutive_number_mismatches_are_aggregated_as_one_document_issue() -> None:
    clauses = []
    alignments = {}
    for ptr_number, report_number, title in [
        ("2.1.9", "2.1.8", "房室间期"),
        ("2.1.10", "2.1.9", "室后房不应期"),
        ("2.1.11", "2.1.10", "空白期"),
        ("2.1.12", "2.1.11", "最大跟踪频率"),
        ("2.1.13", "2.1.12", "产品物理特性及参数"),
    ]:
        clauses.append(
            PTRClause(
                clause_id=f"ptr-{ptr_number}",
                number=PTRClauseNumber.from_string(ptr_number),
                title=title,
                body_text=f"{title}应符合要求。",
            )
        )
        report_identity = _report_identity(report_number, title, source_row=int(report_number.split(".")[-1]))
        alignments[ptr_number] = ClauseIdentityAlignment(
            status="semantic_match_number_mismatch",
            ptr_clause_number=ptr_number,
            ptr_title=title,
            selected_report_clause_number=report_number,
            selected_report_title=title,
            selected_report_item_no=report_identity.item_no,
            selected_report_page=report_identity.source_page,
            selected_report_identity=report_identity,
            number_matches=False,
            title_matches=True,
            parameter_matches=True,
            table_row_matches=True,
            confidence="medium",
            reason="内容一致但编号不同。",
        )

    finding, groups = build_clause_sequence_offset_aggregation(clauses, alignments, task_id="task-offset")

    assert finding is not None
    assert finding.code == "PTR_CLAUSE_SEQUENCE_OFFSET"
    assert finding.metadata["offset"] == -1
    assert len(groups) == 1
    assert groups[0]["confidence"] == "high"
    assert [entry["ptr"] for entry in groups[0]["affected_clauses"]] == [
        "2.1.9",
        "2.1.10",
        "2.1.11",
        "2.1.12",
        "2.1.13",
    ]


def test_identity_mismatch_finding_is_review_candidate_not_confirmed_error() -> None:
    clause = PTRClause(
        clause_id="ptr-2.1.8",
        number=PTRClauseNumber.from_string("2.1.8"),
        title="输入阻抗",
        body_text="输入阻抗应符合表3的要求。",
    )
    alignment = align_clause_identity(
        _ptr_identity("2.1.8", "输入阻抗", units=["kΩ"]),
        ReportSubclauseIndex(identities=[_report_identity("2.1.8", "房室间期", units=["ms"])]),
    )

    findings = build_clause_identity_findings(clause, alignment, task_id="task-identity")

    assert [finding.code for finding in findings] == ["PTR_CLAUSE_IDENTITY_MISMATCH"]
    assert findings[0].severity.value == "warn"
    assert findings[0].metadata["user_facing_status"] == "needs_review"
    assert findings[0].metadata["codex_required"] is True
