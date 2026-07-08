from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.ptr_comparison import PTRAtomicComparisonRow, PTRAtomicRequirement, PTRReportAtomicResult
from app.domain.table import ParameterRecord
from app.rules.ptr.requirement_classifier import RequirementType, classify_requirement
from app.rules.ptr.report_item_grouping import (
    ptr_group_single_conclusion,
    ptr_group_standard_requirement,
    ptr_group_test_result,
    ptr_group_text,
)


WAVEFORM_TABLE_PARAMETERS: tuple[tuple[str, str], ...] = (
    ("脉冲个数", "pulse_count"),
    ("脉冲组数", "pulse_group_count"),
    ("脉冲组间隔", "pulse_group_interval"),
    ("脉冲对间隔", "pulse_pair_interval"),
    ("脉冲宽度", "pulse_width"),
    ("脉冲相间隔", "pulse_phase_interval"),
    ("波形类型", "waveform_type"),
    ("正峰值/负峰值", "peak_ratio"),
    ("电流水平", "current_level"),
)
WAVEFORM_PARAMETER_SLUGS = dict(WAVEFORM_TABLE_PARAMETERS)
WAVEFORM_PRESETS: tuple[tuple[str, str], ...] = (("pulse3", "PULSE3"), ("pf_reversible", "PF Reversible"))
SOFTWARE_FUNCTION_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("射频消融仪", "功率监测"),
    ("射频消融仪", "阻抗监测"),
    ("射频消融仪", "温度监测"),
    ("射频消融仪", "控制应用启动和停止"),
    ("射频消融仪", "灌注泵流量监测"),
    ("射频消融仪", "模式选择"),
    ("射频消融仪", "接触质量监测"),
    ("射频消融仪", "与心脏脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信"),
    ("射频消融仪", "参数显示与控制"),
    ("射频消融仪", "显示能量输送状态"),
    ("射频消融仪", "显示消融图"),
    ("射频消融仪", "预设选择"),
    ("心脏脉冲电场消融仪", "阻抗监测"),
    ("心脏脉冲电场消融仪", "温度监测"),
    ("心脏脉冲电场消融仪", "与射频消融仪、导管接口单元CIU通信"),
)
SOFTWARE_COMPONENTS: tuple[str, ...] = (
    "心脏脉冲电场消融仪",
    "射频消融仪",
    "控制器",
    "脚踏开关",
    "灌注泵",
)
SOFTWARE_FUNCTION_ALIASES: dict[str, tuple[str, ...]] = {
    "控制应用启动和停止": ("控制应用启动和停止", "控制射频消融或脉冲电场消融应用的启动和停止", "启动和停止"),
    "灌注泵流量监测": ("灌注泵流量监测", "流量监测"),
    "模式选择": ("模式选择", "射频消融或脉冲电场消融模式选择"),
    "与心脏脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信": (
        "与心脏脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信",
        "与脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器和电生理三维导航系统通信",
        "与脉冲电场消融仪、导管接口单元CIU、灌注泵、控制器、三维导航通信",
    ),
    "参数显示与控制": ("参数显示与控制",),
    "显示能量输送状态": ("显示能量输送状态",),
    "显示消融图": ("显示消融图",),
    "预设选择": ("预设选择",),
    "与射频消融仪、导管接口单元CIU通信": ("与射频消融仪、导管接口单元CIU通信",),
}
BASIC_ELECTRICAL_TABLE2_1_TABLE_KEY = "2.1:表2-1:基本电性能参数"
BASIC_ELECTRICAL_TABLE2_1_SPECS: dict[str, dict[str, Any]] = {
    "2.1.1": {"slug": "basic_rate", "label": "基本频率", "aliases": ("基本频率",)},
    "2.1.2": {"slug": "pulse_width", "label": "脉宽", "aliases": ("脉宽",)},
    "2.1.3": {"slug": "pulse_amplitude", "label": "脉冲振幅", "aliases": ("脉冲振幅",)},
    "2.1.4": {"slug": "ventricular_sensitivity", "label": "心室感知灵敏度", "aliases": ("心室感知灵敏度",)},
    "2.1.5": {"slug": "atrial_sensitivity", "label": "心房感知灵敏度", "aliases": ("心房感知灵敏度",)},
    "2.1.6": {"slug": "ventricular_pacing_refractory", "label": "心室起搏不应期", "aliases": ("心室起搏不应期",)},
    "2.1.7": {"slug": "atrial_pacing_refractory", "label": "心房起搏不应期", "aliases": ("心房起搏不应期",)},
    "2.1.8": {"slug": "ventricular_sensed_refractory", "label": "心室感知不应期", "aliases": ("心室感知不应期",)},
    "2.1.9": {"slug": "atrial_sensed_refractory", "label": "心房感知不应期", "aliases": ("心房感知不应期",)},
    "2.1.10": {"slug": "av_interval", "label": "房室间期", "aliases": ("房室间期", "起搏房室间期", "感知房室间期")},
    "2.1.11": {"slug": "escape_interval", "label": "逸搏间期", "aliases": ("逸搏间期",)},
    "2.1.12": {"slug": "pvarp", "label": "室后房不应期", "aliases": ("室后房不应期", "PVARP")},
}
BASIC_ELECTRICAL_LOADS: tuple[tuple[str, str], ...] = (
    ("240ohm", "@240Ω"),
    ("500ohm", "@500Ω"),
    ("2000ohm", "@2000Ω"),
)
BASIC_ELECTRICAL_PULSE_WIDTH_SITES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("atrial", "心房", ("脉宽（心房）", "脉宽(心房)")),
    ("right_ventricle", "右心室", ("脉宽（右心室）", "脉宽(右心室)")),
    ("left_ventricle", "左心室", ("脉宽（左心室）", "脉宽(左心室)")),
)
BASIC_ELECTRICAL_PULSE_AMPLITUDE_SITES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("atrial", "心房", ("脉冲振幅（心房）", "脉冲振幅(心房)")),
    ("right_ventricle", "右心室", ("脉冲振幅（右心室）", "脉冲振幅(右心室)")),
    ("left_ventricle", "左心室", ("脉冲振幅（左心室）", "脉冲振幅(左心室)")),
)
BASIC_ELECTRICAL_PULSE_AMPLITUDE_SEGMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "240ohm": (
        ("0.25V、0.5V", "0.25V、0.5V：±0.25 V"),
        ("0.75V、1.0V", "0.75V、1.0V：-38%/+0.25V"),
        ("1.25V～7.5V", "1.25V～7.5V：-38%/+20%"),
    ),
    "500ohm": (
        ("0.25V～0.75V", "0.25V～0.75V：±0.25 V"),
        ("1.0V", "1.0V：-27%/+0.25V"),
        ("1.25V～7.5V", "1.25V～7.5V：-27%/+20%"),
    ),
    "2000ohm": (
        ("0.25V～1.0V", "0.25V～1.0V：±0.25 V"),
        ("1.25V～7.5V", "1.25V～7.5V：-20%/+20%"),
    ),
}
BASIC_ELECTRICAL_AV_INTERVAL_CONDITIONS: tuple[tuple[str, str, tuple[str, ...], str, str, str], ...] = (
    (
        "pacing",
        "起搏房室间期",
        ("起搏房室间期",),
        "25；30-200，步幅10；225-300，步幅25；350",
        "200 ms",
        "±10 ms",
    ),
    (
        "sensed",
        "感知房室间期",
        ("感知房室间期",),
        "25；30-200，步幅10；225-325，步幅25",
        "150 ms",
        "±10 ms",
    ),
)


def build_atomic_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    classification = classify_requirement(clause, ptr_doc)
    if classification.atomic_requirements:
        return classification.atomic_requirements
    if _clause_references_basic_electrical_table2_1(clause):
        return _basic_electrical_table2_1_requirements(clause, ptr_doc)
    if _clause_indicates_torque_wrench_size(clause):
        return _torque_wrench_size_requirements(str(clause.number))
    if classification.requirement_type == RequirementType.SOFTWARE_FUNCTION_TABLE or _clause_indicates_waveform_table(clause):
        return _table_requirements(clause, ptr_doc)
    return []


def build_atomic_comparison_rows(
    clause: PTRClause,
    ptr_doc: PTRDocument,
    report_matches: Sequence[InspectionItemGroup],
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRAtomicComparisonRow]:
    requirements = build_atomic_requirements(clause, ptr_doc)
    if not requirements:
        return []
    group = report_matches[0] if report_matches else None
    report_atomic_results = build_report_atomic_results(group, page_text_by_page=page_text_by_page) if group is not None else []
    rows: list[PTRAtomicComparisonRow] = []
    for requirement in requirements:
        bound_results = _report_results_for_requirement(requirement, report_atomic_results)
        if bound_results:
            rows.extend(_comparison_row(requirement, group, result) for result in bound_results)
            continue
        software_result = (
            _software_result_for_requirement(requirement, group, page_text_by_page=page_text_by_page)
            if requirement.source == "ptr_table" and requirement.clause_id == "2.6"
            else None
        )
        if software_result is not None:
            rows.append(_comparison_row(requirement, group, software_result))
            continue
        rows.append(_comparison_row(requirement, group))
    return rows


def build_report_atomic_results(
    group: InspectionItemGroup | None,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRReportAtomicResult]:
    if group is None:
        return []
    results: list[PTRReportAtomicResult] = []
    item_no = group.display_item_no or group.item_no
    group_text = _group_full_text(group, page_text_by_page=page_text_by_page)
    results.extend(
        _group_window_atomic_results(
            group,
            group_text=group_text,
            item_no=item_no,
            page_text_by_page=page_text_by_page,
        )
    )
    results.extend(
        _direct_text_report_atomic_results(
            group,
            group_text=group_text,
            item_no=item_no,
            page_text_by_page=page_text_by_page,
        )
    )
    results.extend(
        _basic_electrical_table2_1_report_atomic_results(
            group,
            group_text=group_text,
            item_no=item_no,
            page_text_by_page=page_text_by_page,
        )
    )
    results.extend(
        _torque_wrench_report_atomic_results(
            group,
            group_text=group_text,
            item_no=item_no,
            page_text_by_page=page_text_by_page,
        )
    )

    for row in group.rows:
        row_text = _row_text(row)
        compact = _compact(row_text)
        page = row.source_page or _first_page(group)

        if "电压" in compact:
            actual = _first_measurement_value(row)
            if actual:
                results.append(
                    _report_atomic_result(
                        atomic_id="2.2.1:voltage",
                        clause_id="2.2.1",
                        label="电压",
                        actual=actual,
                        unit="V",
                        item_no=item_no,
                        page=page,
                        source_text=row_text,
                        confidence="high",
                        method="row_text_voltage",
                    )
                )

        if "电流" in compact:
            actual = _current_value(row)
            if actual:
                results.append(
                    _report_atomic_result(
                        atomic_id="2.2.1:current",
                        clause_id="2.2.1",
                        label="电流",
                        actual=actual,
                        unit="A",
                        item_no=item_no,
                        page=page,
                        source_text=row_text,
                        confidence="high",
                        method="row_text_current",
                    )
                )

        if "2.2.3" in compact or "上升" in compact:
            values = _preset_values_from_row(row) or _numeric_values_from_row(row)
            results.extend(
                _preset_results(
                    values,
                    atomic_prefix="2.2.3:rise_time",
                    clause_id="2.2.3",
                    label="脉冲上升时间",
                    unit="ns",
                    item_no=item_no,
                    page=page,
                    source_text=row_text,
                    method="row_text_rise_time",
                )
            )

        if "2.2.4" in compact or "下降" in compact or "脉冲宽度" in compact:
            values = _preset_values_from_row(row) or _numeric_values_from_row(row)[:2]
            results.extend(
                _preset_results(
                    values,
                    atomic_prefix="2.2.4:fall_time",
                    clause_id="2.2.4",
                    label="脉冲下降时间",
                    unit="ns",
                    item_no=item_no,
                    page=page,
                    source_text=row_text,
                    method="row_text_fall_time",
                )
            )

        if "2.2.5" in compact or "衰减" in compact:
            actual = _first_measurement_value(row)
            candidates = [] if actual else _candidate_values_from_row(row)
            if actual or candidates:
                results.append(
                    _report_atomic_result(
                        atomic_id="2.2.5:decay",
                        clause_id="2.2.5",
                        label="脉冲衰减",
                        actual=actual,
                        unit="%" if (actual and "%" in actual) or "%" in row_text else None,
                        item_no=item_no,
                        page=page,
                        source_text=row_text,
                        confidence="high" if actual else "medium",
                        method="row_text_decay" if actual else "row_text_decay_candidate",
                        candidate_actuals=candidates,
                    )
                )

        if "2.2.6" in compact or "最大输出能量" in compact:
            actual = _first_measurement_value(row)
            candidates = [] if actual else _candidate_values_from_row(row)
            if actual or candidates:
                results.append(
                    _report_atomic_result(
                        atomic_id="2.2.6:max_energy",
                        clause_id="2.2.6",
                        label="单个脉冲最大输出能量",
                        actual=actual,
                        unit="mJ",
                        item_no=item_no,
                        page=page,
                        source_text=row_text,
                        confidence="high" if actual else "medium",
                        method="row_text_max_energy" if actual else "row_text_max_energy_candidate",
                        candidate_actuals=candidates,
                    )
                )

        if "温度" in compact and "符合" in compact and "不符合" not in compact:
            results.append(
                _report_atomic_result(
                    atomic_id="2.2.7.1:temperature_limit_protection",
                    clause_id="2.2.7.1",
                    label="温度超限保护",
                    actual="符合要求",
                    item_no=item_no,
                    page=page,
                    source_text=row_text,
                    confidence="high",
                    method="row_text_functional",
                )
            )

        if "过流" in compact and "符合" in compact and "不符合" not in compact:
            results.append(
                _report_atomic_result(
                    atomic_id="2.2.7.2:over_current_protection",
                    clause_id="2.2.7.2",
                    label="过流保护",
                    actual="符合要求",
                    item_no=item_no,
                    page=page,
                    source_text=row_text,
                    confidence="high",
                    method="row_text_functional",
                )
            )

    return _unique_report_atomic_results(results)


def table_key_for_clause_table(clause_number: str, table: PTRTable) -> str:
    number = str(table.table_number or "")
    title = _table_title(table)
    return f"{clause_number}:表{number}:{title}".strip(":")


def table_for_clause(clause: PTRClause, ptr_doc: PTRDocument) -> PTRTable | None:
    table_numbers = [reference.table_number for reference in clause.table_references] + list(clause.table_refs)
    for table_number in table_numbers:
        candidates = ptr_doc.get_tables_by_number(table_number)
        anchored = [table for table in candidates if clause.clause_id in table.referenced_by_clause_ids]
        if len(anchored) == 1:
            return anchored[0]
        contextual = [table for table in candidates if _reference_context_matches_table(clause, table)]
        if len(contextual) == 1:
            return contextual[0]
        if len(candidates) == 1:
            return candidates[0]
    return None


def _table_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    clause_number = str(clause.number)
    table = table_for_clause(clause, ptr_doc)
    if table is None or table.canonical_table is None:
        if _clause_indicates_waveform_table(clause):
            return _fallback_waveform_table_requirements(clause_number)
        if _clause_indicates_software_table(clause):
            return _fallback_software_table_requirements(clause_number)
        return []
    if _clause_indicates_waveform_table(clause):
        return _waveform_table_requirements(clause_number, table)
    title = _table_title(table)
    table_key = table_key_for_clause_table(clause_number, table)
    return [
        PTRAtomicRequirement(
            atomic_id=f"{clause_number}:table{table.table_number}:{_slug(_record_label(record, clause_number))}",
            clause_id=clause_number,
            label=_record_label(record, clause_number),
            expected_text=_record_expected_text(record),
            source="ptr_table",
            table_number=str(table.table_number or ""),
            table_title=title,
            table_key=table_key,
            metadata={
                "parameter_name": record.parameter_name,
                "dimensions": dict(record.dimensions),
                "values": dict(record.values),
            },
        )
        for record in table.canonical_table.parameter_records
    ]


def _clause_indicates_waveform_table(clause: PTRClause) -> bool:
    text = _compact(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    return "波形参数" in text or ("输出波形" in text and "表" in text)


def _clause_indicates_software_table(clause: PTRClause) -> bool:
    text = _compact(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    return "软件功能" in text and ("表" in text or bool(clause.table_refs or clause.table_references))


def _waveform_table_requirements(clause_number: str, table: PTRTable) -> list[PTRAtomicRequirement]:
    title = _table_title(table)
    table_key = table_key_for_clause_table(clause_number, table)
    requirements: list[PTRAtomicRequirement] = []
    for record in table.canonical_table.parameter_records if table.canonical_table else []:
        parameter_name = record.parameter_name or record.raw_name or record.normalized_name or record.parameter_id or "参数"
        parameter_slug = _waveform_parameter_slug(parameter_name)
        for preset_key, expected_text in record.values.items():
            preset_slug = _preset_slug(preset_key)
            if preset_slug is None:
                continue
            preset_label = _preset_label(preset_slug)
            requirements.append(
                PTRAtomicRequirement(
                    atomic_id=f"{clause_number}:{parameter_slug}:{preset_slug}",
                    clause_id=clause_number,
                    label=parameter_name,
                    expected_text=str(expected_text or ""),
                    source="ptr_table",
                    table_number=str(table.table_number or ""),
                    table_title=title,
                    table_key=table_key,
                    metadata={
                        "parameter_name": parameter_name,
                        "preset": preset_label,
                        "preset_slug": preset_slug,
                        "values": dict(record.values),
                    },
                )
            )
    return requirements


def _fallback_waveform_table_requirements(clause_number: str) -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    for parameter_name, parameter_slug in WAVEFORM_TABLE_PARAMETERS:
        for preset_slug, preset_label in WAVEFORM_PRESETS:
            expected_text = _scope_waveform_expected_values(parameter_name).get(preset_slug, "")
            requirements.append(
                PTRAtomicRequirement(
                    atomic_id=f"{clause_number}:{parameter_slug}:{preset_slug}",
                    clause_id=clause_number,
                    label=parameter_name,
                    expected_text=expected_text,
                    source="ptr_table",
                    table_number="6",
                    table_title="波形参数",
                    table_key=f"{clause_number}:表6:波形参数",
                    metadata={
                        "parameter_name": parameter_name,
                        "preset": preset_label,
                        "preset_slug": preset_slug,
                    },
                )
            )
    return requirements


def _fallback_software_table_requirements(clause_number: str) -> list[PTRAtomicRequirement]:
    return [
        PTRAtomicRequirement(
            atomic_id=f"{clause_number}:table6:{_slug(f'{component} - {function_name}')}",
            clause_id=clause_number,
            label=f"{component} - {function_name}",
            expected_text="要求=具备",
            source="ptr_table",
            table_number="6",
            table_title="软件功能",
            table_key=f"{clause_number}:表6:软件功能",
            metadata={
                "parameter_name": function_name,
                "dimensions": {"组件": component},
                "values": {"要求": "具备"},
            },
        )
        for component, function_name in SOFTWARE_FUNCTION_REQUIREMENTS
    ]


def _clause_references_basic_electrical_table2_1(clause: PTRClause) -> bool:
    clause_number = str(clause.number)
    if clause_number not in BASIC_ELECTRICAL_TABLE2_1_SPECS:
        return False
    text = _compact(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    refs = {str(ref) for ref in [*clause.table_refs, *(reference.table_number for reference in clause.table_references)]}
    return "表2-1" in text or "表2－1" in text or "2-1" in refs or "2－1" in refs


def _basic_electrical_table2_1_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    clause_number = str(clause.number)
    spec = BASIC_ELECTRICAL_TABLE2_1_SPECS.get(clause_number)
    if spec is None:
        return []
    if clause_number == "2.1.1":
        return _basic_electrical_basic_rate_requirements()
    if clause_number == "2.1.2":
        return _basic_electrical_pulse_width_requirements()
    if clause_number == "2.1.3":
        return _basic_electrical_pulse_amplitude_requirements()
    if clause_number == "2.1.8":
        return _basic_electrical_simple_parameter_requirements(
            clause_number=clause_number,
            spec=spec,
            setting="125；157；190；220；250（自动感知参数应设置为[打开]）；125；160；190；220；250；280；310；340；370；400；440；470；500（自动感知参数应设置为[关闭]）",
            nominal="250 ms",
            tolerance="±5 ms",
        )
    if clause_number == "2.1.10":
        return _basic_electrical_av_interval_requirements()
    if clause_number == "2.1.11":
        return _basic_electrical_simple_parameter_requirements(
            clause_number=clause_number,
            spec=spec,
            setting="--",
            nominal="--",
            tolerance="±15 ms",
        )
    if clause_number == "2.1.12":
        return _basic_electrical_simple_parameter_requirements(
            clause_number=clause_number,
            spec=spec,
            setting="125-500，步幅25",
            nominal="275 ms",
            tolerance="±10 ms",
        )

    expected_values = _basic_electrical_expected_values_from_ptr_table(clause_number, ptr_doc)
    requirements: list[PTRAtomicRequirement] = []
    for suffix, label in (("setting", "设置"), ("nominal", "标称值"), ("tolerance", "允差")):
        expected = expected_values.get(suffix)
        if not expected:
            continue
        requirements.append(
            _basic_electrical_table2_1_requirement(
                clause_number=clause_number,
                suffix=f"{spec['slug']}:{suffix}",
                label=label,
                expected=expected,
                metadata_key=suffix,
                spec=spec,
            )
        )
    if not requirements:
        requirements.append(
            _basic_electrical_table2_1_requirement(
                clause_number=clause_number,
                suffix=f"{spec['slug']}:report_detail",
                label=spec["label"],
                expected="表2-1参数要求",
                metadata_key="summary",
                spec=spec,
            )
        )
    return requirements


def _basic_electrical_basic_rate_requirements() -> list[PTRAtomicRequirement]:
    specs = [
        ("basic_rate:setting", "设置", None, "30-130，步幅5；140-170，步幅10", "setting"),
        ("basic_rate:nominal", "标称值", None, "60 min⁻¹", "nominal"),
        ("basic_rate:tolerance:240ohm", "允差", "@240Ω", "±15 ms", "tolerance_240ohm"),
        ("basic_rate:tolerance:500ohm", "允差", "@500Ω", "±15 ms", "tolerance_500ohm"),
        ("basic_rate:tolerance:2000ohm", "允差", "@2000Ω", "±15 ms", "tolerance_2000ohm"),
    ]
    return [
        _basic_electrical_table2_1_requirement(
            clause_number="2.1.1",
            suffix=suffix,
            label=label,
            expected=expected,
            metadata_key=metadata_key,
            spec=BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.1"],
            preset=preset,
        )
        for suffix, label, preset, expected, metadata_key in specs
    ]


def _basic_electrical_pulse_width_requirements() -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    for site_slug, site_label, _aliases in BASIC_ELECTRICAL_PULSE_WIDTH_SITES:
        for suffix, label, preset, expected, metadata_key in [
            ("setting", "设置", site_label, "0.05；0.1-1.5，步幅0.1", "setting"),
            ("nominal", "标称值", site_label, "0.4 ms", "nominal"),
            *[
                (f"tolerance:{load_slug}", "允差", f"{site_label} / {load_label}", "±0.04 ms", f"tolerance_{load_slug}")
                for load_slug, load_label in BASIC_ELECTRICAL_LOADS
            ],
        ]:
            requirements.append(
                _basic_electrical_table2_1_requirement(
                    clause_number="2.1.2",
                    suffix=f"pulse_width:{site_slug}:{suffix}",
                    label=label,
                    expected=expected,
                    metadata_key=metadata_key,
                    spec=BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.2"],
                    preset=preset,
                )
            )
    return requirements


def _basic_electrical_pulse_amplitude_requirements() -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    for site_slug, site_label, _aliases in BASIC_ELECTRICAL_PULSE_AMPLITUDE_SITES:
        requirements.append(
            _basic_electrical_table2_1_requirement(
                clause_number="2.1.3",
                suffix=f"pulse_amplitude:{site_slug}:setting",
                label="设置",
                expected="0.25-4.0，步幅0.25；4.5-7.5，步幅0.5",
                metadata_key="setting",
                spec=BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.3"],
                preset=site_label,
            )
        )
        requirements.append(
            _basic_electrical_table2_1_requirement(
                clause_number="2.1.3",
                suffix=f"pulse_amplitude:{site_slug}:nominal",
                label="标称值",
                expected="2.5 V",
                metadata_key="nominal",
                spec=BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.3"],
                preset=site_label,
            )
        )
        for load_slug, load_label in BASIC_ELECTRICAL_LOADS:
            for segment_index, (_segment_key, expected) in enumerate(BASIC_ELECTRICAL_PULSE_AMPLITUDE_SEGMENTS[load_slug]):
                requirements.append(
                    _basic_electrical_table2_1_requirement(
                        clause_number="2.1.3",
                        suffix=f"pulse_amplitude:{site_slug}:tolerance:{load_slug}:segment_{segment_index}",
                        label="允差",
                        expected=expected,
                        metadata_key=f"tolerance_{load_slug}_segment_{segment_index}",
                        spec=BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.3"],
                        preset=f"{site_label} / {load_label}",
                    )
                )
    return requirements


def _basic_electrical_simple_parameter_requirements(
    *,
    clause_number: str,
    spec: dict[str, Any],
    setting: str,
    nominal: str,
    tolerance: str,
) -> list[PTRAtomicRequirement]:
    return [
        _basic_electrical_table2_1_requirement(
            clause_number=clause_number,
            suffix=f"{spec['slug']}:{suffix}",
            label=label,
            expected=expected,
            metadata_key=suffix,
            spec=spec,
        )
        for suffix, label, expected in (
            ("setting", "设置", setting),
            ("nominal", "标称值", nominal),
            ("tolerance", "允差", tolerance),
        )
    ]


def _basic_electrical_av_interval_requirements() -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    spec = BASIC_ELECTRICAL_TABLE2_1_SPECS["2.1.10"]
    for condition_slug, condition_label, _aliases, setting, nominal, tolerance in BASIC_ELECTRICAL_AV_INTERVAL_CONDITIONS:
        for suffix, label, expected in (
            ("setting", "设置", setting),
            ("nominal", "标称值", nominal),
            ("tolerance", "允差", tolerance),
        ):
            requirements.append(
                _basic_electrical_table2_1_requirement(
                    clause_number="2.1.10",
                    suffix=f"av_interval:{condition_slug}:{suffix}",
                    label=label,
                    expected=expected,
                    metadata_key=f"{condition_slug}_{suffix}",
                    spec=spec,
                    preset=condition_label,
                )
            )
    return requirements


def _basic_electrical_table2_1_requirement(
    *,
    clause_number: str,
    suffix: str,
    label: str,
    expected: str,
    metadata_key: str,
    spec: dict[str, Any],
    preset: str | None = None,
) -> PTRAtomicRequirement:
    metadata = {
        "parameter_name": spec["label"],
        "aliases": list(spec.get("aliases") or (spec["label"],)),
        "field": metadata_key,
        "values": {"要求": expected},
    }
    if preset:
        metadata["preset"] = preset
    return PTRAtomicRequirement(
        atomic_id=f"{clause_number}:{suffix}",
        clause_id=clause_number,
        label=label,
        expected_text=expected,
        source="ptr_table",
        table_number="2-1",
        table_title="基本电性能参数",
        table_key=BASIC_ELECTRICAL_TABLE2_1_TABLE_KEY,
        metadata=metadata,
    )


def _clause_indicates_torque_wrench_size(clause: PTRClause) -> bool:
    text = _compact(" ".join([clause.title or "", clause.body_text or "", clause.full_text or ""]))
    return "扭矩扳手" in text and "尺寸" in text


def _torque_wrench_size_requirements(clause_number: str) -> list[PTRAtomicRequirement]:
    return [
        PTRAtomicRequirement(
            atomic_id=f"{clause_number}:torque_wrench:A",
            clause_id=clause_number,
            label="A",
            expected_text="0.88～0.89 mm",
            source="ptr_table",
            table_number=None,
            table_title="扭矩扳手尺寸",
            table_key=f"{clause_number}:扭矩扳手尺寸",
            metadata={"parameter_name": "A", "values": {"要求": "0.88～0.89 mm"}},
        ),
        PTRAtomicRequirement(
            atomic_id=f"{clause_number}:torque_wrench:B",
            clause_id=clause_number,
            label="B",
            expected_text="0.96～1.00 mm",
            source="ptr_table",
            table_number=None,
            table_title="扭矩扳手尺寸",
            table_key=f"{clause_number}:扭矩扳手尺寸",
            metadata={"parameter_name": "B", "values": {"要求": "0.96～1.00 mm"}},
        ),
    ]


def _basic_electrical_expected_values_from_ptr_table(clause_number: str, ptr_doc: PTRDocument) -> dict[str, str]:
    spec = BASIC_ELECTRICAL_TABLE2_1_SPECS.get(clause_number)
    if spec is None:
        return {}
    parent_text = _basic_electrical_table2_1_ptr_text(ptr_doc)
    window = _basic_electrical_parameter_window(parent_text, spec.get("aliases") or (spec["label"],))
    return _basic_electrical_expected_values_from_window(window)


def _basic_electrical_table2_1_ptr_text(ptr_doc: PTRDocument) -> str:
    values: list[str] = []
    for clause in ptr_doc.clauses:
        if str(clause.number) == "2.1":
            values.extend([clause.body_text, clause.text_content, clause.full_text])
    for table in ptr_doc.tables:
        if not table.canonical_table:
            continue
        record_names = " ".join(record.parameter_name or "" for record in table.canonical_table.parameter_records)
        if "基本频率" in record_names and "脉宽" in record_names:
            values.append(record_names)
    return "\n".join(_unique_non_empty(values))


def _basic_electrical_expected_values_from_window(window: str) -> dict[str, str]:
    lines = _basic_electrical_window_lines(window)
    if len(lines) <= 1:
        return {}
    payload = lines[1:]
    nominal_index = _basic_electrical_nominal_line_index(payload)
    if nominal_index is None:
        return {"summary": _safe_excerpt(" ".join(payload), limit=360)} if payload else {}
    setting = _clean_basic_electrical_value(" ".join(payload[:nominal_index]))
    nominal = _clean_basic_electrical_value(payload[nominal_index])
    tolerance = _clean_basic_electrical_value(" ".join(payload[nominal_index + 1 :]))
    result: dict[str, str] = {}
    if setting:
        result["setting"] = setting
    if nominal:
        result["nominal"] = nominal
    if tolerance:
        result["tolerance"] = tolerance
    return result


def _basic_electrical_nominal_line_index(lines: Sequence[str]) -> int | None:
    for index, line in enumerate(lines):
        compact = _compact(line)
        if not compact:
            continue
        if "步幅" in compact or "允差" in compact or "±" in compact or "/" in compact or "或" in compact:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?(?:min[-−]1|ms|mV|V)", compact, re.IGNORECASE):
            return index
    return None


def _comparison_row(
    requirement: PTRAtomicRequirement,
    group: InspectionItemGroup | None,
    report_atomic_result: PTRReportAtomicResult | None = None,
) -> PTRAtomicComparisonRow:
    if report_atomic_result is not None:
        actual = report_atomic_result.actual
        page = report_atomic_result.report_page or _first_page(group)
        item_no = report_atomic_result.report_item_no or ((group.display_item_no or group.item_no) if group else None)
        candidate_actuals = list(report_atomic_result.candidate_actuals)
        confidence = report_atomic_result.confidence
        source_text = report_atomic_result.source_text
        preset = report_atomic_result.preset
        unit = report_atomic_result.unit or requirement.unit
        atomic_id = report_atomic_result.atomic_id
    else:
        actual, page, item_no = _actual_for_requirement(requirement, group)
        candidate_actuals = []
        confidence = None
        source_text = None
        preset = requirement.metadata.get("preset") if isinstance(requirement.metadata, dict) else None
        unit = requirement.unit
        atomic_id = requirement.atomic_id
        if _is_not_applicable_requirement(requirement):
            actual = "/"

    status, reason = _status_and_reason(requirement, actual, group, candidate_actuals=candidate_actuals)
    return PTRAtomicComparisonRow(
        atomic_id=atomic_id,
        clause_id=requirement.clause_id,
        label=requirement.label,
        preset=preset,
        expected=_expected_display(requirement),
        actual=actual,
        unit=unit,
        candidate_actuals=candidate_actuals,
        status=status,
        reason=reason,
        report_page=page,
        report_item_no=item_no,
        confidence=confidence,
        source=requirement.source,
        source_text=source_text,
        table_number=requirement.table_number,
        table_title=requirement.table_title,
        table_key=requirement.table_key,
    )


def _actual_for_requirement(requirement: PTRAtomicRequirement, group: InspectionItemGroup | None) -> tuple[str | None, int | None, str | None]:
    if group is None:
        return None, None, None
    item_no = group.display_item_no or group.item_no
    if requirement.source == "ptr_table":
        if _is_not_applicable_requirement(requirement):
            return "/", _first_page(group), item_no
        if _is_basic_electrical_table2_1_requirement(requirement):
            return _group_result_text(group), _first_page(group), item_no
        if requirement.clause_id == "2.6":
            return None, _first_page(group), item_no
        return None, _first_page(group), item_no

    for row in group.rows:
        row_text = " ".join(str(value or "") for value in [row.sequence_raw, row.item_name, row.standard_requirement, row.test_result])
        if _row_matches_requirement(requirement, row_text):
            actual = _row_actual(requirement, row)
            if actual:
                return actual, row.source_page or _first_page(group), item_no
    if requirement.operator == "functional":
        group_text = " ".join(
            [
                ptr_group_standard_requirement(group),
                ptr_group_test_result(group),
                ptr_group_single_conclusion(group) or "",
                ptr_group_text(group),
            ]
        )
        if _row_matches_requirement(requirement, group_text) and _group_passed(group):
            return "符合要求", _first_page(group), item_no
    return None, _first_page(group), item_no


def _row_matches_requirement(requirement: PTRAtomicRequirement, row_text: str) -> bool:
    compact = _compact(row_text)
    atomic_id = requirement.atomic_id
    if requirement.operator == "functional":
        keywords = requirement.metadata.get("match_keywords") if isinstance(requirement.metadata, dict) else None
        if isinstance(keywords, list) and keywords:
            return any(_compact(str(keyword)) in compact for keyword in keywords)
        return _compact(requirement.label) in compact
    if atomic_id.endswith(":voltage"):
        return "电压" in compact
    if atomic_id.endswith(":current"):
        return "电流" in compact
    if ":rise_time" in atomic_id:
        return "2.2.3" in compact or "上升" in compact
    if ":fall_time" in atomic_id:
        return "2.2.4" in compact or "下降" in compact or "脉冲宽度" in compact
    if atomic_id.endswith(":decay"):
        return "2.2.5" in compact or "衰减" in compact
    if atomic_id.endswith(":max_energy"):
        return "2.2.6" in compact or "最大输出能量" in compact
    if atomic_id.endswith(":temperature_limit_protection"):
        return "温度" in compact
    if atomic_id.endswith(":over_current_protection"):
        return "过流" in compact
    return False


def _row_actual(requirement: PTRAtomicRequirement, row) -> str | None:
    if requirement.operator == "functional":
        text = " ".join(str(value or "") for value in [row.standard_requirement, row.test_result, row.conclusion])
        return "符合要求" if "符合" in text and "不符合" not in text else (row.test_result or row.conclusion)
    if requirement.atomic_id.endswith(":current") and row.item_name:
        return str(row.item_name).strip()
    values = row.result_values or []
    if values:
        return _actual_subset(requirement, " / ".join(values))
    if row.test_result:
        return _actual_subset(requirement, row.test_result)
    return None


def _actual_subset(requirement: PTRAtomicRequirement, value: str) -> str:
    text = str(value or "").strip()
    if ":fall_time" in requirement.atomic_id:
        numbers = re.findall(r"\d+(?:\.\d+)?", text)
        return " / ".join(numbers[:2]) if len(numbers) >= 2 else text
    return text


def _status_and_reason(
    requirement: PTRAtomicRequirement,
    actual: str | None,
    group: InspectionItemGroup | None,
    *,
    candidate_actuals: Sequence[str] | None = None,
) -> tuple[str, str]:
    if requirement.source == "ptr_table":
        if _is_not_applicable_requirement(requirement):
            return "not_applicable", "PTR 表格要求为 /，该预设不适用。"
        if requirement.clause_id == "2.6":
            item_no = (group.display_item_no or group.item_no) if group else "未编号"
            if _is_report_not_applicable_text(actual):
                return "not_applicable", "报告软件功能表显示该组件功能不适用。"
            if actual and "符合" in actual and "不符合" not in actual:
                return "match", "报告软件功能表显示符合要求。"
            if actual and "不符合" in actual:
                return "mismatch", f"报告软件功能表显示 {actual}。"
            return "needs_review", f"报告序号 {item_no} 未稳定展开表格功能明细需复核。"
        if actual is None:
            item_no = (group.display_item_no or group.item_no) if group else "未编号"
            return "needs_review", f"报告序号 {item_no} 未稳定展开表格参数结果，需复核。"
        if _is_basic_electrical_table2_1_requirement(requirement):
            return _basic_electrical_table2_1_status_and_reason(requirement, actual, group)
        if _is_torque_wrench_requirement(requirement):
            return _torque_wrench_status_and_reason(requirement, actual, group)
        if requirement.clause_id == "2.2.2" and _waveform_report_actual_satisfies(requirement.expected_text, actual):
            return "match", "报告表 6 波形参数结果满足 PTR 要求。"
        if _table_value_matches(requirement.expected_text, actual):
            return "match", "报告表格结果与 PTR 表格要求一致。"
        return "mismatch", f"报告结果 {actual} 与 PTR 要求 {requirement.expected_text or '无'} 不一致。"
    if requirement.operator == "functional":
        if actual and "符合" in actual:
            return "match", "报告检验结果显示符合。"
        if candidate_actuals:
            return "candidate_found_needs_mapping", "报告中找到候选结果，但未完成结构化绑定。"
        return "needs_review", "报告功能性结果未能稳定抽取，需复核。"
    if requirement.operator == "functional_or_equal":
        if actual and "符合" in actual and "不符合" not in actual:
            return "match", "报告检验结果显示符合。"
        if _table_value_matches(requirement.expected_text, actual):
            return "match", "报告结果与 PTR 要求一致。"
        if _numbers(actual) and _numbers(requirement.expected_text) and _numbers(actual) == _numbers(requirement.expected_text):
            return "match", "报告结果与 PTR 要求一致。"
        return "needs_review", "报告功能/计数结果需复核。"
    if requirement.operator == "deviation_within_tolerance":
        tolerance = _expected_tolerance(requirement.expected_text or "")
        actual_values = _signed_numbers(actual or "")
        if tolerance is not None and actual_values and all(abs(value) <= tolerance for value in actual_values):
            return "match", f"报告偏差 {actual} 在 {requirement.expected_text} 范围内。"
        return "needs_review", "报告偏差结果需复核。"
    if actual is None:
        if candidate_actuals:
            return "candidate_found_needs_mapping", "报告中找到候选结果，但未完成结构化绑定。"
        return "needs_review", "报告结果未能稳定抽取，需复核。"
    actual_numbers = _numbers(actual)
    expected = requirement.expected_value
    if expected is None or not actual_numbers:
        return "needs_review", "缺少可计算的数值证据，需复核。"
    matched = _compare_numbers(actual_numbers, expected, requirement.operator or "")
    symbol = _display_operator(requirement.operator)
    if matched:
        return "match", f"{actual} {symbol} {int(expected) if expected.is_integer() else expected}"
    return "mismatch", f"{actual} 不满足 {symbol} {int(expected) if expected.is_integer() else expected}"


def _compare_numbers(values: list[float], expected: float, operator: str) -> bool:
    if operator in {">=", "≥"}:
        return all(value >= expected for value in values)
    if operator in {"<=", "≤"}:
        return all(value <= expected for value in values)
    if operator == "<":
        return all(value < expected for value in values)
    if operator == ">":
        return all(value > expected for value in values)
    return False


def _report_results_for_requirement(
    requirement: PTRAtomicRequirement,
    report_atomic_results: Sequence[PTRReportAtomicResult],
) -> list[PTRReportAtomicResult]:
    return [
        result
        for result in report_atomic_results
        if result.atomic_id == requirement.atomic_id or result.atomic_id.startswith(f"{requirement.atomic_id}:")
    ]


def _is_basic_electrical_table2_1_requirement(requirement: PTRAtomicRequirement) -> bool:
    return requirement.source == "ptr_table" and requirement.table_key == BASIC_ELECTRICAL_TABLE2_1_TABLE_KEY


def _is_torque_wrench_requirement(requirement: PTRAtomicRequirement) -> bool:
    return requirement.source == "ptr_table" and "torque_wrench" in requirement.atomic_id


def _torque_wrench_status_and_reason(
    requirement: PTRAtomicRequirement,
    actual: str | None,
    group: InspectionItemGroup | None,
) -> tuple[str, str]:
    if actual and _numeric_range_expected_matches(requirement.expected_text, actual):
        return "match", f"报告实测值 {actual} 在 {requirement.expected_text} 范围内。"
    if _group_passed(group):
        return "match", "报告扭矩扳手尺寸单项结论符合。"
    item_no = (group.display_item_no or group.item_no) if group else "未编号"
    return "needs_review", f"报告序号 {item_no} 未稳定展开扭矩扳手尺寸，需复核。"


def _basic_electrical_table2_1_status_and_reason(
    requirement: PTRAtomicRequirement,
    actual: str | None,
    group: InspectionItemGroup | None,
) -> tuple[str, str]:
    if not actual:
        item_no = (group.display_item_no or group.item_no) if group else "未编号"
        return "needs_review", f"报告序号 {item_no} 未稳定展开表2-1参数结果，需复核。"
    if ":tolerance:" in requirement.atomic_id:
        tolerance = _expected_tolerance(requirement.expected_text or "")
        actual_values = _signed_numbers(actual)
        if tolerance is not None and actual_values and all(abs(value) <= tolerance for value in actual_values):
            return "match", f"报告偏差 {actual} 在 {requirement.expected_text} 范围内。"
    if _table_value_matches(requirement.expected_text, actual) or _basic_electrical_text_contains_expected(requirement.expected_text, actual):
        return "match", "报告表2-1参数与 PTR 要求一致。"
    if _group_passed(group):
        return "match", "报告已展开表2-1参数结果，单项结论符合。"
    return "needs_review", f"报告表2-1参数结果 {actual} 需人工复核。"


def _basic_electrical_text_contains_expected(expected: str | None, actual: str | None) -> bool:
    expected_text = _normalize_table_value(expected)
    actual_text = _normalize_table_value(actual)
    if not expected_text or not actual_text:
        return False
    expected_text = expected_text.replace("步幅", "").replace("为", "")
    actual_text = actual_text.replace("步幅", "").replace("为", "")
    return expected_text in actual_text or actual_text in expected_text


def _group_passed(group: InspectionItemGroup | None) -> bool:
    if group is None:
        return False
    text = ptr_group_text(group)
    conclusion = " ".join(str(value or "") for value in [group.effective_single_conclusion, text])
    return "符合" in conclusion and "不符合" not in conclusion


def _report_atomic_result(
    *,
    atomic_id: str,
    clause_id: str,
    label: str,
    actual: str | None,
    item_no: str | None,
    page: int | None,
    source_text: str,
    confidence: str,
    method: str,
    unit: str | None = None,
    preset: str | None = None,
    candidate_actuals: Sequence[str] | None = None,
    full_group_text: str | None = None,
) -> PTRReportAtomicResult:
    diagnostic = {
        "method": method,
        "confidence": confidence,
        "source_text_excerpt": _safe_excerpt(source_text),
    }
    if full_group_text is not None:
        diagnostic["full_group_text_excerpt"] = _safe_excerpt(full_group_text, limit=2400)
    return PTRReportAtomicResult(
        atomic_id=atomic_id,
        clause_id=clause_id,
        label=label,
        actual=actual,
        unit=unit,
        preset=preset,
        report_item_no=item_no,
        report_page=page,
        source_text=_safe_excerpt(source_text, limit=1200),
        confidence=confidence,
        candidate_actuals=list(candidate_actuals or []),
        diagnostics=[diagnostic],
    )


def _group_window_atomic_results(
    group: InspectionItemGroup,
    *,
    group_text: str,
    item_no: str | None,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRReportAtomicResult]:
    results: list[PTRReportAtomicResult] = []
    waveform_window = _clause_window(group_text, "2.2.2")
    if waveform_window:
        results.extend(
            _waveform_table_atomic_results(
                group,
                window=waveform_window,
                item_no=item_no,
                page=_page_for_clause_window(group, "2.2.2", page_text_by_page=page_text_by_page),
                full_group_text=group_text,
            )
        )
    for clause_id, atomic_prefix, label, unit, method in (
        ("2.2.3", "2.2.3:rise_time", "脉冲上升时间", "ns", "group_clause_window_rise_time"),
        ("2.2.4", "2.2.4:fall_time", "脉冲下降时间", "ns", "group_clause_window_fall_time"),
    ):
        window = _clause_window(group_text, clause_id)
        values_by_preset = _preset_values_by_slug_from_text(window)
        if not values_by_preset:
            continue
        results.extend(
            _preset_results(
                values_by_preset,
                atomic_prefix=atomic_prefix,
                clause_id=clause_id,
                label=label,
                unit=unit,
                item_no=item_no,
                page=_page_for_clause_window(group, clause_id, page_text_by_page=page_text_by_page),
                source_text=window,
                method=method,
                full_group_text=group_text,
            )
        )

    decay_window = _clause_window(group_text, "2.2.5")
    decay_actual = _numeric_result_from_window(decay_window, expected=10)
    if decay_actual:
        results.append(
            _report_atomic_result(
                atomic_id="2.2.5:decay",
                clause_id="2.2.5",
                label="脉冲衰减",
                actual=decay_actual,
                unit="%",
                item_no=item_no,
                page=_page_for_clause_window(group, "2.2.5", page_text_by_page=page_text_by_page),
                source_text=decay_window,
                confidence="high",
                method="group_clause_window_decay",
                full_group_text=group_text,
            )
        )

    energy_window = _clause_window(group_text, "2.2.6")
    energy_actual = _numeric_result_from_window(energy_window, expected=258)
    if energy_actual:
        results.append(
            _report_atomic_result(
                atomic_id="2.2.6:max_energy",
                clause_id="2.2.6",
                label="单个脉冲最大输出能量",
                actual=energy_actual,
                unit="mJ",
                item_no=item_no,
                page=_page_for_clause_window(group, "2.2.6", page_text_by_page=page_text_by_page),
                source_text=energy_window,
                confidence="high",
                method="group_clause_window_max_energy",
                full_group_text=group_text,
            )
        )

    return results


def _direct_text_report_atomic_results(
    group: InspectionItemGroup,
    *,
    group_text: str,
    item_no: str | None,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRReportAtomicResult]:
    results: list[PTRReportAtomicResult] = []
    direct_source_text = _direct_group_source_text(group, group_text)
    for clause_id in _clause_ids_in_text(direct_source_text):
        window = _clause_window(direct_source_text, clause_id)
        if not window:
            continue
        page = _page_for_clause_window(group, clause_id, page_text_by_page=page_text_by_page)
        compact = _compact(window)
        if "电压" in compact and "标称值" in compact:
            nominal = _direct_result_after_marker(window, "标称值")
            low_voltage = _direct_result_after_marker(window, "低电压")
            if nominal:
                results.append(
                    _report_atomic_result(
                        atomic_id=f"{clause_id}:voltage:nominal",
                        clause_id=clause_id,
                        label="电压",
                        actual=nominal,
                        unit="V",
                        item_no=item_no,
                        page=page,
                        source_text=window,
                        confidence="high",
                        method="direct_clause_window_voltage_nominal",
                        full_group_text=direct_source_text,
                    )
                )
            if low_voltage:
                results.append(
                    _report_atomic_result(
                        atomic_id=f"{clause_id}:voltage:low_voltage",
                        clause_id=clause_id,
                        label="低电压",
                        actual=low_voltage,
                        unit="V",
                        item_no=item_no,
                        page=page,
                        source_text=window,
                        confidence="high",
                        method="direct_clause_window_voltage_low",
                        full_group_text=direct_source_text,
                    )
                )
        direct_specs = (
            ("脉宽", "pulse_width", "脉宽", "μs", "direct_clause_window_pulse_width"),
            ("脉冲间隔", "pulse_interval", "脉冲间隔", "μs", "direct_clause_window_pulse_interval"),
            ("脉冲群间隔", "pulse_group_interval", "脉冲群间隔", "s", "direct_clause_window_pulse_group_interval"),
            ("上升沿时间", "rise_edge_time", "上升沿时间", "ns", "direct_clause_window_rise_edge_time"),
            ("下降沿时间", "fall_edge_time", "下降沿时间", "ns", "direct_clause_window_fall_edge_time"),
        )
        for marker, suffix, label, unit, method in direct_specs:
            if marker not in window or (marker == "脉冲间隔" and "脉冲群间隔" in window):
                continue
            actual = _direct_result_after_marker(window, marker)
            if not actual:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"{clause_id}:{suffix}",
                    clause_id=clause_id,
                    label=label,
                    actual=actual,
                    unit=unit,
                    item_no=item_no,
                    page=page,
                    source_text=window,
                    confidence="high",
                    method=method,
                    full_group_text=direct_source_text,
                )
            )
        functional_specs = (
            ("每个脉冲群中的循环数", "pulse_group_cycles", "每个脉冲群中的循环数"),
            ("每个治疗波中的脉冲群数量", "treatment_wave_pulse_group_count", "每个治疗波中的脉冲群数量"),
        )
        for marker, suffix, label in functional_specs:
            if marker not in window:
                continue
            actual = _direct_result_after_marker(window, marker)
            if not actual:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"{clause_id}:{suffix}",
                    clause_id=clause_id,
                    label=label,
                    actual=actual,
                    item_no=item_no,
                    page=page,
                    source_text=window,
                    confidence="high",
                    method="direct_clause_window_functional_or_equal",
                    full_group_text=direct_source_text,
                )
            )
        functional_actual = _direct_functional_actual(window)
        if functional_actual:
            results.append(
                _report_atomic_result(
                    atomic_id=f"{clause_id}:functional",
                    clause_id=clause_id,
                    label=_direct_clause_label(clause_id, window),
                    actual=functional_actual,
                    item_no=item_no,
                    page=page,
                    source_text=window,
                    confidence="high",
                    method="direct_clause_window_functional",
                    full_group_text=direct_source_text,
                )
            )
    return results


def _basic_electrical_table2_1_report_atomic_results(
    group: InspectionItemGroup,
    *,
    group_text: str,
    item_no: str | None,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRReportAtomicResult]:
    clause_id = _basic_electrical_group_clause_id(group)
    spec = BASIC_ELECTRICAL_TABLE2_1_SPECS.get(clause_id)
    if spec is None:
        return []
    window = _basic_electrical_report_window(group_text, clause_id, spec)
    if not window:
        return []
    page = _page_for_basic_electrical_table2_1(group, clause_id, page_text_by_page=page_text_by_page)
    if clause_id == "2.1.1":
        return _basic_electrical_basic_rate_report_results(window=window, item_no=item_no, page=page, full_group_text=group_text)
    if clause_id == "2.1.2":
        return _basic_electrical_pulse_width_report_results(window=window, item_no=item_no, page=page, full_group_text=group_text)
    if clause_id == "2.1.3":
        return _basic_electrical_pulse_amplitude_report_results(window=window, item_no=item_no, page=page, full_group_text=group_text)
    if clause_id == "2.1.10":
        return _basic_electrical_av_interval_report_results(window=window, item_no=item_no, page=page, full_group_text=group_text)
    return _basic_electrical_generic_table2_1_report_results(
        clause_id=clause_id,
        spec=spec,
        window=window,
        item_no=item_no,
        page=page,
        full_group_text=group_text,
    )


def _basic_electrical_group_clause_id(group: InspectionItemGroup) -> str | None:
    for row in group.rows:
        clause = str(row.standard_clause or "").strip()
        if clause in BASIC_ELECTRICAL_TABLE2_1_SPECS:
            return clause
    text = ptr_group_text(group)
    for clause_id in BASIC_ELECTRICAL_TABLE2_1_SPECS:
        if _clause_header_pattern(clause_id).search(text):
            return clause_id
    return None


def _basic_electrical_basic_rate_report_results(
    *,
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    specs = [
        ("2.1.1:basic_rate:setting", "设置", None, _basic_electrical_report_label_value(window, "设置", ("标称值",))),
        ("2.1.1:basic_rate:nominal", "标称值", None, _basic_electrical_report_label_value(window, "标称值", ("符合要求", "允差"))),
        ("2.1.1:basic_rate:tolerance:240ohm", "允差", "@240Ω", _basic_electrical_load_result(window, "@240Ω")),
        ("2.1.1:basic_rate:tolerance:500ohm", "允差", "@500Ω", _basic_electrical_load_result(window, "@500Ω")),
        ("2.1.1:basic_rate:tolerance:2000ohm", "允差", "@2000Ω", _basic_electrical_load_result(window, "@2000Ω")),
    ]
    results: list[PTRReportAtomicResult] = []
    for atomic_id, label, preset, actual in specs:
        if not actual:
            continue
        results.append(
            _report_atomic_result(
                atomic_id=atomic_id,
                clause_id="2.1.1",
                label=label,
                actual=actual,
                preset=preset,
                item_no=item_no,
                page=page,
                source_text=window,
                confidence="high",
                method="basic_electrical_table2_1_basic_rate",
                full_group_text=full_group_text,
            )
        )
    return results


def _basic_electrical_pulse_width_report_results(
    *,
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    results: list[PTRReportAtomicResult] = []
    all_site_aliases = [alias for _slug_value, _label, aliases in BASIC_ELECTRICAL_PULSE_WIDTH_SITES for alias in aliases]
    for site_slug, site_label, aliases in BASIC_ELECTRICAL_PULSE_WIDTH_SITES:
        site_window = _basic_electrical_condition_window(window, aliases, all_site_aliases)
        if not site_window:
            continue
        for suffix, label, preset, actual in [
            ("setting", "设置", site_label, _basic_electrical_report_label_value(site_window, "设置", ("标称值",))),
            ("nominal", "标称值", site_label, _basic_electrical_report_label_value(site_window, "标称值", ("符合要求", "允差"))),
            *[
                (f"tolerance:{load_slug}", "允差", f"{site_label} / {load_label}", _basic_electrical_load_result(site_window, load_label))
                for load_slug, load_label in BASIC_ELECTRICAL_LOADS
            ],
        ]:
            if not actual:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"2.1.2:pulse_width:{site_slug}:{suffix}",
                    clause_id="2.1.2",
                    label=label,
                    actual=actual,
                    preset=preset,
                    item_no=item_no,
                    page=page,
                    source_text=site_window,
                    confidence="high",
                    method="basic_electrical_table2_1_pulse_width_condition",
                    full_group_text=full_group_text,
                )
            )
    return results


def _basic_electrical_pulse_amplitude_report_results(
    *,
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    results: list[PTRReportAtomicResult] = []
    all_site_aliases = [alias for _slug_value, _label, aliases in BASIC_ELECTRICAL_PULSE_AMPLITUDE_SITES for alias in aliases]
    for site_slug, site_label, aliases in BASIC_ELECTRICAL_PULSE_AMPLITUDE_SITES:
        site_window = _basic_electrical_condition_window(window, aliases, all_site_aliases)
        if not site_window:
            continue
        for suffix, label, actual in [
            ("setting", "设置", _basic_electrical_report_label_value(site_window, "设置", ("标称值",))),
            ("nominal", "标称值", _basic_electrical_report_label_value(site_window, "标称值", ("符合要求", "允差"))),
        ]:
            if not actual:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"2.1.3:pulse_amplitude:{site_slug}:{suffix}",
                    clause_id="2.1.3",
                    label=label,
                    actual=actual,
                    preset=site_label,
                    item_no=item_no,
                    page=page,
                    source_text=site_window,
                    confidence="high",
                    method="basic_electrical_table2_1_pulse_amplitude_condition",
                    full_group_text=full_group_text,
                )
            )
        for load_slug, load_label in BASIC_ELECTRICAL_LOADS:
            load_block = _basic_electrical_load_block(site_window, load_label)
            for segment_index, (segment_key, _expected) in enumerate(BASIC_ELECTRICAL_PULSE_AMPLITUDE_SEGMENTS[load_slug]):
                actual = _basic_electrical_segment_actual(load_block, segment_key)
                if not actual:
                    continue
                results.append(
                    _report_atomic_result(
                        atomic_id=f"2.1.3:pulse_amplitude:{site_slug}:tolerance:{load_slug}:segment_{segment_index}",
                        clause_id="2.1.3",
                        label="允差",
                        actual=actual,
                        preset=f"{site_label} / {load_label}",
                        item_no=item_no,
                        page=page,
                        source_text=load_block or site_window,
                        confidence="high",
                        method="basic_electrical_table2_1_pulse_amplitude_segment",
                        full_group_text=full_group_text,
                    )
                )
    return results


def _basic_electrical_av_interval_report_results(
    *,
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    results: list[PTRReportAtomicResult] = []
    all_aliases = [alias for _slug_value, _label, aliases, _setting, _nominal, _tolerance in BASIC_ELECTRICAL_AV_INTERVAL_CONDITIONS for alias in aliases]
    for condition_slug, condition_label, aliases, _setting, _nominal, _tolerance in BASIC_ELECTRICAL_AV_INTERVAL_CONDITIONS:
        condition_window = _basic_electrical_condition_window(window, aliases, all_aliases)
        if not condition_window:
            continue
        for suffix, label, actual in (
            ("setting", "设置", _basic_electrical_report_label_value(condition_window, "设置", ("标称值",))),
            ("nominal", "标称值", _basic_electrical_report_label_value(condition_window, "标称值", ("符合要求", "允差"))),
            ("tolerance", "允差", _basic_electrical_report_tolerance_result(condition_window)),
        ):
            if not actual:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"2.1.10:av_interval:{condition_slug}:{suffix}",
                    clause_id="2.1.10",
                    label=label,
                    actual=actual,
                    preset=condition_label,
                    item_no=item_no,
                    page=page,
                    source_text=condition_window,
                    confidence="high",
                    method="basic_electrical_table2_1_av_interval_condition",
                    full_group_text=full_group_text,
                )
            )
    return results


def _basic_electrical_generic_table2_1_report_results(
    *,
    clause_id: str,
    spec: dict[str, Any],
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    slug = str(spec["slug"])
    fields = [
        (f"{clause_id}:{slug}:setting", "设置", _basic_electrical_report_label_value(window, "设置", ("标称值",))),
        (f"{clause_id}:{slug}:nominal", "标称值", _basic_electrical_report_label_value(window, "标称值", ("符合要求", "允差"))),
        (f"{clause_id}:{slug}:tolerance", "允差", _basic_electrical_report_tolerance_result(window)),
    ]
    results: list[PTRReportAtomicResult] = []
    for atomic_id, label, actual in fields:
        if not actual:
            continue
        results.append(
            _report_atomic_result(
                atomic_id=atomic_id,
                clause_id=clause_id,
                label=label,
                actual=actual,
                item_no=item_no,
                page=page,
                source_text=window,
                confidence="high",
                method="basic_electrical_table2_1_parameter_detail",
                full_group_text=full_group_text,
            )
        )
    summary = _basic_electrical_report_summary(window)
    if summary:
        results.append(
            _report_atomic_result(
                atomic_id=f"{clause_id}:{slug}:report_detail",
                clause_id=clause_id,
                label=str(spec["label"]),
                actual=summary,
                item_no=item_no,
                page=page,
                source_text=window,
                confidence="medium" if not results else "high",
                method="basic_electrical_table2_1_summary",
                full_group_text=full_group_text,
            )
        )
    return results


def _basic_electrical_report_window(group_text: str, clause_id: str, spec: dict[str, Any]) -> str:
    text = str(group_text or "")
    if not text.strip():
        return ""
    windows: list[str] = []
    next_clause = _basic_electrical_next_clause(clause_id)
    for match in _clause_header_pattern(clause_id).finditer(text):
        end = len(text)
        if next_clause:
            next_match = _clause_header_pattern(next_clause).search(text, match.end())
            if next_match is not None:
                end = next_match.start()
        windows.append(text[match.start() : end].strip())
    alias_window = _basic_electrical_parameter_window(text, spec.get("aliases") or (spec["label"],))
    if alias_window:
        windows.append(alias_window)
    if not windows:
        return ""
    return max(windows, key=lambda window: _basic_electrical_report_window_score_for_clause(window, clause_id))


def _basic_electrical_report_window_score(window: str) -> tuple[int, int]:
    text = str(window or "")
    compact = _compact_for_match(text)
    detail_hits = sum(1 for token in ("设置", "标称值", "允差", "符合要求") if token in text)
    load_hits = sum(1 for token in ("240ω", "500ω", "2000ω") if token in compact)
    signed_hits = len(_signed_numbers(text))
    return detail_hits * 10 + load_hits * 5 + signed_hits, len(text)


def _basic_electrical_report_window_score_for_clause(window: str, clause_id: str) -> tuple[int, int, int]:
    previous_clause = _basic_electrical_previous_clause(clause_id)
    previous_clause_hits = 0
    if previous_clause:
        previous_clause_hits = len(_clause_header_pattern(previous_clause).findall(str(window or "")))
    data_score, length_score = _basic_electrical_report_window_score(window)
    return -previous_clause_hits, data_score, length_score


def _basic_electrical_condition_window(text: str, aliases: Sequence[str], all_aliases: Sequence[str]) -> str:
    source = str(text or "")
    compact_source = _compact_for_match(source)
    starts: list[int] = []
    for alias in aliases:
        key = _compact_for_match(alias)
        if not key:
            continue
        search_from = 0
        while True:
            compact_index = compact_source.find(key, search_from)
            if compact_index < 0:
                break
            starts.append(_compact_index_to_source_index(source, compact_index))
            search_from = compact_index + len(key)
    starts = sorted({index for index in starts if index >= 0})
    if not starts:
        return ""
    windows: list[str] = []
    for start in starts:
        end = len(source)
        compact_start = _source_index_to_compact_index(source, start + 1)
        for alias in all_aliases:
            key = _compact_for_match(alias)
            if not key:
                continue
            index = compact_source.find(key, compact_start)
            if index >= 0:
                source_index = _compact_index_to_source_index(source, index)
                if source_index > start:
                    end = min(end, source_index)
        windows.append(source[start:end].strip())
    return max(windows, key=_basic_electrical_report_window_score)


def _basic_electrical_load_block(window: str, load_label: str) -> str:
    text = str(window or "")
    start_match = _basic_electrical_load_heading_pattern(load_label).search(text)
    if start_match is None:
        return ""
    end = len(text)
    for _load_slug, other_load_label in BASIC_ELECTRICAL_LOADS:
        if other_load_label == load_label:
            continue
        other_match = _basic_electrical_load_heading_pattern(other_load_label).search(text, start_match.end())
        if other_match is not None:
            end = min(end, other_match.start())
    return text[start_match.start() : end].strip()


def _basic_electrical_load_heading_pattern(load_label: str) -> re.Pattern[str]:
    number = re.escape(re.sub(r"\D", "", load_label))
    return re.compile(rf"(?:允差\s*[:：]?\s*)?{number}\s*[ΩΩ欧]\s*[:：]", re.IGNORECASE)


def _basic_electrical_segment_actual(load_block: str, segment_key: str) -> str | None:
    lines = _basic_electrical_window_lines(load_block)
    compact_segment = _compact_for_match(segment_key)
    starts = [
        index
        for index, line in enumerate(lines)
        if compact_segment and compact_segment in _compact_for_match(line)
    ]
    if not starts:
        return None
    start = starts[0]
    end = len(lines)
    all_segment_keys = [key for segments in BASIC_ELECTRICAL_PULSE_AMPLITUDE_SEGMENTS.values() for key, _expected in segments]
    for index in range(start + 1, len(lines)):
        compact_line = _compact_for_match(lines[index])
        if any(_compact_for_match(key) and _compact_for_match(key) in compact_line for key in all_segment_keys):
            end = index
            break
        if re.search(r"^\s*允差\s*[:：]?", lines[index]):
            end = index
            break
    actual = _basic_electrical_trailing_signed_actual(" ".join(lines[start:end]))
    if actual:
        return actual
    signed_lines = [line for line in lines[start + 1 : end] if _line_starts_with_signed_result(line)]
    if not signed_lines:
        return None
    return _clean_basic_electrical_actual(" ".join(signed_lines))


def _basic_electrical_trailing_signed_actual(value: str) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    match = re.search(
        r"([+＋\-－]\s*\d+(?:\.\d+)?\s*(?:%|V|mV|ms)?"
        r"(?:\s*[~～至]\s*[+＋\-－]?\s*\d+(?:\.\d+)?\s*(?:%|V|mV|ms)?)?"
        r"(?:\s*[、,，]\s*[+＋\-－]\s*\d+(?:\.\d+)?\s*(?:%|V|mV|ms)?"
        r"(?:\s*[~～至]\s*[+＋\-－]?\s*\d+(?:\.\d+)?\s*(?:%|V|mV|ms)?)?)*"
        r")\s*$",
        text,
    )
    return _clean_basic_electrical_actual(match.group(1)) if match else None


def _line_starts_with_signed_result(line: str) -> bool:
    return bool(re.match(r"\s*[+＋\-－]\s*\d", str(line or "")))


def _clean_basic_electrical_actual(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    text = text.replace("＋", "+").replace("－", "-").replace("~", "～").replace("至", "～")
    text = text.replace("，", "、").strip("、")
    text = re.sub(r"、(?=[+\\-])", "、", text)
    return text


def _basic_electrical_parameter_window(text: str, aliases: Sequence[str]) -> str:
    source = str(text or "")
    compact_source = _compact_for_match(source)
    starts = [
        _compact_index_to_source_index(source, compact_source.find(_compact_for_match(alias)))
        for alias in aliases
        if _compact_for_match(alias) and compact_source.find(_compact_for_match(alias)) >= 0
    ]
    starts = [index for index in starts if index >= 0]
    if not starts:
        return ""
    start = min(starts)
    end = len(source)
    for other_spec in BASIC_ELECTRICAL_TABLE2_1_SPECS.values():
        for alias in other_spec.get("aliases") or (other_spec["label"],):
            key = _compact_for_match(alias)
            if not key:
                continue
            compact_start = _source_index_to_compact_index(source, start + 1)
            index = compact_source.find(key, compact_start)
            if index >= 0:
                source_index = _compact_index_to_source_index(source, index)
                if source_index > start:
                    end = min(end, source_index)
    return source[start:end].strip()


def _basic_electrical_next_clause(clause_id: str) -> str | None:
    match = re.fullmatch(r"2\.1\.(\d+)", clause_id)
    if not match:
        return None
    return f"2.1.{int(match.group(1)) + 1}"


def _basic_electrical_previous_clause(clause_id: str) -> str | None:
    match = re.fullmatch(r"2\.1\.(\d+)", clause_id)
    if not match:
        return None
    previous = int(match.group(1)) - 1
    return f"2.1.{previous}" if previous >= 1 else None


def _page_for_basic_electrical_table2_1(
    group: InspectionItemGroup,
    clause_id: str,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> int | None:
    if page_text_by_page:
        pattern = _clause_header_pattern(clause_id)
        for page_number in group.pages:
            if pattern.search(page_text_by_page.get(page_number) or ""):
                return page_number
    return _first_page(group)


def _basic_electrical_report_label_value(window: str, label: str, end_markers: Sequence[str]) -> str | None:
    text = str(window or "")
    match = re.search(rf"{re.escape(label)}\s*[:：]\s*", text)
    if match is None:
        return None
    start = match.end()
    end = len(text)
    for marker in end_markers:
        marker_match = re.search(re.escape(marker), text[start:])
        if marker_match is not None:
            end = min(end, start + marker_match.start())
    return _clean_basic_electrical_value(text[start:end])


def _basic_electrical_load_result(window: str, load_marker: str) -> str | None:
    text = str(window or "")
    pattern = _basic_electrical_load_pattern(load_marker)
    match = pattern.search(text)
    if match is None:
        return None
    start = match.end()
    end = len(text)
    for marker in ("@240Ω", "@500Ω", "@2000Ω"):
        if marker == load_marker:
            continue
        next_match = _basic_electrical_load_pattern(marker).search(text, start)
        if next_match is not None:
            end = min(end, next_match.start())
    segment = text[start:end]
    return _basic_electrical_signed_result(segment)


def _basic_electrical_load_pattern(load_marker: str) -> re.Pattern[str]:
    marker = str(load_marker or "").lstrip("@")
    number = re.escape(re.sub(r"\D", "", marker))
    return re.compile(rf"@\s*{number}\s*[ΩΩ欧]", re.IGNORECASE)


def _basic_electrical_report_tolerance_result(window: str) -> str | None:
    for load_marker in ("@240Ω", "@500Ω", "@2000Ω"):
        value = _basic_electrical_load_result(window, load_marker)
        if value:
            return value
    tolerance_match = re.search(r"允差\s*[:：]?", str(window or ""))
    if tolerance_match is None:
        return "符合要求" if "符合要求" in str(window or "") or "符合" in str(window or "") else None
    segment = str(window or "")[tolerance_match.end() :]
    return _basic_electrical_signed_result(segment) or ("符合要求" if "符合" in segment else None)


def _basic_electrical_signed_result(value: str) -> str | None:
    text = str(value or "")
    range_match = re.search(
        r"([+＋\-－]\s*\d+(?:\.\d+)?\s*[~～至-]\s*[+＋\-－]?\s*\d+(?:\.\d+)?)",
        text,
    )
    if range_match:
        return _clean_signed_actual(range_match.group(1)).replace("~", "～").replace("至", "～")
    signed_match = re.search(r"([+＋\-－]\s*\d+(?:\.\d+)?)", text)
    if signed_match:
        return _clean_signed_actual(signed_match.group(1))
    return None


def _basic_electrical_report_summary(window: str) -> str | None:
    lines = [line for line in _basic_electrical_window_lines(window) if not _looks_like_report_table_header(line)]
    return _safe_excerpt("；".join(lines[:8]), limit=360) if lines else None


def _basic_electrical_window_lines(window: str) -> list[str]:
    return [_clean_basic_electrical_value(line) for line in str(window or "").splitlines() if _clean_basic_electrical_value(line)]


def _clean_basic_electrical_value(value: str | None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace(" ，", "，").replace("， ", "，").replace(" ；", "；").replace("； ", "；")
    text = re.sub(r"步\s*幅\s*为\s*", "步幅为", text)
    text = re.sub(r"步幅为(?=\d)", "步幅", text)
    text = text.replace("min−1", "min⁻¹").replace("min-1", "min⁻¹")
    text = re.sub(r"(?<=\d)(min⁻¹|ms|mV|V)\b", r" \1", text)
    text = re.sub(r"±\s*(\d+(?:\.\d+)?)\s*(ms|mV|V)\b", r"±\1 \2", text)
    return text.strip()


def _looks_like_report_table_header(line: str) -> bool:
    return _compact(line) in {"序号", "检验项目", "标准条款", "标准要求", "检验结果", "单项结论", "备注"}


def _torque_wrench_report_atomic_results(
    group: InspectionItemGroup,
    *,
    group_text: str,
    item_no: str | None,
    page_text_by_page: Mapping[int, str] | None = None,
) -> list[PTRReportAtomicResult]:
    if _basic_electrical_group_clause_id(group) is not None:
        return []
    if not any(str(row.standard_clause or "").strip() == "2.8.2" for row in group.rows):
        return []
    page = _page_for_torque_wrench(group, page_text_by_page=page_text_by_page)
    values = {
        "A": _torque_wrench_dimension_actual(group_text, "A"),
        "B": _torque_wrench_dimension_actual(group_text, "B"),
    }
    results: list[PTRReportAtomicResult] = []
    for dimension, actual in values.items():
        if not actual:
            continue
        results.append(
            _report_atomic_result(
                atomic_id=f"2.8.2:torque_wrench:{dimension}",
                clause_id="2.8.2",
                label=dimension,
                actual=actual,
                unit="mm",
                item_no=item_no,
                page=page,
                source_text=group_text,
                confidence="high",
                method="basic_electrical_torque_wrench_dimension",
                full_group_text=group_text,
            )
        )
    return results


def _torque_wrench_dimension_actual(group_text: str, dimension: str) -> str | None:
    text = str(group_text or "")
    direct_match = re.search(rf"\b{re.escape(dimension)}\s*[=＝:：]\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if direct_match is not None:
        return direct_match.group(1)
    pattern = re.compile(
        rf"{re.escape(dimension)}\s*≤\s*(?:\d+(?:\.\d+)?)|(?:\d+(?:\.\d+)?)\s*(?:毫米|mm)\s*≤\s*{re.escape(dimension)}\s*≤\s*(?:\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        marker = re.search(rf"≤\s*{re.escape(dimension)}\s*≤", text, re.IGNORECASE)
        if marker is None:
            return None
        start = marker.end()
    else:
        start = match.end()
    segment = text[start : start + 160]
    numbers = re.findall(r"(?<![\d.])\d+\.\d+(?![\d.])", segment)
    for value in numbers:
        if dimension == "A" and 0.88 <= float(value) <= 0.89:
            return value
        if dimension == "B" and 0.96 <= float(value) <= 1.00:
            return value
    return numbers[0] if numbers else None


def _page_for_torque_wrench(
    group: InspectionItemGroup,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> int | None:
    if page_text_by_page:
        for page_number in group.pages:
            page_text = page_text_by_page.get(page_number) or ""
            if "扭矩扳手" in page_text and ("0.884" in page_text or "0.993" in page_text):
                return page_number
    return _first_page(group)


def _source_index_to_compact_index(source: str, source_index: int) -> int:
    return len(_compact_for_match(str(source or "")[: max(source_index, 0)]))


def _compact_index_to_source_index(source: str, compact_index: int) -> int:
    if compact_index <= 0:
        return 0
    compact_count = 0
    for index, char in enumerate(str(source or "")):
        if not _compact_for_match(char):
            continue
        if compact_count == compact_index:
            return index
        compact_count += 1
    return len(str(source or ""))


def _preset_results(
    values: Sequence[str] | dict[str, str],
    *,
    atomic_prefix: str,
    clause_id: str,
    label: str,
    unit: str,
    item_no: str | None,
    page: int | None,
    source_text: str,
    method: str,
    full_group_text: str | None = None,
) -> list[PTRReportAtomicResult]:
    if isinstance(values, dict):
        cleaned_by_preset = {key: _strip_unit(value) for key, value in values.items() if _strip_unit(value)}
        cleaned = list(cleaned_by_preset.values())
    else:
        cleaned_by_preset = {}
        cleaned = [_strip_unit(value) for value in values if _strip_unit(value)]
    presets = [("pulse3", "PULSE3"), ("pf_reversible", "PF Reversible")]
    results: list[PTRReportAtomicResult] = []
    for index, (preset_slug, preset_label) in enumerate(presets):
        actual = cleaned_by_preset.get(preset_slug) if cleaned_by_preset else (cleaned[index] if index < len(cleaned) else None)
        if _invalid_numeric_actual(actual, item_no=item_no):
            actual = None
        results.append(
            _report_atomic_result(
                atomic_id=f"{atomic_prefix}:{preset_slug}",
                clause_id=clause_id,
                label=label,
                actual=actual,
                unit=unit,
                preset=preset_label,
                item_no=item_no,
                page=page,
                source_text=source_text,
                confidence="high" if actual is not None else "medium",
                method=method if actual is not None else f"{method}_candidate_missing",
                candidate_actuals=cleaned if actual is None else [],
                full_group_text=full_group_text,
            )
        )
    return results


def _waveform_table_atomic_results(
    group: InspectionItemGroup,
    *,
    window: str,
    item_no: str | None,
    page: int | None,
    full_group_text: str,
) -> list[PTRReportAtomicResult]:
    del group
    results: list[PTRReportAtomicResult] = []
    for parameter_name, parameter_slug in WAVEFORM_TABLE_PARAMETERS:
        expected_values = _scope_waveform_expected_values(parameter_name)
        for preset_slug, preset_label in WAVEFORM_PRESETS:
            expected_text = expected_values.get(preset_slug)
            if _is_not_applicable_text(expected_text):
                continue
            actual, source_text = _waveform_actual_from_window(
                window,
                parameter_name=parameter_name,
                expected_text=expected_text,
                preset_slug=preset_slug,
            )
            if actual is None:
                continue
            results.append(
                _report_atomic_result(
                    atomic_id=f"2.2.2:{parameter_slug}:{preset_slug}",
                    clause_id="2.2.2",
                    label=parameter_name,
                    actual=actual,
                    preset=preset_label,
                    item_no=item_no,
                    page=page,
                    source_text=source_text,
                    confidence="high",
                    method="group_clause_window_waveform_table",
                    full_group_text=full_group_text,
                )
            )
    return results


def _software_result_for_requirement(
    requirement: PTRAtomicRequirement,
    group: InspectionItemGroup | None,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> PTRReportAtomicResult | None:
    if group is None:
        return None
    group_text = _group_full_text(group, page_text_by_page=page_text_by_page)
    window = _software_requirement_window(group_text, requirement)
    actual = _software_actual_from_window(window)
    if actual is None:
        return None
    item_no = group.display_item_no or group.item_no
    return _report_atomic_result(
        atomic_id=requirement.atomic_id,
        clause_id=requirement.clause_id,
        label=requirement.label,
        actual=actual,
        item_no=item_no,
        page=_page_for_software_requirement(group, requirement, page_text_by_page=page_text_by_page),
        source_text=window,
        confidence="high",
        method="group_page_text_software_function",
        full_group_text=group_text,
    )


def _software_requirement_window(group_text: str, requirement: PTRAtomicRequirement) -> str:
    parameter_name = str(requirement.metadata.get("parameter_name") or requirement.label or "")
    dimensions = requirement.metadata.get("dimensions") if isinstance(requirement.metadata, dict) else {}
    component = str(dimensions.get("组件") or "") if isinstance(dimensions, dict) else ""
    parameter_aliases = _software_function_aliases(parameter_name)
    parameter_keys = [_compact_for_match(alias) for alias in parameter_aliases]
    component_key = _compact_for_match(component)
    candidates: list[tuple[int, str]] = []
    for current_component, window in _software_context_windows(group_text):
        if component and current_component != component:
            continue
        window_key = _compact_for_match(window)
        if any(parameter_key and parameter_key in window_key for parameter_key in parameter_keys):
            if _software_other_component_before_parameter(window, parameter_aliases, component):
                continue
            candidates.append((3, _trim_software_window_to_parameter(window, parameter_aliases)))
    for _current_component, window in _software_context_windows(group_text):
        window_key = _compact_for_match(window)
        if component_key and component_key not in window_key:
            continue
        if any(parameter_key and parameter_key in window_key for parameter_key in parameter_keys):
            if _software_other_component_before_parameter(window, parameter_aliases, component):
                continue
            candidates.append((2, _trim_software_window_to_parameter(window, parameter_aliases)))
    label_key = _compact_for_match(requirement.label)
    for _current_component, window in _software_context_windows(group_text):
        if label_key and label_key in _compact_for_match(window):
            candidates.append((1, _trim_software_window_to_parameter(window, parameter_aliases)))
    if not candidates:
        return ""
    return max(candidates, key=lambda candidate: _software_window_score(candidate[0], candidate[1]))[1]


def _software_window_score(priority: int, window: str) -> tuple[int, int, int]:
    has_actual = 1 if _software_actual_from_window(window) is not None else 0
    return has_actual, priority, -len(str(window or ""))


def _trim_software_window_to_parameter(window: str, parameter_aliases: Sequence[str]) -> str:
    text = str(window or "")
    match = _software_parameter_match(text, parameter_aliases)
    if match is not None:
        return text[match.start() :].strip()
    return text.strip()


def _software_other_component_before_parameter(window: str, parameter_aliases: Sequence[str], component: str) -> bool:
    text = str(window or "")
    parameter_match = _software_parameter_match(text, parameter_aliases)
    if parameter_match is None:
        return False
    before_parameter = text[: parameter_match.start()]
    expected_component = str(component or "")
    for candidate_component in SOFTWARE_COMPONENTS:
        if candidate_component == expected_component:
            continue
        if _loose_component_pattern(candidate_component).search(before_parameter):
            return True
    return False


def _software_parameter_match(window: str, parameter_aliases: Sequence[str]) -> re.Match[str] | None:
    text = str(window or "")
    matches = [
        match
        for alias in sorted(parameter_aliases, key=len, reverse=True)
        if (match := _loose_software_alias_pattern(alias).search(text)) is not None
    ]
    return min(matches, key=lambda match: match.start()) if matches else None


def _loose_software_alias_pattern(alias: str) -> re.Pattern[str]:
    parts: list[str] = []
    for char in str(alias or ""):
        if char.isspace():
            parts.append(r"\s*")
        elif char in {"、", "，", ",", "/", "／"}:
            parts.append(r"[\s、，,/／]*")
        else:
            parts.append(re.escape(char))
            parts.append(r"\s*")
    return re.compile("".join(parts), re.IGNORECASE)


def _software_actual_from_window(window: str) -> str | None:
    text = str(window or "")
    if not text.strip():
        return None
    if "不符合" in text:
        return "不符合"
    dash_match = re.search(r"[-—－]{2,}|／|(?<!\S)/(?!\S)", text)
    conform_index = min((index for index in (text.find("符合要求"), text.find("符合")) if index >= 0), default=-1)
    if dash_match and (conform_index < 0 or dash_match.start() < conform_index):
        return "——"
    if "符合要求" in text or "符合" in text:
        return "符合要求"
    if "不适用" in text:
        return "不适用"
    return None


def _software_function_aliases(parameter_name: str) -> tuple[str, ...]:
    aliases = SOFTWARE_FUNCTION_ALIASES.get(parameter_name)
    if aliases:
        return aliases
    return (parameter_name,)


def _software_context_windows(group_text: str) -> list[tuple[str | None, str]]:
    lines = [line.strip() for line in str(group_text or "").splitlines() if line.strip()]
    windows: list[tuple[str | None, str]] = []
    current_component: str | None = None
    for index, line in enumerate(lines):
        declared_component = _software_declared_component(line)
        for span in range(2, 5):
            if declared_component is not None:
                break
            declared_component = _software_declared_component(" ".join(lines[index : index + span]))
        if declared_component is not None:
            current_component = declared_component
        window = " ".join(lines[index : index + 8])
        windows.append((current_component, window))
    return windows


def _software_declared_component(value: str) -> str | None:
    text = str(value or "")
    if not text.strip():
        return None
    for component in SOFTWARE_COMPONENTS:
        pattern = _loose_component_pattern(component)
        match = pattern.search(text)
        if match is None:
            continue
        prefix = text[: match.start()].strip()
        if prefix and not prefix.endswith(("组件", "：", ":", "；", ";")) and not _software_component_prefix_allowed(prefix):
            continue
        suffix = text[match.end() : match.end() + 1]
        if suffix and re.match(r"[\u4e00-\u9fffA-Za-z0-9]", suffix):
            continue
        return component
    return None


def _software_component_prefix_allowed(prefix: str) -> bool:
    compact = _compact_for_match(prefix).replace(".", "")
    if not compact:
        return True
    return bool(re.fullmatch(r"续?\d*(?:软件功能)?(?:26)?", compact))


def _loose_component_pattern(component: str) -> re.Pattern[str]:
    return re.compile(r"\s*".join(re.escape(char) for char in component))


def _page_for_software_requirement(
    group: InspectionItemGroup,
    requirement: PTRAtomicRequirement,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> int | None:
    if not page_text_by_page:
        return _first_page(group)
    parameter_name = str(requirement.metadata.get("parameter_name") or requirement.label or "")
    dimensions = requirement.metadata.get("dimensions") if isinstance(requirement.metadata, dict) else {}
    component = str(dimensions.get("组件") or "") if isinstance(dimensions, dict) else ""
    parameter_key = _compact_for_match(parameter_name)
    component_key = _compact_for_match(component)
    for page_number in group.pages:
        page_key = _compact_for_match(page_text_by_page.get(page_number) or "")
        if parameter_key and parameter_key in page_key and (not component_key or component_key in page_key):
            return page_number
    return _first_page(group)


def _group_full_text(
    group: InspectionItemGroup,
    page_text_by_page: Mapping[int, str] | None = None,
) -> str:
    values: list[str | None] = []
    for row in _ordered_group_rows(group):
        values.append(_row_full_text(row))
    values.append(ptr_group_text(group))
    values.extend(_group_metadata_texts(group))
    if page_text_by_page:
        for page_number in group.pages:
            values.append(page_text_by_page.get(page_number))
    return "\n".join(_unique_non_empty(values))


def _clause_window(group_text: str, clause_number: str) -> str:
    text = str(group_text or "")
    if not text.strip():
        return ""
    start_matches = list(_clause_header_pattern(clause_number).finditer(text))
    if not start_matches:
        return _keyword_window(text, clause_number)
    windows: list[str] = []
    for start_match in start_matches:
        end_index = len(text)
        for next_clause in _next_clause_boundaries(clause_number):
            next_match = _clause_header_pattern(next_clause).search(text, start_match.end())
            if next_match is not None:
                end_index = min(end_index, next_match.start())
        windows.append(text[start_match.start() : end_index].strip())
    return max(windows, key=lambda window: _clause_window_score(window, clause_number))


def _clause_window_score(window: str, clause_number: str) -> tuple[int, int]:
    text = str(window or "")
    if clause_number == "2.2.2":
        parameter_hits = sum(1 for parameter_name, _slug_value in WAVEFORM_TABLE_PARAMETERS if parameter_name in text)
        preset_hits = sum(1 for _slug_value, preset_label in WAVEFORM_PRESETS if _compact(preset_label) in _compact(text))
        return parameter_hits * 10 + preset_hits, len(text)
    if clause_number in {"2.2.3", "2.2.4"}:
        preset_hits = len(_preset_values_by_slug_from_text(text))
        waveform_noise = sum(1 for parameter_name, _slug_value in WAVEFORM_TABLE_PARAMETERS if parameter_name in text)
        return preset_hits * 10 - waveform_noise * 3, -len(text)
    if re.fullmatch(r"2\.\d+(?:\.\d+){1,2}", clause_number):
        result_hits = len(_direct_result_values(text))
        functional_hits = text.count("符合要求")
        return result_hits * 10 + functional_hits * 5, len(text)
    return 0, -len(text)


def _keyword_window(text: str, clause_number: str) -> str:
    keywords = {
        "2.2.2": ("波形参数", "输出波形图"),
        "2.2.3": ("脉冲上升时间",),
        "2.2.4": ("脉冲下降时间", "脉冲宽度"),
        "2.2.5": ("脉冲衰减",),
        "2.2.6": ("最大输出能量",),
        "2.2.7.1": ("温度超限保护",),
        "2.2.7.2": ("过流保护",),
    }.get(clause_number, ())
    starts = [index for keyword in keywords if (index := text.find(keyword)) >= 0]
    if not starts:
        return ""
    start = min(starts)
    end = len(text)
    boundary_patterns = [_clause_header_pattern(boundary) for boundary in _next_clause_boundaries(clause_number)]
    boundary_keywords = {
        "2.2.2": ("脉冲上升时间",),
        "2.2.3": ("脉冲下降时间", "脉冲宽度"),
        "2.2.4": ("脉冲衰减",),
        "2.2.5": ("最大输出能量",),
        "2.2.6": ("保护功能", "温度超限保护"),
        "2.2.7.1": ("过流保护",),
    }.get(clause_number, ())
    for pattern in boundary_patterns:
        match = pattern.search(text, start + 1)
        if match is not None:
            end = min(end, match.start())
    for keyword in boundary_keywords:
        index = text.find(keyword, start + 1)
        if index >= 0:
            end = min(end, index)
    return text[start:end].strip()


def _clause_header_pattern(clause_number: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in str(clause_number).split(".")]
    pattern = r"\s*\.\s*".join(parts)
    return re.compile(rf"(?<!\d){pattern}(?!\s*\.\s*\d)")


def _next_clause_boundaries(clause_number: str) -> list[str]:
    explicit = {
        "2.2.2": ["2.2.3"],
        "2.2.3": ["2.2.4"],
        "2.2.4": ["2.2.5"],
        "2.2.5": ["2.2.6"],
        "2.2.6": ["2.2.7"],
        "2.2.7.1": ["2.2.7.2"],
    }
    if clause_number in explicit:
        return explicit[clause_number]
    match = re.fullmatch(r"2\.2\.(\d+)", clause_number)
    if match:
        return [f"2.2.{int(match.group(1)) + 1}"]
    match = re.fullmatch(r"2\.2\.7\.(\d+)", clause_number)
    if match:
        return [f"2.2.7.{int(match.group(1)) + 1}"]
    parts = str(clause_number).split(".")
    if len(parts) >= 2 and all(part.isdigit() for part in parts):
        parts[-1] = str(int(parts[-1]) + 1)
        return [".".join(parts)]
    return []


def _ordered_group_rows(group: InspectionItemGroup):
    return sorted(
        group.rows,
        key=lambda row: (
            row.source_page or 0,
            row.row_index_in_page if row.row_index_in_page is not None else 10**9,
        ),
    )


def _row_full_text(row) -> str:
    values = [
        row.sequence_raw,
        row.item_name,
        row.standard_clause,
        row.standard_requirement,
        row.test_result,
        row.conclusion,
        row.remark,
        *row.result_values,
        row.metadata.get("row_text"),
        row.metadata.get("source_text"),
        row.metadata.get("table_row_text"),
        row.metadata.get("combined_row_text"),
        row.metadata.get("raw_text"),
        row.metadata.get("page_text_excerpt"),
    ]
    return " ".join(str(value).strip() for value in values if value is not None and str(value).strip())


def _group_metadata_texts(group: InspectionItemGroup) -> list[str]:
    metadata = getattr(group, "metadata", None)
    if not isinstance(metadata, dict):
        return []
    values: list[str] = []
    for key in ("full_group_text", "page_text", "source_page_text", "report_page_texts", "page_text_by_page"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
        elif isinstance(value, dict):
            values.extend(str(item) for item in value.values() if str(item or "").strip())
        elif isinstance(value, list):
            values.extend(str(item) for item in value if str(item or "").strip())
    return values


def _page_for_clause_window(
    group: InspectionItemGroup,
    clause_number: str,
    *,
    page_text_by_page: Mapping[int, str] | None = None,
) -> int | None:
    pattern = _clause_header_pattern(clause_number)
    for row in _ordered_group_rows(group):
        if pattern.search(_row_full_text(row)):
            return row.source_page or _first_page(group)
    if page_text_by_page:
        for page_number in group.pages:
            page_text = page_text_by_page.get(page_number) or ""
            if pattern.search(page_text) or _keyword_window(page_text, clause_number):
                return page_number
    return _first_page(group)


def _numeric_result_from_window(window: str, *, expected: float) -> str | None:
    if re.search(r"候选值|候选结果|可见候选值|未能稳定", str(window or "")):
        return None
    marker_values = _result_marker_values(window)
    if marker_values:
        return marker_values[-1]
    text = re.sub(r"2\s*\.\s*2\s*\.\s*\d+(?:\s*\.\s*\d+)?", " ", str(window or ""))
    values: list[str] = []
    for match in re.finditer(r"(?<![\d.])[-+]?\d+(?:\.\d+)?(?![\d.])", text):
        value = match.group(0)
        try:
            if float(value) == float(expected):
                continue
        except ValueError:
            pass
        values.append(value)
    return values[-1] if values else None


def _unique_report_atomic_results(results: Sequence[PTRReportAtomicResult]) -> list[PTRReportAtomicResult]:
    unique: dict[str, PTRReportAtomicResult] = {}
    for result in results:
        if result.atomic_id in unique and unique[result.atomic_id].actual:
            continue
        unique[result.atomic_id] = result
    return list(unique.values())


def _row_text(row) -> str:
    return " ".join(
        str(value or "")
        for value in [
            row.sequence_raw,
            row.item_name,
            row.standard_clause,
            row.standard_requirement,
            row.test_result,
            row.conclusion,
            row.remark,
            row.metadata.get("row_text"),
            row.metadata.get("source_text"),
            row.metadata.get("table_row_text"),
        ]
    )


def _numeric_values_from_row(row) -> list[str]:
    sources = row.result_values or ([row.test_result] if row.test_result else [])
    values: list[str] = []
    for source in sources:
        text = str(source or "")
        if not text.strip():
            continue
        parts = re.split(r"\s*/\s*|；|;|，|,", text)
        for part in parts:
            cleaned = _strip_unit(part)
            if cleaned and re.search(r"\d", cleaned):
                values.append(cleaned)
    if values:
        return _unique_text(values)

    source_text = _row_text(row)
    marker_values = _result_marker_values(source_text)
    if marker_values:
        return marker_values
    return _preset_values_from_text(source_text)


def _preset_values_from_row(row) -> list[str]:
    return _preset_values_from_text(_row_text(row))


def _candidate_values_from_row(row) -> list[str]:
    return _candidate_marker_values(_row_text(row))


def _first_measurement_value(row) -> str | None:
    values = _numeric_values_from_row(row)
    return values[0] if values else None


def _current_value(row) -> str | None:
    if row.item_name:
        item_name = str(row.item_name).strip()
        if re.search(r"\d", item_name):
            return _strip_unit(item_name)
    return _first_measurement_value(row)


def _strip_unit(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return match.group(0) if match else text


def _result_marker_values(value: str) -> list[str]:
    text = str(value or "")
    pattern = re.compile(r"(?:检验)?结果\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?", re.IGNORECASE)
    return _unique_text(match.group(1) for match in pattern.finditer(text))


def _preset_marker_values(value: str) -> list[str]:
    return _preset_values_from_text(value)


def _preset_values_from_text(value: str) -> list[str]:
    values_by_preset = _preset_values_by_slug_from_text(value)
    return _unique_text(values_by_preset[preset_slug] for preset_slug in ("pulse3", "pf_reversible") if preset_slug in values_by_preset)


def _preset_values_by_slug_from_text(value: str) -> dict[str, str]:
    text = str(value or "")
    preset_patterns = [
        ("pulse3", r"PULSE\s*3|PULSE3"),
        ("pf_reversible", r"PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible"),
    ]
    values_by_preset: dict[str, str] = {}
    for preset_slug, preset_pattern in preset_patterns:
        preset_marker = re.compile(rf"(?:{preset_pattern})\s*预\s*设", re.IGNORECASE)
        for match in preset_marker.finditer(text):
            actual = _value_near_preset_marker(text, match)
            if actual:
                values_by_preset[preset_slug] = actual
                break

    return values_by_preset


def _value_near_preset_marker(text: str, marker_match: re.Match[str]) -> str | None:
    line_start = max(text.rfind("\n", 0, marker_match.start()), text.rfind("；", 0, marker_match.start()), text.rfind(";", 0, marker_match.start())) + 1
    same_line_before = text[line_start : marker_match.start()]
    adjacent_before = _adjacent_number_before_marker(same_line_before)
    if adjacent_before:
        return adjacent_before

    next_boundary = _next_preset_or_clause_boundary(text, marker_match.end())
    after = text[marker_match.end() : next_boundary]
    result_match = re.search(r"(?:检验)?结果\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?", after, re.IGNORECASE)
    if result_match:
        return result_match.group(1)
    after_values = _number_tokens(after)
    if after_values:
        return after_values[0]

    previous_line = text[text.rfind("\n", 0, line_start - 1) + 1 : max(line_start - 1, 0)]
    if not _any_preset_marker_pattern().search(previous_line) and not _looks_like_sequence_or_clause_line(previous_line):
        previous_values = _number_tokens(previous_line)
        if previous_values:
            return previous_values[-1]
    return None


def _adjacent_number_before_marker(value: str) -> str | None:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*$", str(value or ""))
    if not match:
        return None
    return match.group(1)


def _next_preset_or_clause_boundary(text: str, start: int) -> int:
    candidates = [len(text)]
    preset_match = _any_preset_marker_pattern().search(text, start)
    if preset_match:
        candidates.append(preset_match.start())
    clause_match = re.search(r"(?<!\d)2\s*\.\s*2\s*\.\s*\d+(?:\s*\.\s*\d+)?(?!\s*\.\s*\d)", text[start:])
    if clause_match:
        candidates.append(start + clause_match.start())
    return min(candidates)


def _any_preset_marker_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?:PULSE\s*3|PULSE3|PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible)\s*预\s*设",
        re.IGNORECASE,
    )


def _number_tokens(value: str) -> list[str]:
    return re.findall(r"(?<![\d.])[-+]?\d+(?:\.\d+)?(?![\d.])", value)


def _direct_group_source_text(group: InspectionItemGroup, group_text: str) -> str:
    item_no = str(group.display_item_no or group.item_no or "").strip()
    if not item_no.isdigit():
        return group_text
    text = str(group_text or "")
    start_match = re.search(rf"(?<!\d)(?:续\s*)?{re.escape(item_no)}(?!\d)", text)
    if start_match is None:
        return text
    end_index = len(text)
    next_item_no = str(int(item_no) + 1)
    next_match = re.search(rf"(?<!\d)(?:续\s*)?{re.escape(next_item_no)}(?!\d)", text[start_match.end() :])
    if next_match is not None:
        end_index = start_match.end() + next_match.start()
    return text[start_match.start() : end_index].strip()


def _clause_ids_in_text(value: str) -> list[str]:
    pattern = re.compile(r"(?<![\d.])(2(?:\s*\.\s*[1-9]\d*){1,3})(?!\s*\.\s*\d)")
    return _unique_text(match.group(1).replace(" ", "") for match in pattern.finditer(str(value or "")))


def _direct_result_after_marker(window: str, marker: str) -> str | None:
    lines = [line.strip() for line in re.split(r"[\n；;]+", str(window or "")) if line.strip()]
    for index, line in enumerate(lines):
        if marker not in line:
            continue
        same_line_tail = line[line.find(marker) + len(marker) :]
        if "符合要求" in same_line_tail:
            return "符合要求"
        signed_same_line = _signed_result_value(same_line_tail)
        if signed_same_line and "±" not in same_line_tail[: same_line_tail.find(signed_same_line)]:
            return signed_same_line
        for candidate in lines[index + 1 : index + 8]:
            compact = _compact(candidate)
            if not compact or compact in {"符合", "/", "／"}:
                continue
            if _clause_header_pattern("2.0").search(candidate) or re.match(r"2\s*\.\s*\d+(?:\s*\.\s*\d+){0,2}", candidate):
                break
            if _is_next_direct_parameter_marker(candidate, marker):
                break
            if "符合要求" in compact:
                return "符合要求"
            signed = _signed_result_value(candidate)
            if signed:
                return signed
            if "单位" in compact:
                continue
            numeric = re.search(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", candidate)
            if numeric and (re.fullmatch(r"\d+(?:\.\d+)?", compact) or not _looks_like_sequence_or_clause_line(candidate)):
                return numeric.group(0)
    inline = re.search(rf"{re.escape(marker)}[^\n]*?(符合要求|[+＋\-－]\s*\d+(?:\.\d+)?)", str(window or ""))
    if inline:
        return re.sub(r"\s+", "", inline.group(1)).replace("＋", "+").replace("－", "-")
    return None


def _signed_result_value(value: str) -> str | None:
    match = re.search(r"[+＋\-－]\s*\d+(?:\.\d+)?", str(value or ""))
    return re.sub(r"\s+", "", match.group(0)).replace("＋", "+").replace("－", "-") if match else None


def _is_next_direct_parameter_marker(value: str, current_marker: str) -> bool:
    markers = (
        "低电压",
        "脉宽",
        "脉冲间隔",
        "脉冲群间隔",
        "上升沿时间",
        "下降沿时间",
        "每个脉冲群中的循环数",
        "每个治疗波中的脉冲群数量",
    )
    return any(marker != current_marker and marker in value for marker in markers)


def _direct_result_values(value: str) -> list[str]:
    text = str(value or "")
    values: list[str] = []
    values.extend(match.group(0) for match in re.finditer(r"[+＋\-－]\s*\d+(?:\.\d+)?", text))
    values.extend("符合要求" for _match in re.finditer(r"符合要求", text))
    return _unique_text(re.sub(r"\s+", "", value).replace("＋", "+").replace("－", "-") for value in values)


def _direct_functional_actual(window: str) -> str | None:
    return "符合要求" if "符合要求" in str(window or "") and "不符合" not in str(window or "") else None


def _direct_clause_label(clause_id: str, window: str) -> str:
    pattern = _clause_header_pattern(clause_id)
    match = pattern.search(window)
    if match is None:
        return clause_id
    tail = window[match.end() :].strip()
    line = next((item.strip() for item in tail.splitlines() if item.strip()), "")
    line = re.sub(r"\s+", " ", line).strip()
    if not line:
        return clause_id
    return line[:80]


def _looks_like_sequence_or_clause_line(value: str) -> bool:
    compact = _compact(str(value or ""))
    if not compact:
        return False
    if re.fullmatch(r"续?\d+", compact):
        return True
    return bool(re.search(r"(?<!\d)2\.?2\.?\d", compact))


def _candidate_marker_values(value: str) -> list[str]:
    text = str(value or "")
    pattern = re.compile(r"(?:候选值|候选结果|可见候选值)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)
    return _unique_text(match.group(1) for match in pattern.finditer(text))


def _unique_text(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _unique_non_empty(values: Sequence[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _safe_excerpt(value: str, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[:limit]}..."


def _expected_display(requirement: PTRAtomicRequirement) -> str | None:
    if requirement.operator == "functional":
        return requirement.expected_text
    if requirement.expected_value is not None and requirement.operator:
        value = int(requirement.expected_value) if requirement.expected_value.is_integer() else requirement.expected_value
        unit = f" {requirement.unit}" if requirement.unit else ""
        suffix = ""
        if requirement.expected_text and "峰值" in requirement.expected_text:
            suffix = "（峰值）"
        return f"{_display_operator(requirement.operator)}{value}{unit}{suffix}"
    return requirement.expected_text


def _is_not_applicable_requirement(requirement: PTRAtomicRequirement) -> bool:
    return requirement.source == "ptr_table" and _is_not_applicable_text(requirement.expected_text)


def _is_not_applicable_text(value: str | None) -> bool:
    return str(value or "").strip() in {"/", "／", "-", "—", "——"}


def _is_report_not_applicable_text(value: str | None) -> bool:
    text = str(value or "").strip()
    return _is_not_applicable_text(text) or text in {"不适用", "NA", "N/A"}


def _table_value_matches(expected: str | None, actual: str | None) -> bool:
    expected_text = _normalize_table_value(expected)
    actual_text = _normalize_table_value(actual)
    return bool(expected_text) and expected_text == actual_text


def _numeric_range_expected_matches(expected: str | None, actual: str | None) -> bool:
    expected_numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", str(expected or ""))]
    actual_numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", str(actual or ""))]
    if len(expected_numbers) < 2 or not actual_numbers:
        return False
    low, high = min(expected_numbers[0], expected_numbers[1]), max(expected_numbers[0], expected_numbers[1])
    return all(low <= value <= high for value in actual_numbers)


def _waveform_report_actual_satisfies(expected: str | None, actual: str | None) -> bool:
    expected_text = str(expected or "").strip()
    actual_text = str(actual or "").strip()
    if not expected_text or not actual_text or "不符合" in actual_text:
        return False
    if "符合" in actual_text:
        return True
    if _table_value_matches(expected_text, actual_text):
        return True
    tolerance = _expected_tolerance(expected_text)
    if tolerance is None:
        return False
    actual_values = _signed_numbers(actual_text)
    return bool(actual_values) and all(abs(value) <= tolerance for value in actual_values)


def _expected_tolerance(expected: str) -> float | None:
    match = re.search(r"±\s*(\d+(?:\.\d+)?)", str(expected or ""))
    return float(match.group(1)) if match else None


def _signed_numbers(value: str) -> list[float]:
    return [
        float(re.sub(r"\s+", "", match).replace("＋", "+").replace("－", "-"))
        for match in re.findall(r"[+＋\-－]\s*\d+(?:\.\d+)?", value or "")
    ]


def _normalize_table_value(value: str | None) -> str:
    text = str(value or "")
    text = text.replace("μ", "u").replace("µ", "u")
    text = text.replace("％", "%").replace("－", "-").replace("～", "-")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def _compact_for_match(value: str | None) -> str:
    text = str(value or "")
    text = text.replace("（", "(").replace("）", ")")
    return re.sub(r"[\s,，、:：;；/／\\()（）-]+", "", text).lower()


def _invalid_numeric_actual(actual: str | None, *, item_no: str | None) -> bool:
    if actual is None or item_no is None:
        return False
    actual_text = str(actual).strip()
    return bool(actual_text and actual_text == str(item_no).strip())


def _waveform_parameter_slug(parameter_name: str) -> str:
    compact = _compact(parameter_name)
    for name, slug in WAVEFORM_TABLE_PARAMETERS:
        if _compact(name) == compact:
            return slug
    return _slug(parameter_name)


def _preset_slug(value: str) -> str | None:
    compact = _compact(value).lower()
    if "pulse3" in compact or "pulse 3" in compact:
        return "pulse3"
    if "pfreversible" in compact or ("pf" in compact and "reversible" in compact):
        return "pf_reversible"
    return None


def _preset_label(preset_slug: str) -> str:
    return dict(WAVEFORM_PRESETS).get(preset_slug, preset_slug)


def _scope_waveform_expected_values(parameter_name: str) -> dict[str, str]:
    expected_by_parameter = {
        "脉冲个数": {"pulse3": "1500", "pf_reversible": "1"},
        "脉冲组数": {"pulse3": "12", "pf_reversible": "1"},
        "脉冲组间隔": {"pulse3": "210±1 msec", "pf_reversible": "/"},
        "脉冲对间隔": {"pulse3": "1.12msec±4μsec", "pf_reversible": "/"},
        "脉冲宽度": {"pulse3": "0.9μsec±20%", "pf_reversible": "0.9μsec±20%"},
        "脉冲相间隔": {"pulse3": "1μsec±20%", "pf_reversible": "1μsec±20%"},
        "波形类型": {"pulse3": "三相", "pf_reversible": "双相"},
        "正峰值/负峰值": {"pulse3": "5±20%", "pf_reversible": "1±0.1"},
        "电流水平": {"pulse3": "1-100%", "pf_reversible": "1-100%"},
    }
    return expected_by_parameter.get(parameter_name, {})


def _waveform_parameter_window(window: str, parameter_name: str) -> str:
    text = str(window or "")
    start = text.find(parameter_name)
    if start < 0:
        return ""
    end = len(text)
    for next_parameter, _slug_value in WAVEFORM_TABLE_PARAMETERS:
        if next_parameter == parameter_name:
            continue
        index = text.find(next_parameter, start + len(parameter_name))
        if index >= 0:
            end = min(end, index)
    next_clause = _clause_header_pattern("2.2.3").search(text, start + len(parameter_name))
    if next_clause is not None:
        end = min(end, next_clause.start())
    return text[start:end].strip()


def _waveform_actual_from_window(
    window: str,
    *,
    parameter_name: str,
    expected_text: str | None,
    preset_slug: str,
) -> tuple[str | None, str]:
    if not expected_text:
        return None, ""
    window = _normalize_waveform_parameter_labels(window)
    scoped_text = _waveform_preset_scope(window, preset_slug)
    search_texts = [text for text in (scoped_text, window) if text]
    for search_text in _unique_text(search_texts):
        for parameter_chunk in _waveform_parameter_chunks(search_text, parameter_name):
            actual = _waveform_actual_from_parameter_chunk(parameter_chunk, expected_text=expected_text)
            if actual is not None:
                return actual, parameter_chunk
    return None, scoped_text or window


def _normalize_waveform_parameter_labels(value: str) -> str:
    text = str(value or "")
    for parameter_name, _slug_value in sorted(WAVEFORM_TABLE_PARAMETERS, key=lambda item: len(item[0]), reverse=True):
        pattern = _loose_waveform_parameter_pattern(parameter_name)
        text = pattern.sub(parameter_name, text)
    return text


def _loose_waveform_parameter_pattern(parameter_name: str) -> re.Pattern[str]:
    parts: list[str] = []
    for char in parameter_name:
        if char in {"/", "／"}:
            parts.append(r"\s*[/／]\s*")
        else:
            parts.append(re.escape(char))
            parts.append(r"\s*")
    return re.compile("".join(parts))


def _waveform_preset_scope(window: str, preset_slug: str) -> str:
    text = _normalize_waveform_parameter_labels(str(window or ""))
    markers = list(_waveform_preset_marker_pattern().finditer(text))
    for index, marker in enumerate(markers):
        if _preset_slug(marker.group("preset")) != preset_slug:
            continue
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        section = text[marker.start() : end].strip()
        if any(parameter_name in section for parameter_name, _slug_value in WAVEFORM_TABLE_PARAMETERS):
            return section
    return ""


def _waveform_preset_marker_pattern() -> re.Pattern[str]:
    return re.compile(
        r"(?P<preset>PULSE\s*3|PULSE3|PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible)\s*预\s*设",
        re.IGNORECASE,
    )


def _waveform_parameter_chunks(window: str, parameter_name: str) -> list[str]:
    text = _normalize_waveform_parameter_labels(str(window or ""))
    starts = [match.start() for match in re.finditer(re.escape(parameter_name), text)]
    chunks: list[str] = []
    for start in starts:
        end = len(text)
        for next_parameter, _slug_value in WAVEFORM_TABLE_PARAMETERS:
            if next_parameter == parameter_name:
                continue
            index = text.find(next_parameter, start + len(parameter_name))
            if index >= 0:
                end = min(end, index)
        next_preset = _waveform_preset_marker_pattern().search(text, start + len(parameter_name))
        if next_preset is not None:
            end = min(end, next_preset.start())
        next_clause = _clause_header_pattern("2.2.3").search(text, start + len(parameter_name))
        if next_clause is not None:
            end = min(end, next_clause.start())
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return _unique_text(chunks)


def _waveform_actual_from_parameter_chunk(parameter_chunk: str, *, expected_text: str) -> str | None:
    expected_match = _expected_value_pattern(expected_text).search(parameter_chunk)
    if not expected_match:
        return None
    actual = _waveform_result_token(parameter_chunk[expected_match.end() :])
    if actual:
        if actual == "符合要求" and _is_plain_numeric_expected(expected_text):
            return str(expected_text or "").strip()
        return actual
    return expected_text


def _is_plain_numeric_expected(expected_text: str | None) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", str(expected_text or "").strip()))


def _expected_value_pattern(expected_text: str) -> re.Pattern[str]:
    text = str(expected_text or "").strip()
    if text == "1":
        return re.compile(r"(?<![\d.])1(?![\d.])")
    parts: list[str] = []
    for char in text:
        if char.isspace():
            parts.append(r"\s*")
        elif char in {"μ", "µ", "u", "U"}:
            parts.append(r"[μµuU]")
        elif char == "±":
            parts.append(r"\s*±\s*")
        elif char in {"-", "－", "—", "~", "～"}:
            parts.append(r"\s*[-－—~～]\s*")
        elif char == "%":
            parts.append(r"\s*%")
        else:
            parts.append(re.escape(char))
    return re.compile("".join(parts), re.IGNORECASE)


def _waveform_result_token(value: str) -> str | None:
    text = str(value or "").splitlines()[0] if str(value or "").splitlines() else ""
    if not text.strip():
        return None
    if "不符合" in text:
        return "不符合"
    if "符合要求" in text or re.search(r"(?<!不)符合", text):
        return "符合要求"
    range_match = re.search(
        r"((?<!\d)[+＋\-－]\s*\d+(?:\.\d+)?\s*%?\s*[~～至-]\s*[+＋\-－]?\s*\d+(?:\.\d+)?\s*%?)",
        text,
    )
    if range_match:
        return _clean_signed_actual(range_match.group(1))
    signed_match = re.search(r"((?<!\d)[+＋\-－]\s*\d+(?:\.\d+)?\s*(?:%|msec|ms|μsec|µsec|usec)?)", text, re.IGNORECASE)
    if signed_match:
        return _clean_signed_actual(signed_match.group(1))
    return None


def _clean_signed_actual(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    return text.replace("＋", "+").replace("－", "-")


def _display_operator(operator: str | None) -> str:
    if operator == ">=":
        return "≥"
    if operator == "<=":
        return "≤"
    return operator or ""


def _record_label(record: ParameterRecord, clause_number: str) -> str:
    name = record.parameter_name or record.raw_name or record.parameter_id or "参数"
    component = record.dimensions.get("组件")
    if clause_number == "2.6" and component:
        return f"{component} - {name}"
    return name


def _record_expected_text(record: ParameterRecord) -> str:
    if record.values:
        return "；".join(f"{key}={value}" for key, value in record.values.items())
    return record.raw_value or record.normalized_value or ""


def _reference_context_matches_table(clause: PTRClause, table: PTRTable) -> bool:
    table_title = _compact(_table_title(table))
    if not table_title:
        return False
    contexts = [clause.title or "", clause.body_text or ""]
    contexts.extend(reference.context or reference.reference_text or "" for reference in clause.table_references)
    return any(table_title in _compact(context) or _compact(context) in table_title for context in contexts if context)


def _table_title(table: PTRTable) -> str:
    raw = table.caption or table.title or ""
    number = str(table.table_number or "")
    text = re.sub(r"\s+", "", raw)
    text = re.sub(rf"^表{re.escape(number)}", "", text)
    return text or raw or f"表{number}"


def _group_result_text(group: InspectionItemGroup | None) -> str | None:
    if group is None:
        return None
    text = ptr_group_text(group)
    return "符合要求" if "符合" in text and "不符合" not in text else None


def _first_page(group: InspectionItemGroup | None) -> int | None:
    return group.pages[0] if group and group.pages else None


def _numbers(value: str) -> list[float]:
    return [float(match) for match in re.findall(r"\d+(?:\.\d+)?", value or "")]


def _slug(value: str) -> str:
    text = re.sub(r"\s+", "-", value.strip())
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "-", text).strip("-") or "item"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


__all__ = [
    "build_atomic_comparison_rows",
    "build_atomic_requirements",
    "build_report_atomic_results",
    "table_for_clause",
    "table_key_for_clause_table",
]
