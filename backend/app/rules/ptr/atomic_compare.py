from __future__ import annotations

import re
from collections.abc import Sequence
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
            "suffix": "rise_time",
            "label": "脉冲上升时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
        }
    ],
    "2.2.4": [
        {
            "suffix": "fall_time",
            "label": "脉冲下降时间",
            "expected_text": "不超过 700ns",
            "expected_value": 700,
            "operator": "<=",
            "unit": "ns",
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
) -> list[PTRAtomicComparisonRow]:
    requirements = build_atomic_requirements(clause, ptr_doc)
    if not requirements:
        return []
    group = report_matches[0] if report_matches else None
    report_atomic_results = build_report_atomic_results(group) if group is not None else []
    rows: list[PTRAtomicComparisonRow] = []
    for requirement in requirements:
        bound_results = _report_results_for_requirement(requirement, report_atomic_results)
        if bound_results:
            rows.extend(_comparison_row(requirement, group, result) for result in bound_results)
            continue
        rows.append(_comparison_row(requirement, group))
    return rows


def build_report_atomic_results(group: InspectionItemGroup | None) -> list[PTRReportAtomicResult]:
    if group is None:
        return []
    results: list[PTRReportAtomicResult] = []
    item_no = group.display_item_no or group.item_no

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
    )


def _table_requirements(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRAtomicRequirement]:
    clause_number = str(clause.number)
    table = table_for_clause(clause, ptr_doc)
    if table is None or table.canonical_table is None:
        return []
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
        preset = None
        unit = requirement.unit
        atomic_id = requirement.atomic_id

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
        if requirement.clause_id == "2.6":
            return _group_result_text(group), _first_page(group), item_no
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
    if atomic_id.endswith(":rise_time"):
        return "2.2.3" in compact or "上升" in compact
    if atomic_id.endswith(":fall_time"):
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
    if requirement.atomic_id.endswith(":fall_time"):
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
        if requirement.clause_id == "2.6":
            item_no = (group.display_item_no or group.item_no) if group else "未编号"
            return "needs_review", f"报告序号 {item_no} 仅有软件功能总项，表格功能明细需复核。"
        item_no = (group.display_item_no or group.item_no) if group else "未编号"
        return "needs_review", f"报告序号 {item_no} 未稳定展开表格参数结果，需复核。"
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
) -> PTRReportAtomicResult:
    return PTRReportAtomicResult(
        atomic_id=atomic_id,
        clause_id=clause_id,
        label=label,
        actual=actual,
        unit=unit,
        preset=preset,
        report_item_no=item_no,
        report_page=page,
        source_text=_safe_excerpt(source_text),
        confidence=confidence,
        candidate_actuals=list(candidate_actuals or []),
        diagnostics=[
            {
                "method": method,
                "confidence": confidence,
                "source_text_excerpt": _safe_excerpt(source_text),
            }
        ],
    )


def _preset_results(
    values: Sequence[str],
    *,
    atomic_prefix: str,
    clause_id: str,
    label: str,
    unit: str,
    item_no: str | None,
    page: int | None,
    source_text: str,
    method: str,
) -> list[PTRReportAtomicResult]:
    cleaned = [_strip_unit(value) for value in values if _strip_unit(value)]
    presets = [("pulse3", "PULSE3"), ("pf_reversible", "PF Reversible")]
    results: list[PTRReportAtomicResult] = []
    for index, (preset_slug, preset_label) in enumerate(presets):
        actual = cleaned[index] if index < len(cleaned) else None
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
            )
        )
    return results


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
    text = str(value or "")
    preset_patterns = [
        ("pulse3", r"PULSE\s*3|PULSE3"),
        ("pf_reversible", r"PF\s*Reversi\s*ble|PFReversi\s*ble|PF\s*Reversible|PFReversible"),
    ]
    values_by_preset: dict[str, str] = {}
    for preset_slug, preset_pattern in preset_patterns:
        value_before = re.compile(
            rf"([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?\s*(?:{preset_pattern})\s*预设",
            re.IGNORECASE,
        )
        value_after = re.compile(
            rf"(?:{preset_pattern})\s*预设[^\d\n]{{0,40}}(?:检验)?结果\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?",
            re.IGNORECASE,
        )
        loose_same_line_after = re.compile(
            rf"(?:{preset_pattern})\s*预设[^\d\n]{{0,20}}([-+]?\d+(?:\.\d+)?)\s*(?:ns|mJ|%|V|A)?",
            re.IGNORECASE,
        )
        for pattern in (value_after, value_before, loose_same_line_after):
            match = pattern.search(text)
            if match:
                values_by_preset[preset_slug] = match.group(1)
                break

    return _unique_text(values_by_preset[preset_slug] for preset_slug, _ in preset_patterns if preset_slug in values_by_preset)


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
