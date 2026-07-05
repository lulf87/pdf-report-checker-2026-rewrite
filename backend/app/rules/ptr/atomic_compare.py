from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from app.domain.inspection_group import InspectionItemGroup
from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.ptr_comparison import PTRAtomicComparisonRow, PTRAtomicRequirement
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
    return [_comparison_row(requirement, group) for requirement in requirements]


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


def _comparison_row(requirement: PTRAtomicRequirement, group: InspectionItemGroup | None) -> PTRAtomicComparisonRow:
    actual, page, item_no = _actual_for_requirement(requirement, group)
    status, reason = _status_and_reason(requirement, actual, group)
    return PTRAtomicComparisonRow(
        atomic_id=requirement.atomic_id,
        clause_id=requirement.clause_id,
        label=requirement.label,
        expected=_expected_display(requirement),
        actual=actual,
        status=status,
        reason=reason,
        report_page=page,
        report_item_no=item_no,
        source=requirement.source,
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


def _status_and_reason(requirement: PTRAtomicRequirement, actual: str | None, group: InspectionItemGroup | None) -> tuple[str, str]:
    if requirement.source == "ptr_table":
        if requirement.clause_id == "2.6":
            item_no = (group.display_item_no or group.item_no) if group else "未编号"
            return "needs_review", f"报告序号 {item_no} 仅有软件功能总项，表格功能明细需复核。"
        item_no = (group.display_item_no or group.item_no) if group else "未编号"
        return "needs_review", f"报告序号 {item_no} 未稳定展开表格参数结果，需复核。"
    if requirement.operator == "functional":
        if actual and "符合" in actual:
            return "match", "报告检验结果显示符合。"
        return "needs_review", "报告功能性结果未能稳定抽取，需复核。"
    if actual is None:
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
    "table_for_clause",
    "table_key_for_clause_table",
]
