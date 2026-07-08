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


def classify_requirement(clause: PTRClause, ptr_doc: PTRDocument | None = None) -> RequirementClassification:
    text = _clause_text(clause)
    numeric_requirements = _numeric_text_requirements(clause, text)
    if numeric_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.NUMERIC_LIMIT,
            atomic_requirements=numeric_requirements,
        )

    functional_requirements = _functional_requirements(clause, text)
    if functional_requirements:
        return RequirementClassification(
            requirement_type=RequirementType.FUNCTIONAL,
            atomic_requirements=functional_requirements,
        )

    if _is_software_function_table(clause, text):
        return RequirementClassification(requirement_type=RequirementType.SOFTWARE_FUNCTION_TABLE)

    if _has_table_reference(clause, text):
        return RequirementClassification(requirement_type=RequirementType.TABLE_DRIVEN)

    if _is_external_standard_coverage(text):
        return RequirementClassification(requirement_type=RequirementType.EXTERNAL_STANDARD_COVERAGE)

    return RequirementClassification(
        requirement_type=RequirementType.UNKNOWN_NEEDS_REVIEW,
        diagnostics=[{"code": "PTR_REQUIREMENT_TYPE_UNKNOWN", "clause_id": str(clause.number)}],
    )


def _numeric_text_requirements(clause: PTRClause, text: str) -> list[PTRAtomicRequirement]:
    requirements: list[PTRAtomicRequirement] = []
    requirements.extend(_output_voltage_current_requirements(clause, text))
    if requirements:
        return requirements

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
        value = _limit_value(text, unit="mJ") or 258
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

    return requirements


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
    return requirements


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


def _clause_text(clause: PTRClause) -> str:
    return "\n".join(
        str(value or "")
        for value in (clause.title, clause.body_text, clause.text_content, clause.full_text)
        if str(value or "").strip()
    )


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
    "RequirementClassification",
    "RequirementType",
    "classify_requirement",
]
