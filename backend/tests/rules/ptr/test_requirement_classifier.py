from __future__ import annotations

from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, PTRTable, TableReference
from app.domain.table import CanonicalTable, ParameterRecord
from app.rules.ptr.atomic_compare import build_atomic_requirements
from app.rules.ptr.requirement_classifier import RequirementType, classify_requirement


def _clause(number: str, title: str, body: str, *, table_refs: list[str] | None = None) -> PTRClause:
    references = [
        TableReference(table_number=table_number, context=body, clause_id=f"ptr-{number}")
        for table_number in (table_refs or [])
    ]
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=PTRClauseNumber.from_string(number),
        title=title,
        body_text=body,
        full_text=f"{number} {title}\n{body}",
        table_refs=table_refs or [],
        table_references=references,
    )


def test_classifier_uses_clause_content_for_same_clause_number() -> None:
    voltage_current = _clause(
        "2.2.1",
        "心脏脉冲电场消融仪输出",
        "输出电压应不小于3333V（峰值），输出电流应不小于57A（峰值）。",
    )
    r_wave_sync = _clause(
        "2.2.1",
        "R 波同步",
        "设备应具有 R 波同步触发功能，检验结果应符合要求。",
    )

    numeric = classify_requirement(voltage_current, PTRDocument(clauses=[voltage_current]))
    functional = classify_requirement(r_wave_sync, PTRDocument(clauses=[r_wave_sync]))

    assert numeric.requirement_type == RequirementType.NUMERIC_LIMIT
    assert {requirement.atomic_id for requirement in numeric.atomic_requirements} == {
        "2.2.1:voltage",
        "2.2.1:current",
    }
    assert functional.requirement_type == RequirementType.FUNCTIONAL
    assert {requirement.atomic_id for requirement in functional.atomic_requirements} == {"2.2.1:r_wave_sync"}


def test_classifier_identifies_table_and_external_standard_requirements() -> None:
    table_clause = _clause("2.1.1", "基本频率", "应符合表2-1规定的要求。", table_refs=["2-1"])
    software_table = _clause("2.6", "软件功能", "软件功能应符合表6的要求。", table_refs=["6"])
    external = _clause("2.5", "电气安全", "应符合 GB 9706.1-2020 的要求。")
    unknown = _clause("2.9", "其他", "应满足产品技术要求。")

    assert classify_requirement(table_clause, PTRDocument(clauses=[table_clause])).requirement_type == RequirementType.TABLE_DRIVEN
    assert (
        classify_requirement(software_table, PTRDocument(clauses=[software_table])).requirement_type
        == RequirementType.SOFTWARE_FUNCTION_TABLE
    )
    assert (
        classify_requirement(external, PTRDocument(clauses=[external])).requirement_type
        == RequirementType.EXTERNAL_STANDARD_COVERAGE
    )
    assert classify_requirement(unknown, PTRDocument(clauses=[unknown])).requirement_type == RequirementType.UNKNOWN_NEEDS_REVIEW


def test_atomic_requirements_do_not_treat_all_2_2_1_clauses_as_voltage_current() -> None:
    r_wave_sync = _clause(
        "2.2.1",
        "R 波同步",
        "设备应具有 R 波同步触发功能，检验结果应符合要求。",
    )

    requirements = build_atomic_requirements(r_wave_sync, PTRDocument(clauses=[r_wave_sync]))

    assert {requirement.atomic_id for requirement in requirements} == {"2.2.1:r_wave_sync"}
    assert all(requirement.label != "电压" for requirement in requirements)
    assert all(requirement.label != "电流" for requirement in requirements)


def test_classifier_extracts_direct_waveform_numeric_requirements_from_title_body() -> None:
    voltage = _clause(
        "2.1.1",
        "电压: 标称值：1700V±100V；低电压：1345V±80V",
        "电压: 标称值：1700V±100V；低电压：1345V±80V",
    )
    pulse_width = _clause("2.1.2", "脉宽：2.76μs±0.20μs", "脉宽：2.76μs±0.20μs")
    cycles = _clause("2.1.7", "每个脉冲群中的循环数：10", "每个脉冲群中的循环数：10")

    voltage_requirements = build_atomic_requirements(voltage, PTRDocument(clauses=[voltage]))
    pulse_width_requirements = build_atomic_requirements(pulse_width, PTRDocument(clauses=[pulse_width]))
    cycle_requirements = build_atomic_requirements(cycles, PTRDocument(clauses=[cycles]))

    assert {requirement.atomic_id for requirement in voltage_requirements} == {
        "2.1.1:voltage:nominal",
        "2.1.1:voltage:low_voltage",
    }
    assert {requirement.expected_text for requirement in pulse_width_requirements} == {"2.76μs±0.20μs"}
    assert {requirement.atomic_id for requirement in cycle_requirements} == {"2.1.7:pulse_group_cycles"}


def test_classifier_creates_generic_functional_requirement_from_clause_content() -> None:
    catheter_detection = _clause(
        "2.3.1",
        "导管检测和波形/电极选择",
        "该功能允许消融仪检测兼容的 PFA 导管的连接状态，用户可以根据患者需要选择 PFA 波形。",
    )

    requirements = build_atomic_requirements(catheter_detection, PTRDocument(clauses=[catheter_detection]))

    assert {requirement.atomic_id for requirement in requirements} == {"2.3.1:functional"}
    assert requirements[0].label == "导管检测和波形/电极选择"
    assert requirements[0].operator == "functional"


def test_classifier_extracts_deviation_requirements_from_clause_content() -> None:
    work_frequency = _clause(
        "2.2.1",
        "工作频率",
        "射频治疗仪工作频率为 5MHz，偏差为±5%。",
    )
    rated_power = _clause(
        "2.2.2",
        "额定功率",
        "射频治疗仪额定负载为 100Ω 时，额定功率为 32W，偏差为±20%。",
    )
    temperature_accuracy = _clause(
        "2.2.8.2",
        "治疗电极温度测量精度",
        "治疗电极温度测量精度不大于±3℃。",
    )

    frequency = classify_requirement(work_frequency, PTRDocument(clauses=[work_frequency]))
    power = classify_requirement(rated_power, PTRDocument(clauses=[rated_power]))
    accuracy = classify_requirement(temperature_accuracy, PTRDocument(clauses=[temperature_accuracy]))

    assert frequency.requirement_type == RequirementType.NUMERIC_RANGE
    assert frequency.atomic_requirements[0].atomic_id == "2.2.1:deviation"
    assert frequency.atomic_requirements[0].operator == "deviation_within_tolerance"
    assert frequency.atomic_requirements[0].metadata["tolerance_text"] == "±5%"
    assert power.atomic_requirements[0].metadata["tolerance_text"] == "±20%"
    assert accuracy.atomic_requirements[0].atomic_id == "2.2.8.2:accuracy"
    assert accuracy.atomic_requirements[0].metadata["tolerance_text"] == "±3℃"


def test_classifier_treats_programmable_ranges_as_functional_without_inventing_numeric_limits() -> None:
    energy_setting = _clause(
        "2.2.5",
        "输出能量",
        "射频治疗仪输出能量可调等级为 1~16，步进为 1。",
    )
    measurement_range = _clause(
        "2.2.8.1",
        "治疗电极温度测量范围",
        "治疗电极温度测量范围不小于 10℃-46℃。",
    )
    cooling_range = _clause(
        "2.2.7",
        "治疗电极冷却温度调节范围",
        "Page 4 of 10 某医疗器械有限公司 治疗电极冷却温度调节范围为 15℃-25℃，步进为 5℃。",
    )

    energy = classify_requirement(energy_setting, PTRDocument(clauses=[energy_setting]))
    measurement = classify_requirement(measurement_range, PTRDocument(clauses=[measurement_range]))
    cooling = classify_requirement(cooling_range, PTRDocument(clauses=[cooling_range]))

    assert energy.requirement_type == RequirementType.FUNCTIONAL
    assert energy.atomic_requirements[0].atomic_id == "2.2.5:setting_range"
    assert energy.atomic_requirements[0].operator == "functional"
    assert "1~16" in (energy.atomic_requirements[0].expected_text or "")
    assert all(requirement.expected_value != 258 for requirement in energy.atomic_requirements)
    assert all(requirement.unit != "mJ" for requirement in energy.atomic_requirements)
    assert measurement.requirement_type == RequirementType.FUNCTIONAL
    assert measurement.atomic_requirements[0].atomic_id == "2.2.8.1:measurement_range"
    assert "10℃-46℃" in (measurement.atomic_requirements[0].expected_text or "")
    assert cooling.atomic_requirements[0].expected_text == "治疗电极冷却温度调节范围为 15℃-25℃，步进为 5℃。"


def test_classifier_splits_withstand_and_preset_torque_requirements_from_content() -> None:
    clause = _clause(
        "2.8.1.2",
        "扭矩",
        "扭矩扳手的六角轴应能承受最小 14N·cm 的扭矩，不应损坏。预置力矩应为 8.5±1.41N·cm。",
    )

    classification = classify_requirement(clause, PTRDocument(clauses=[clause]))
    requirements = {row.atomic_id: row for row in classification.atomic_requirements}

    assert classification.requirement_type == RequirementType.NUMERIC_RANGE
    assert requirements["2.8.1.2:torque_withstand"].expected_text == "至少14 N·cm且不损坏"
    assert requirements["2.8.1.2:torque_withstand"].operator == "functional"
    assert requirements["2.8.1.2:preset_torque"].expected_text == "8.5±1.41 N·cm"
    assert requirements["2.8.1.2:preset_torque"].operator == "deviation_within_tolerance"


def test_classifier_ignores_attached_table_numeric_content_for_container_and_sibling_clauses() -> None:
    parent = PTRClause(
        clause_id="ptr-2.1",
        number=PTRClauseNumber.from_string("2.1"),
        title="基本电性能指标",
        body_text="基本电性能指标\n表3 功能参数\n输入阻抗 6232 ≥40kΩ",
        table_references=[TableReference(table_number="3", reference_text="表3")],
        children_ids=["ptr-2.1.7"],
        metadata={"referenced_table_text_attached": True},
    )
    escape_interval = PTRClause(
        clause_id="ptr-2.1.7",
        number=PTRClauseNumber.from_string("2.1.7"),
        title="逸搏间期",
        body_text=(
            "逸搏间期\n心脏起搏器的逸搏间期与基本频率设置相对应，见表3的注释，允许误差：±2min⁻¹。\n"
            "表3 功能参数\n输入阻抗 6232 ≥40kΩ"
        ),
        table_references=[TableReference(table_number="3", reference_text="表3")],
        metadata={"referenced_table_text_attached": True},
    )
    document = PTRDocument(
        clauses=[parent, escape_interval],
        tables=[
            PTRTable(
                table_id="ptr-table-3",
                table_number="3",
                title="表3 功能参数",
                canonical_table=CanonicalTable(table_id="canonical-table-3"),
                referenced_by_clause_ids=["ptr-2.1"],
                metadata={"raw_rows": [["参数", "6232"], ["输入阻抗", "≥40kΩ"]]},
            )
        ],
    )

    parent_classification = classify_requirement(parent, document)
    escape_classification = classify_requirement(escape_interval, document)

    assert parent_classification.requirement_type == RequirementType.TABLE_DRIVEN
    assert parent_classification.atomic_requirements == []
    assert build_atomic_requirements(parent, document) == []
    assert escape_classification.requirement_type == RequirementType.TABLE_DRIVEN
    assert all(requirement.expected_value != 40 for requirement in escape_classification.atomic_requirements)
    assert any(requirement.operator == "deviation_within_tolerance" for requirement in escape_classification.atomic_requirements)


def test_table_driven_classifier_preserves_asymmetric_clause_local_tolerance() -> None:
    clause = _clause(
        "2.1.9",
        "房室间期（只适用于双腔起搏器）",
        "房室间期的数值应符合表3的要求，允许误差：-10/+15 ms。",
        table_refs=["3"],
    )

    classification = classify_requirement(clause, PTRDocument(clauses=[clause]))

    assert classification.requirement_type == RequirementType.TABLE_DRIVEN
    assert len(classification.atomic_requirements) == 1
    assert classification.atomic_requirements[0].expected_text == "-10/+15ms"
    assert classification.atomic_requirements[0].operator == "deviation_within_tolerance"


def test_software_table_selection_ignores_attached_waveform_table_text() -> None:
    clause = _clause("2.6", "软件功能", "软件功能应符合表6的要求。", table_refs=["6"])
    clause.full_text = (
        f"{clause.full_text}\n"
        "表6 波形参数\n脉冲个数 PULSE3 1500 PF Reversible 1"
    )
    clause.metadata["referenced_table_text_attached"] = True
    document = PTRDocument(
        clauses=[clause],
        tables=[
            PTRTable(
                table_id="waveform-table-6",
                table_number="6",
                title="表6 波形参数",
                canonical_table=CanonicalTable(
                    table_id="canonical-waveform-table-6",
                    parameter_records=[
                        ParameterRecord(
                            parameter_name="脉冲个数",
                            values={"PULSE3": "1500", "PF Reversible": "1"},
                        )
                    ],
                ),
                metadata={"parent_clause": "2.2.2"},
            ),
            PTRTable(
                table_id="software-table-6",
                table_number="6",
                title="表6 软件功能",
                canonical_table=CanonicalTable(
                    table_id="canonical-software-table-6",
                    parameter_records=[
                        ParameterRecord(
                            parameter_name="功率监测",
                            dimensions={"组件": "射频消融仪"},
                            values={"要求": "具备"},
                        )
                    ],
                ),
                referenced_by_clause_ids=["ptr-2.6"],
                metadata={"parent_clause": "2.6"},
            ),
        ],
    )

    requirements = build_atomic_requirements(clause, document)

    assert [requirement.label for requirement in requirements] == ["射频消融仪 - 功率监测"]
    assert {requirement.table_title for requirement in requirements} == {"软件功能"}
    assert {requirement.table_key for requirement in requirements} == {"2.6:表6:软件功能"}
    assert all("pulse" not in requirement.atomic_id for requirement in requirements)
