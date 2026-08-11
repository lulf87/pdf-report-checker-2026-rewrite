from __future__ import annotations

from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument
from app.domain.ptr_comparison import ClauseIdentityAlignment, PTRAtomicComparisonRow, PTRAtomicRequirement
from app.domain.report import InspectionItem
from app.rules.ptr.comparison_trace import build_comparison_trace


def _clause(number: str, title: str, body: str) -> PTRClause:
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=PTRClauseNumber.from_string(number),
        title=title,
        body_text=body,
    )


def _trace(
    clause: PTRClause,
    requirement: PTRAtomicRequirement,
    row: PTRAtomicComparisonRow,
):
    return build_comparison_trace(
        clause=clause,
        ptr_doc=PTRDocument(clauses=[clause]),
        report_matches=[],
        atomic_requirements=[requirement],
        atomic_rows=[row],
        findings=[],
        external_coverages=[],
    )


def test_numeric_requirement_with_only_report_conclusion_is_not_numeric_verified() -> None:
    clause = _clause("2.6", "环氧乙烷残留量", "环氧乙烷残留量应不超过10μg/g。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.6:limit",
        clause_id="2.6",
        label="环氧乙烷残留量",
        expected_text="≤10 μg/g",
        expected_value=10,
        operator="<=",
        unit="μg/g",
        metadata={"numeric_limit": True},
    )
    row = PTRAtomicComparisonRow(
        atomic_id="2.6:limit",
        clause_id="2.6",
        label="环氧乙烷残留量",
        expected="≤10 μg/g",
        actual="符合要求",
        unit="μg/g",
        status="match",
        reason="报告结论符合。",
        report_item_no="40",
        report_page=10,
        source="ptr_text",
        source_text="环氧乙烷残留量应不超过10μg/g。",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_comparisons[0].status == "pass_by_report_conclusion"
    assert trace.result_comparisons[0].verification_basis == "pass_by_report_conclusion"
    assert trace.result_compliance.status == "needs_review"


def test_requirement_alignment_reports_clear_numeric_limit_mismatch() -> None:
    clause = _clause("2.6", "环氧乙烷残留量", "环氧乙烷残留量应不超过10μg/g。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.6:limit",
        clause_id="2.6",
        label="环氧乙烷残留量",
        expected_text="≤10 μg/g",
        expected_value=10,
        operator="<=",
        unit="μg/g",
        metadata={"numeric_limit": True},
    )
    row = PTRAtomicComparisonRow(
        atomic_id="2.6:limit",
        clause_id="2.6",
        label="环氧乙烷残留量",
        expected="≤10 μg/g",
        actual="<0.5",
        unit="μg/g",
        status="match",
        reason="实测值满足限值。",
        report_item_no="40",
        report_page=10,
        source="ptr_text",
        source_text="环氧乙烷残留量应不超过20μg/g。",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "mismatch"
    assert trace.result_compliance.status == "match"


def test_functional_requirement_can_pass_by_report_conclusion() -> None:
    clause = _clause("2.2.1", "R波同步", "设备应具备R波同步功能。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.2.1:r_wave_sync",
        clause_id="2.2.1",
        label="R波同步",
        expected_text="设备应具备R波同步功能。",
        operator="functional",
    )
    row = PTRAtomicComparisonRow(
        atomic_id="2.2.1:r_wave_sync",
        clause_id="2.2.1",
        label="R波同步",
        expected="设备应具备R波同步功能。",
        actual="符合要求",
        status="match",
        reason="报告功能结论符合。",
        report_item_no="158",
        report_page=20,
        source="ptr_text",
        source_text="设备应具备R波同步功能。",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_comparisons[0].verification_basis == "functional_conclusion"
    assert trace.result_compliance.status == "match"


def test_table_setting_list_can_pass_by_equivalent_requirement_and_report_conclusion() -> None:
    clause = _clause("2.1.5", "心房灵敏度", "心房灵敏度应符合表3的要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.1.5:table3:atrial_sensitivity",
        clause_id="2.1.5",
        label="心房灵敏度",
        expected_text="0.1-0.2-0.3-0.4-0.6-0.8-1-1.2-1.5mV 出厂值1mV",
        source="ptr_table",
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.1.5",
        label="心房灵敏度",
        expected=requirement.expected_text,
        actual="符合要求",
        status="match",
        report_item_no="38",
        report_page=28,
        source="ptr_table",
        source_text="心房灵敏度：0.1-0.2-0.3-0.4-0.6-0.8-1-1.2-1.5mV 出厂值1mV",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_comparisons[0].status == "pass_by_report_conclusion"
    assert trace.result_compliance.status == "match"


def test_parent_container_does_not_require_independent_result_when_it_has_children() -> None:
    clause = _clause("2.1", "基本电性能指标", "基本电性能指标。")
    clause.children_ids = ["ptr-2.1.1"]
    requirement = PTRAtomicRequirement(
        atomic_id="2.1:local",
        clause_id="2.1",
        label="基本电性能指标",
        expected_text="基本电性能指标",
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.1",
        label="基本电性能指标",
        expected=requirement.expected_text,
        actual=None,
        status="needs_review",
        source="ptr_text",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "not_applicable"
    assert trace.result_compliance.status == "not_applicable"


def test_external_standard_year_difference_requires_policy_review() -> None:
    clause = _clause("2.10", "通用要求", "应符合 GB 16174.1-2015 的要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.10:standard",
        clause_id="2.10",
        label="通用要求",
        expected_text="应符合 GB 16174.1-2015 的要求。",
    )

    trace = build_comparison_trace(
        clause=clause,
        ptr_doc=PTRDocument(clauses=[clause]),
        report_matches=[],
        atomic_requirements=[requirement],
        atomic_rows=[],
        findings=[],
        external_coverages=[
            {
                "standard": "GB 16174.1-2024",
                "start_item_no": "1",
                "end_item_no": "24",
                "passed_count": 24,
                "review_count": 0,
            }
        ],
    )

    assert trace.requirement_alignment.status == "needs_policy_review"
    assert "2015" in trace.requirement_alignment.reason
    assert "2024" in trace.requirement_alignment.reason


def test_table_range_requirement_matches_chinese_bound_expression() -> None:
    clause = _clause("2.8.2", "扭矩扳手尺寸", "扭矩扳手金属杆头截面尺寸应符合要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.8.2:torque_wrench:A",
        clause_id="2.8.2",
        label="A",
        expected_text="0.88～0.89 mm",
        source="ptr_table",
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.8.2",
        label="A",
        expected=requirement.expected_text,
        actual="0.884",
        unit="mm",
        status="match",
        reason="实测尺寸满足范围。",
        report_item_no="54",
        report_page=33,
        source="ptr_table",
        source_text="0.88 毫米≤A≤0.89 毫米；单位：mm",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_compliance.status == "match"


def test_composite_tolerance_requires_all_numeric_tokens_and_units() -> None:
    clause = _clause("2.1.4", "心室感知灵敏度", "应符合表2-1规定的要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.1.4:sensitivity:tolerance",
        clause_id="2.1.4",
        label="允差",
        expected_text="-16%/+56% 或 ±0.3 mV，两者取较大值",
        source="ptr_table",
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.1.4",
        label="允差",
        expected=requirement.expected_text,
        actual="+38%～+46%",
        unit="%",
        status="match",
        reason="实测偏差满足允差。",
        report_item_no="41",
        report_page=29,
        source="ptr_table",
        source_text="1.0mV、1.5mV：-0.3mV/+56%；2.0mV～12.5mV：-16%/+56%",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_compliance.status == "match"


def test_table_numeric_requirement_with_only_group_conclusion_needs_review() -> None:
    clause = _clause("2.1.8", "输入阻抗", "输入阻抗应符合表3的要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.1.8:table3:input_impedance:6232",
        clause_id="2.1.8",
        label="输入阻抗",
        expected_text="≥40kΩ",
        source="ptr_table",
        metadata={"model_column": "6232"},
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.1.8",
        label="输入阻抗",
        expected=requirement.expected_text,
        actual="符合要求",
        status="match",
        reason="报告大组结论符合。",
        report_item_no="38",
        report_page=27,
        source="ptr_table",
        source_text="2.1.8 房室间期应符合表3的要求。",
    )

    trace = _trace(clause, requirement, row)

    assert trace.report_requirement_matches == []
    assert trace.requirement_alignment.status == "needs_review"
    assert trace.result_comparisons[0].verification_basis == "pass_by_report_conclusion"
    assert trace.result_compliance.status == "needs_review"


def test_identity_mismatch_blocks_parent_group_conclusion_and_atomic_match() -> None:
    clause = _clause("2.1.8", "输入阻抗", "输入阻抗应符合表3的要求。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.1.8:table3:input_impedance:6232",
        clause_id="2.1.8",
        label="输入阻抗",
        expected_text="≥40kΩ",
        source="ptr_table",
        metadata={"model_column": "6232"},
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.1.8",
        label="输入阻抗",
        expected="≥40kΩ",
        actual="-1～+0",
        unit="ms",
        status="match",
        report_clause_number="2.1.8",
        report_item_no="38",
        source="ptr_table",
        source_text="2.1.8 房室间期；大组结论符合。",
    )
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
                standard_requirement="2.1.8 房室间期应符合表3的要求。",
                test_result="符合",
                conclusion="符合",
                source_page=30,
            )
        ],
    )
    identity = ClauseIdentityAlignment(
        status="identity_mismatch",
        ptr_clause_number="2.1.8",
        ptr_title="输入阻抗",
        reason="报告同编号条款为房室间期。",
        confidence="high",
    )

    trace = build_comparison_trace(
        clause=clause,
        ptr_doc=PTRDocument(clauses=[clause]),
        report_matches=[group],
        atomic_requirements=[requirement],
        atomic_rows=[row],
        findings=[],
        external_coverages=[],
        clause_identity_alignment=identity,
    )

    assert trace.clause_identity_alignment.status == "identity_mismatch"
    assert trace.report_requirement_matches == []
    assert trace.result_comparisons == []
    assert trace.requirement_alignment.status == "needs_review"
    assert trace.result_compliance.status == "needs_review"


def test_numeric_actual_without_report_limit_is_not_a_requirement_mismatch() -> None:
    clause = _clause("2.2.4", "脉冲下降时间", "脉冲下降时间应不超过700ns。")
    requirement = PTRAtomicRequirement(
        atomic_id="2.2.4:fall_time:pulse3",
        clause_id="2.2.4",
        label="脉冲下降时间",
        expected_text="≤700 ns",
        expected_value=700,
        operator="<=",
        unit="ns",
    )
    row = PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id="2.2.4",
        label="脉冲下降时间",
        expected=requirement.expected_text,
        actual="260",
        unit="ns",
        status="match",
        reason="实测值满足限值。",
        report_item_no="157",
        report_page=100,
        source="ptr_text",
        source_text="2.2.4 脉冲下降时间 260 PULSE3 单项结论符合",
    )

    trace = _trace(clause, requirement, row)

    assert trace.requirement_alignment.status == "needs_review"
    assert trace.result_compliance.status == "match"


def test_structured_only_modifier_narrows_direct_table_statement_and_uses_functional_result() -> None:
    clause = _clause(
        "2.3",
        "特殊功能",
        "应符合表2-2的要求。PVC 反应 / PVC Response：应支持。MR Conditional：应支持。",
    )
    group = InspectionItemGroup(
        item_no="51",
        display_item_no="51",
        pages=[21],
        rows=[
            InspectionItem(
                sequence_raw="51",
                sequence=51,
                standard_clause="2.3",
                item_name="特殊功能",
                standard_requirement="特殊功能；PVC 反应 / PVC Response：应支持。",
                test_result="符合要求",
                conclusion="符合",
                source_page=21,
            )
        ],
    )

    trace = build_comparison_trace(
        clause=clause,
        ptr_doc=PTRDocument(clauses=[clause]),
        report_matches=[group],
        atomic_requirements=[],
        atomic_rows=[],
        findings=[],
        external_coverages=[],
        scope_modifiers=[
            {
                "clause": "2.3",
                "only": ["PVC 反应", "PVC Response"],
                "source_text": "仅检 PVC 反应",
            }
        ],
    )

    assert len(trace.effective_requirements) == 1
    assert "PVC" in trace.effective_requirements[0].label
    assert "MR Conditional" not in str(trace.effective_requirements[0].expected)
    assert all("PVC" in row.standard_requirement_text for row in trace.report_requirement_matches)
    assert trace.requirement_alignment.status == "equivalent"
    assert trace.result_comparisons[0].actual == "符合要求"
    assert trace.result_comparisons[0].verification_basis == "functional_conclusion"
    assert trace.result_compliance.status == "match"
