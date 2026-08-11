from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.ptr import PTRClause, PTRDocument
from app.domain.ptr_comparison import PTRAtomicRequirement


class RequirementType(StrEnum):
    NUMERIC_LIMIT = "numeric_limit"
    NUMERIC_RANGE = "numeric_range"
    TABLE_DRIVEN = "table_driven"
    FUNCTIONAL = "functional"
    EXTERNAL_STANDARD_COVERAGE = "external_standard_coverage"
    SOFTWARE_FUNCTION_TABLE = "software_function_table"
    EXCLUDED_BY_SCOPE = "excluded_by_scope"
    UNKNOWN_NEEDS_REVIEW = "unknown_needs_review"


@dataclass(frozen=True)
class RequirementClassification:
    requirement_type: RequirementType
    atomic_requirements: list[PTRAtomicRequirement] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class NumericLimitExpression:
    operator: str
    value: float
    unit: str | None
    raw_text: str


def classify_requirement(clause: PTRClause, ptr_doc: PTRDocument | None = None) -> RequirementClassification:
    text = clause_local_text(clause)

    if _has_table_reference(clause, text):
        if _is_software_function_table(clause, text):
            return RequirementClassification(requirement_type=RequirementType.SOFTWARE_FUNCTION_TABLE)
        return RequirementClassification(
            requirement_type=RequirementType.TABLE_DRIVEN,
            atomic_requirements=_table_local_requirements(clause, text),
        )

    mixed_torque_requirements = _mixed_torque_requirements(clause, text)
    if mixed_torque_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.NUMERIC_RANGE,
            atomic_requirements=mixed_torque_requirements,
        )

    deviation_requirements = _deviation_requirements(clause, text)
    if deviation_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.NUMERIC_RANGE,
            atomic_requirements=deviation_requirements,
        )

    functional_requirements = _functional_requirements(clause, text)
    if functional_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.FUNCTIONAL,
            atomic_requirements=functional_requirements,
        )

    if _is_external_standard_coverage(text):
        return RequirementClassification(requirement_type=RequirementType.EXTERNAL_STANDARD_COVERAGE)

    numeric_requirements = _numeric_text_requirements(clause, text)
    if numeric_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.NUMERIC_LIMIT,
            atomic_requirements=numeric_requirements,
        )

    return RequirementClassification(
        requirement_type=RequirementType.UNKNOWN_NEEDS_REVIEW,
        diagnostics=[{"code": "PTR_REQUIREMENT_TYPE_UNKNOWN", "clause_id": str(clause.number)}],
    )


def _numeric_text_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    requirements.extend(_output_voltage_current_requirements(clause, text))
    if requirements:
        return requirements

    direct_waveform = _direct_waveform_numeric_requirements(clause, text)
    if direct_waveform:
        return direct_waveform

    pulse_timing = _pulse_timing_requirements(clause, text)
    if pulse_timing:
        return pulse_timing

    if "脉冲衰减" in text or "衰减" in text:
        value = _limit_value(text, unit="%") or 10
        requirements.append(
            _text_requirement(
                clause,
                suffix="decay",
                label="脉冲衰减",
                expected_text=f"不超过 {int(value) if value.is_integer() else value}%",
                expected_value=value,
                operator="<=",
                unit="%",
            )
        )

    if "最大输出能量" in text or "输出能量" in text:
        value = _limit_value(text, unit="mJ")
        has_limit_semantics = "最大输出能量" in text or any(
            token in text for token in ("不超过", "不大于", "小于", "低于", "至多")
        )
        if value is None or not has_limit_semantics:
            value = None
    else:
        value = None
    if value is not None:
        requirements.append(
            _text_requirement(
                clause,
                suffix="max_energy",
                label="单个脉冲最大输出能量",
                expected_text=f"小于 {int(value) if value.is_integer() else value}mJ",
                expected_value=value,
                operator="<" if _has_strict_less_than(text) else "<=",
                unit="mJ",
            )
        )

    if not requirements:
        requirements.extend(_generic_numeric_limit_requirements(clause, text))

    return requirements


def _deviation_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    normalized = str(text or "").replace("+/-", "±").replace("＋／－", "±")
    pattern = re.compile(
        r"(?P<descriptor>"
        r"偏差(?:为)?|允许误差(?:为)?|允差(?:为)?|公差(?:为)?|"
        r"(?:测量)?精度(?:应)?(?:不大于|不超过)?(?:为)?"
        r")\s*[:：]?\s*"
        r"(?P<tolerance>±\s*(?P<value>\d+(?:\.\d+)?)\s*"
        r"(?P<unit>%|℃|°C|[A-Za-zμµΩ⁻¹·/]+)?)",
        flags=re.IGNORECASE,
    )
    matches = list(pattern.finditer(normalized))
    if len(matches) != 1:
        return []

    match = matches[0]
    descriptor = match.group("descriptor")
    tolerance_text = re.sub(r"\s+", "", match.group("tolerance")).replace("µ", "μ")
    expected_text = _clause_requirement_text(clause, fallback=text)
    suffix = "accuracy" if "精度" in descriptor else "deviation"
    label = str(clause.title or "").strip() or f"条款 {clause.number}"
    return [
        _text_requirement(
            clause,
            suffix=suffix,
            label=label,
            expected_text=expected_text,
            expected_value=float(match.group("value")),
            operator="deviation_within_tolerance",
            unit=_normalize_numeric_unit(match.group("unit")),
            metadata={
                "match_keywords": [label],
                "result_binding": "clause_window",
                "tolerance_text": tolerance_text,
                "deviation_requirement": True,
            },
        )
    ]


def _generic_numeric_limit_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    expressions = extract_numeric_limit_expressions(text)
    if not expressions:
        return []
    label = _generic_numeric_label(clause)
    requirements: list[PTRAtomicRequirement] = []
    for index, expression in enumerate(expressions, start=1):
        suffix = "numeric_limit" if len(expressions) == 1 else f"numeric_limit:{index}"
        unit = f"{expression.unit}" if expression.unit else ""
        requirements.append(
            _text_requirement(
                clause,
                suffix=suffix,
                label=label,
                expected_text=f"{_display_limit_operator(expression.operator)}{expression.value:g}{unit}",
                expected_value=expression.value,
                operator=expression.operator,
                unit=expression.unit,
                metadata={
                    "match_keywords": [label],
                    "numeric_limit": True,
                    "result_binding": "clause_window",
                },
            )
        )
    return requirements


def _mixed_torque_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    normalized = re.sub(r"\s+", "", str(text or "")).replace("µ", "μ")
    withstand = re.search(
        r"(?:承受|耐受).{0,20}?(?:最小|至少|不小于)\s*(?P<value>\d+(?:\.\d+)?)\s*N[·・.]?cm.{0,30}?(?:不应损坏|无损坏)",
        normalized,
        flags=re.IGNORECASE,
    )
    preset = re.search(
        r"(?:预置|预设|设定)(?:力矩|扭矩).{0,10}?(?P<nominal>\d+(?:\.\d+)?)\s*±\s*(?P<tolerance>\d+(?:\.\d+)?)\s*N[·・.]?cm",
        normalized,
        flags=re.IGNORECASE,
    )
    if withstand is None or preset is None:
        return []

    withstand_value = float(withstand.group("value"))
    nominal = float(preset.group("nominal"))
    tolerance = float(preset.group("tolerance"))
    return [
        _text_requirement(
            clause,
            suffix="torque_withstand",
            label="六角轴承受扭矩",
            expected_text=f"至少{withstand_value:g} N·cm且不损坏",
            expected_value=withstand_value,
            operator="functional",
            unit="N·cm",
            metadata={
                "match_keywords": ["承受", "扭矩", "不损坏"],
                "result_binding": "clause_window",
            },
        ),
        _text_requirement(
            clause,
            suffix="preset_torque",
            label="预置力矩",
            expected_text=f"{nominal:g}±{tolerance:g} N·cm",
            expected_value=nominal,
            operator="deviation_within_tolerance",
            unit="N·cm",
            metadata={
                "match_keywords": ["预置力矩", "预设扭矩", "设定扭矩"],
                "result_binding": "clause_window",
                "tolerance_text": f"±{tolerance:g} N·cm",
            },
        ),
    ]


def extract_numeric_limit_expressions(text: str) -> list[NumericLimitExpression]:
    normalized_text = str(text or "").replace("µ", "μ").replace("／", "/").replace("％", "%")
    standalone_unit = extract_standalone_numeric_unit(normalized_text)
    expressions: list[NumericLimitExpression] = []
    seen: set[tuple[str, float, str]] = set()
    pattern = re.compile(
        r"(?P<operator>不超过|不大于|小于等于|不高于|至多|不小于|不少于|大于等于|至少|"
        r"<=|>=|≤|≥|≦|≧|<|>|＜|＞|小于|低于|少于|大于|高于|多于)"
        r"\s*(?:为|[:：])?\s*"
        r"(?P<value>[+-]?\d+(?:\.\d+)?)\s*"
        r"(?P<unit>[A-Za-zμΩ%℃°]+(?:\s*/\s*[A-Za-zμΩ%℃°\u4e00-\u9fff]+)?)?",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(normalized_text):
        operator = _normalized_limit_operator(match.group("operator"))
        value = float(match.group("value"))
        unit = _normalize_numeric_unit(match.group("unit") or standalone_unit)
        key = (operator, value, (unit or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        expressions.append(
            NumericLimitExpression(
                operator=operator,
                value=value,
                unit=unit,
                raw_text=match.group(0).strip(),
            )
        )
    return expressions


def extract_standalone_numeric_unit(text: str) -> str | None:
    match = re.search(
        r"单位\s*[:：]\s*([A-Za-zμΩ%℃°]+(?:\s*/\s*[A-Za-zμΩ%℃°\u4e00-\u9fff]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    return _normalize_numeric_unit(match.group(1)) if match else None


def _normalize_numeric_unit(unit: str | None) -> str | None:
    value = re.sub(r"\s+", "", str(unit or "")).replace("µ", "μ").replace("／", "/").replace("％", "%")
    return value or None


def _normalized_limit_operator(value: str) -> str:
    compact = _compact(value)
    if compact in {"不超过", "不大于", "小于等于", "不高于", "至多", "<=", "≤", "≦"}:
        return "<="
    if compact in {"不小于", "不少于", "大于等于", "至少", ">=", "≥", "≧"}:
        return ">="
    if compact in {"小于", "低于", "少于", "<", "＜"}:
        return "<"
    return ">"


def _display_limit_operator(operator: str) -> str:
    return {"<=": "≤", ">=": "≥"}.get(operator, operator)


def _generic_numeric_label(clause: PTRClause) -> str:
    title = re.sub(r"\s+", "", str(clause.title or "")).strip("：:。；;")
    if title:
        return title
    body = str(clause.body_text or "")
    marker = re.search(r"不超过|不大于|小于等于|≤|不小于|不少于|大于等于|≥|小于|大于", body)
    prefix = body[: marker.start()] if marker else body
    label = re.sub(r"\s+", "", prefix).strip("：:。；;，,应")
    return label or f"条款 {clause.number} 数值限值"


def _direct_waveform_numeric_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    compact = _compact(text)
    specs: list[tuple[str, str, str, str | None, str | None, float | None]] = []
    if "电压" in compact and "标称值" in compact:
        nominal = _expected_after_label(text, "标称值")
        low_voltage = _expected_after_label(text, "低电压")
        if nominal:
            specs.append(("voltage:nominal", "电压", nominal, "deviation_within_tolerance", "V", None))
        if low_voltage:
            specs.append(("voltage:low_voltage", "低电压", low_voltage, "deviation_within_tolerance", "V", None))
    if "脉宽" in compact:
        expected = _direct_expected_text(text, "脉宽")
        if expected:
            specs.append(("pulse_width", "脉宽", expected, "deviation_within_tolerance", "μs", None))
    if "脉冲间隔" in compact and "脉冲群间隔" not in compact:
        expected = _direct_expected_text(text, "脉冲间隔")
        if expected:
            specs.append(("pulse_interval", "脉冲间隔", expected, "deviation_within_tolerance", "μs", None))
    if "脉冲群间隔" in compact:
        value = _limit_value(text, unit="s")
        if value is not None:
            specs.append(("pulse_group_interval", "脉冲群间隔", _direct_expected_text(text, "脉冲群间隔") or f"≥{value:g}s", ">=", "s", value))
    if "上升沿时间" in compact:
        value = _limit_value(text, unit="ns")
        if value is not None:
            specs.append(("rise_edge_time", "上升沿时间", _direct_expected_text(text, "上升沿时间") or f"≤{value:g}ns", "<=", "ns", value))
    if "下降沿时间" in compact:
        value = _limit_value(text, unit="ns")
        if value is not None:
            specs.append(("fall_edge_time", "下降沿时间", _direct_expected_text(text, "下降沿时间") or f"≤{value:g}ns", "<=", "ns", value))
    if "每个脉冲群中的循环数" in compact:
        expected = _direct_expected_text(text, "每个脉冲群中的循环数")
        if expected:
            specs.append(("pulse_group_cycles", "每个脉冲群中的循环数", expected, "functional_or_equal", None, None))
    if "每个治疗波中的脉冲群数量" in compact:
        expected = _direct_expected_text(text, "每个治疗波中的脉冲群数量")
        if expected:
            specs.append(("treatment_wave_pulse_group_count", "每个治疗波中的脉冲群数量", expected, "functional_or_equal", None, None))

    return [
        _text_requirement(
            clause,
            suffix=suffix,
            label=label,
            expected_text=expected,
            expected_value=expected_value,
            operator=operator,
            unit=unit,
            metadata={"match_keywords": [label], "result_binding": "clause_window"},
        )
        for suffix, label, expected, operator, unit, expected_value in specs
    ]


def _output_voltage_current_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    if "电压" not in text and "电流" not in text:
        return []
    compact = _compact(text)
    if not any(token in compact for token in ("输出", "至少能够提供", "不小于", "大于等于", "≥")):
        return []
    if "标称值" in compact and "±" in compact and not any(token in compact for token in ("输出", "至少能够提供")):
        return []
    requirements: list[PTRAtomicRequirement] = []
    voltage = _value_after_keyword(text, keyword="电压", unit="V")
    current = _value_after_keyword(text, keyword="电流", unit="A")
    if voltage is not None:
        requirements.append(
            _text_requirement(
                clause,
                suffix="voltage",
                label="电压",
                expected_text=f"{int(voltage) if voltage.is_integer() else voltage}V（峰值）",
                expected_value=voltage,
                operator=_limit_operator(text, default=">="),
                unit="V",
            )
        )
    if current is not None:
        requirements.append(
            _text_requirement(
                clause,
                suffix="current",
                label="电流",
                expected_text=f"{int(current) if current.is_integer() else current}A（峰值）",
                expected_value=current,
                operator=_limit_operator(text, default=">="),
                unit="A",
            )
        )
    return requirements


def _pulse_timing_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    if "上升时间" in text:
        return _preset_timing_requirements(
            clause,
            suffix="rise_time",
            label="脉冲上升时间",
            expected_value=_limit_value(text, unit="ns") or 700,
        )
    if "下降时间" in text:
        return _preset_timing_requirements(
            clause,
            suffix="fall_time",
            label="脉冲下降时间",
            expected_value=_limit_value(text, unit="ns") or 700,
        )
    return []


def _preset_timing_requirements(
    clause: PTRClause,
    *,
    suffix: str,
    label: str,
    expected_value: float,
) -> list[PTRAtomicRequirement]:
    value = int(expected_value) if expected_value.is_integer() else expected_value
    return [
        _text_requirement(
            clause,
            suffix=f"{suffix}:pulse3",
            label=label,
            expected_text=f"不超过 {value}ns",
            expected_value=expected_value,
            operator="<=",
            unit="ns",
            preset="PULSE3",
        ),
        _text_requirement(
            clause,
            suffix=f"{suffix}:pf_reversible",
            label=label,
            expected_text=f"不超过 {value}ns",
            expected_value=expected_value,
            operator="<=",
            unit="ns",
            preset="PF Reversible",
        ),
    ]


def _functional_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    programmable_setting = _programmable_setting_requirement(clause, text)
    if programmable_setting is not None:
        return [programmable_setting]

    specs: list[tuple[str, str, tuple[str, ...]]] = [
        ("r_wave_sync", "R 波同步", ("R波同步", "R 波同步")),
        ("impedance_out_of_range_protection", "阻抗超出保护", ("阻抗超出保护", "阻抗超限保护")),
        ("temperature_limit_protection", "温度超限保护", ("温度超限保护",)),
        ("over_current_protection", "过流保护", ("过流保护",)),
    ]
    requirements: list[PTRAtomicRequirement] = []
    compact = _compact(text)
    for suffix, label, keywords in specs:
        if any(_compact(keyword) in compact for keyword in keywords):
            requirements.append(
                _text_requirement(
                    clause,
                    suffix=suffix,
                    label=label,
                    expected_text=f"具有{label}功能" if "保护" in label or "同步" in label else "符合要求",
                    operator="functional",
                    metadata={"match_keywords": list(keywords)},
                )
            )
    generic = _generic_functional_requirement(clause, text)
    if generic is not None and not requirements:
        requirements.append(generic)
    return requirements


def _programmable_setting_requirement(clause: PTRClause, text: str) -> PTRAtomicRequirement | None:
    compact = _compact(text)
    markers = (
        "可调等级",
        "可调范围",
        "调节范围",
        "设置范围",
        "程控范围",
        "测量范围",
    )
    if not any(marker in compact for marker in markers):
        return None
    if any(marker in compact for marker in ("测量精度", "允许误差", "允差", "公差")):
        return None

    label = str(clause.title or "").strip() or f"条款 {clause.number}"
    suffix = "measurement_range" if "测量范围" in compact else "setting_range"
    return _text_requirement(
        clause,
        suffix=suffix,
        label=label,
        expected_text=_clause_requirement_text(clause, fallback=text),
        operator="functional",
        metadata={
            "match_keywords": [label],
            "result_binding": "clause_window",
            "programmable_setting": True,
        },
    )


def _generic_functional_requirement(clause: PTRClause, text: str) -> PTRAtomicRequirement | None:
    compact = _compact(text)
    if not compact or _is_external_standard_coverage(text) or _has_table_reference(clause, text):
        return None
    title = str(clause.title or "").strip()
    if not title:
        return None
    functional_markers = (
        "该功能",
        "应具有",
        "应该",
        "应有",
        "允许",
        "可以",
        "接口",
        "存储",
        "检测",
        "选择",
        "访问",
        "验证",
    )
    if not any(_compact(marker) in compact for marker in functional_markers):
        return None
    return _text_requirement(
        clause,
        suffix="functional",
        label=title,
        expected_text="符合要求",
        operator="functional",
        metadata={"match_keywords": [title], "result_binding": "clause_window"},
    )


def _text_requirement(
    clause: PTRClause,
    *,
    suffix: str,
    label: str,
    expected_text: str | None,
    expected_value: float | None = None,
    operator: str | None = None,
    unit: str | None = None,
    preset: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PTRAtomicRequirement:
    requirement_metadata = dict(metadata or {})
    if preset:
        requirement_metadata["preset"] = preset
    return PTRAtomicRequirement(
        atomic_id=f"{clause.number}:{suffix}",
        clause_id=str(clause.number),
        label=label,
        expected_text=expected_text,
        expected_value=expected_value,
        operator=operator,
        unit=unit,
        source="ptr_text",
        metadata=requirement_metadata,
    )


def clause_local_text(clause: PTRClause, *, include_title: bool = True) -> str:
    body = str(clause.body_text or clause.text_content or clause.full_text or "")
    table_numbers = [re.escape(str(number)) for number in clause.get_all_table_numbers() if str(number)]
    if table_numbers:
        marker = re.search(rf"\n\s*表\s*(?:{'|'.join(table_numbers)})(?:\D|$)", body)
        if marker is not None:
            body = body[: marker.start()].strip()

    title = str(clause.title or "").strip()
    if title:
        numbered_heading = re.compile(
            rf"^\s*{re.escape(str(clause.number))}\s*{re.escape(title)}(?:\s*[:：]?\s*)",
        )
        title_line = re.compile(rf"^\s*{re.escape(title)}\s*(?:\r?\n|[:：])\s*")
        if numbered_heading.match(body):
            body = numbered_heading.sub("", body, count=1)
        elif title_line.match(body):
            body = title_line.sub("", body, count=1)
    body = re.sub(r"\s+", " ", body).strip()
    return "\n".join(value for value in (title if include_title else "", body) if value)


def _clause_requirement_text(clause: PTRClause, *, fallback: str) -> str:
    value = clause_local_text(clause, include_title=False) or str(fallback or "")
    page_marker = re.search(r"\bPage\s+\d+\s+of\s+\d+\b", value, flags=re.IGNORECASE)
    value = re.sub(r"\bPage\s+\d+\s+of\s+\d+\b", " ", value, flags=re.IGNORECASE)
    title = str(clause.title or "").strip()
    if page_marker is not None and title:
        title_index = value.find(title)
        if 0 <= title_index <= 160:
            value = value[title_index:]
    return re.sub(r"\s+", " ", value).strip()


def _table_local_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    tolerance = re.search(
        r"(?:允许误差|允差)\s*[:：]?\s*"
        r"(?P<value>(?:±\s*\d+(?:\.\d+)?|[-−]\s*\d+(?:\.\d+)?\s*/\s*[+＋]?\s*\d+(?:\.\d+)?)"
        r"\s*[A-Za-z0-9μµΩ⁻¹\-−/]*)",
        text,
        flags=re.IGNORECASE,
    )
    if tolerance is None:
        return []
    expected = _clean_expected_text(tolerance.group("value"))
    return [
        _text_requirement(
            clause,
            suffix="table_local_tolerance",
            label=str(clause.title or f"条款 {clause.number}").strip(),
            expected_text=expected,
            operator="deviation_within_tolerance",
            metadata={"match_keywords": [str(clause.title or "").strip()], "result_binding": "clause_window"},
        )
    ]


def _has_table_reference(clause: PTRClause, text: str) -> bool:
    return bool(clause.table_refs or clause.table_references) or bool(re.search(r"表\s*[\d一二三四五六七八九十]+(?:[-－]\d+)?", text))


def _is_software_function_table(clause: PTRClause, text: str) -> bool:
    compact = _compact(text)
    return "软件功能" in compact and _has_table_reference(clause, text)


def _is_external_standard_coverage(text: str) -> bool:
    return bool(re.search(r"\b(?:GB|YY/T|YY|IEC|ISO)\s*\d", text, flags=re.IGNORECASE))


def _value_after_keyword(text: str, *, keyword: str, unit: str) -> float | None:
    pattern = re.compile(rf"{re.escape(keyword)}[^\n。；;，,]{{0,80}}?(\d+(?:\.\d+)?)\s*{re.escape(unit)}", flags=re.IGNORECASE)
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def _expected_after_label(text: str, label: str) -> str | None:
    pattern = re.compile(
        rf"{re.escape(label)}\s*[:：]\s*([^；;，,\n]+(?:±\s*\d+(?:\.\d+)?\s*[A-Za-zΩμµ⁻¹\-−]*)?)"
    )
    match = pattern.search(text)
    return _clean_expected_text(match.group(1)) if match else None


def _direct_expected_text(text: str, label: str) -> str | None:
    pattern = re.compile(rf"{re.escape(label)}\s*[:：]\s*([^；;\n]+)")
    match = pattern.search(text)
    return _clean_expected_text(match.group(1)) if match else None


def _clean_expected_text(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    return text.strip("。；;，,").replace("µ", "μ")


def _limit_value(text: str, *, unit: str) -> float | None:
    pattern = re.compile(rf"(\d+(?:\.\d+)?)\s*{re.escape(unit)}", flags=re.IGNORECASE)
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def _limit_operator(text: str, *, default: str) -> str:
    if any(token in text for token in ("不小于", "至少", "大于等于", "≥")):
        return ">="
    if any(token in text for token in ("不超过", "不大于", "小于等于", "≤")):
        return "<="
    if any(token in text for token in ("小于", "<")):
        return "<"
    if any(token in text for token in ("大于", ">")):
        return ">"
    return default


def _has_strict_less_than(text: str) -> bool:
    return "小于" in text and "不小于" not in text and "小于等于" not in text


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


__all__ = [
    "NumericLimitExpression",
    "RequirementClassification",
    "RequirementType",
    "clause_local_text",
    "classify_requirement",
    "extract_numeric_limit_expressions",
    "extract_standalone_numeric_unit",
]
