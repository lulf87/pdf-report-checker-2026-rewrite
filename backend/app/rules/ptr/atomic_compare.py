from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.ptr_comparison import PTRAtomicComparisonRow, PTRAtomicRequirement, PTRReportAtomicResult
from app.domain.table import ParameterRecord
from app.rules.ptr.report_item_grouping import ptr_group_text


TEXT_REQUIREMENTS: dict[str, list[dict[str, Any]]] = {
    "2.2.1": [
        {
            "suffix": "voltage",
            "label": "电压",
            "expected_text": "3333V（峰值）",
            "expected_value": 3333,
            "operator": ">=",
            "unit": "V",
        },
        {
            "suffix": "current",
            "label": "电流",
            "expected_text": "57A（峰值）",
            "expected_value": 57,
            "operator": ">=",
            "unit": "A",
        },
    ],
    "2.2.3": [
        {
            "suffix": "rise_time:pulse3",
            "label": "脉冲上升时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
            "preset": "PULSE3",
        },
        {
            "suffix": "rise_time:pf_reversible",
            "label": "脉冲上升时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
            "preset": "PF Reversible",
        }
    ],
    "2.2.4": [
        {
            "suffix": "fall_time:pulse3",
            "label": "脉冲下降时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
            "preset": "PULSE3",
        },
        {
            "suffix": "fall_time:pf_reversible",
            "label": "脉冲下降时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
            "preset": "PF Reversible",
        }
    ],
    "2.2.5": [
        {
            "suffix": "decay",
            "label": "脉冲衰减",
            "expected_text": "不超过 10%",
            "expected_value": 10,
            "operator": "<=",
            "unit": "%",
        }
    ],
    "2.2.6": [
        {
            "suffix": "max_energy",
            "label": "单个脉冲最大输出能量",
            "expected_text": "小于 258mJ",
            "expected_value": 258,
            "operator": "<",
            "unit": "mJ",
        }
    ],
    "2.2.7.1": [
        {
            "suffix": "temperature_limit_protection",
            "label": "温度超限保护",
            "expected_text": "具有温度超限保护功能",
            "operator": "functional",
        }
    ],
    "2.2.7.2": [
        {
            "suffix": "over_current_protection",
            "label": "过流保护",
            "expected_text": "具有过流保护功能",
            "operator": "functional",
        }
    ],
}

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


def build_atomic_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    clause_number = str(clause.number)
    if clause_number in TEXT_REQUIREMENTS:
        return [_text_requirement(clause_number, spec) for spec in TEXT_REQUIREMENTS[clause_number]]
    if clause_number in {"2.2.2", "2.6"}:
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


def _text_requirement(clause_number: str, spec: dict[str, Any]) -> PTRAtomicRequirement:
    return PTRAtomicRequirement(
        atomic_id=f"{clause_number}:{spec['suffix']}",
        clause_id=clause_number,
        label=spec["label"],
        expected_text=spec.get("expected_text"),
        expected_value=spec.get("expected_value"),
        operator=spec.get("operator"),
        unit=spec.get("unit"),
        source="ptr_text",
        metadata={"preset": spec["preset"]} if spec.get("preset") else {},
    )


def _table_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    clause_number = str(clause.number)
    table = table_for_clause(clause, ptr_doc)
    if table is None or table.canonical_table is None:
        if clause_number == "2.2.2":
            return _fallback_waveform_table_requirements(clause_number)
        if clause_number == "2.6":
            return _fallback_software_table_requirements(clause_number)
        return []
    if clause_number == "2.2.2":
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
        if requirement.clause_id == "2.6":
            return None, _first_page(group), item_no
        return None, _first_page(group), item_no

    for row in group.rows:
        row_text = " ".join(str(value or "") for value in [row.sequence_raw, row.item_name, row.standard_requirement, row.test_result])
        if _row_matches_requirement(requirement, row_text):
            actual = _row_actual(requirement, row)
            if actual:
                return actual, row.source_page or _first_page(group), item_no
    return None, _first_page(group), item_no


def _row_matches_requirement(requirement: PTRAtomicRequirement, row_text: str) -> bool:
    compact = _compact(row_text)
    atomic_id = requirement.atomic_id
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
        if _table_value_matches(requirement.expected_text, actual):
            return "match", "报告表格结果与 PTR 表格要求一致。"
        return "mismatch", f"报告结果 {actual} 与 PTR 要求 {requirement.expected_text or '无'} 不一致。"
    if requirement.operator == "functional":
        if actual and "符合" in actual:
            return "match", "报告检验结果显示符合。"
        if candidate_actuals:
            return "candidate_found_needs_mapping", "报告中找到候选结果，但未完成结构化绑定。"
        return "needs_review", "报告功能性结果未能稳定抽取，需复核。"
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
        parameter_window = _waveform_parameter_window(window, parameter_name)
        if not parameter_window:
            continue
        expected_values = _scope_waveform_expected_values(parameter_name)
        for preset_slug, preset_label in WAVEFORM_PRESETS:
            expected_text = expected_values.get(preset_slug)
            if _is_not_applicable_text(expected_text):
                continue
            actual = _waveform_actual_from_parameter_window(
                parameter_window,
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
                    source_text=parameter_window,
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
    parameter_key = _compact_for_match(parameter_name)
    component_key = _compact_for_match(component)
    best_line = ""
    for line in str(group_text or "").splitlines():
        line_key = _compact_for_match(line)
        if not parameter_key or parameter_key not in line_key:
            continue
        if component_key and component_key not in line_key:
            continue
        best_line = line.strip()
        break
    if best_line:
        return best_line
    label_key = _compact_for_match(requirement.label)
    for line in str(group_text or "").splitlines():
        if label_key and label_key in _compact_for_match(line):
            return line.strip()
    return ""


def _software_actual_from_window(window: str) -> str | None:
    text = str(window or "")
    if not text.strip():
        return None
    if "不符合" in text:
        return "不符合"
    if "符合要求" in text or "符合" in text:
        return "符合要求"
    if re.search(r"[-—－]{2,}|／|(?<!\S)/(?!\S)", text):
        return "——"
    if "不适用" in text:
        return "不适用"
    return None


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


def _waveform_actual_from_parameter_window(
    parameter_window: str,
    *,
    expected_text: str | None,
    preset_slug: str,
) -> str | None:
    if not expected_text:
        return None
    normalized_expected = _normalize_table_value(expected_text)
    if normalized_expected and normalized_expected in _normalize_table_value(parameter_window):
        return expected_text
    preset_values = _preset_values_by_slug_from_text(parameter_window)
    preset_actual = preset_values.get(preset_slug)
    if preset_actual:
        return preset_actual
    return None


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
