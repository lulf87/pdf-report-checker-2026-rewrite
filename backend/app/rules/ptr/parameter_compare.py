from __future__ import annotations

import re

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.table import CanonicalTable, ParameterRecord
from app.infrastructure.table.numeric_semantics import numeric_expressions_equivalent
from app.infrastructure.text.normalizer import normalize_text


def compare_parameter_tables(
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    *,
    task_id: str = "ptr-table",
    clause_number: str = "",
    table_number: str = "",
) -> list[Finding]:
    findings: list[Finding] = []
    expected_records = list(expected_table.parameter_records)
    actual_records = list(actual_table.parameter_records if actual_table else [])

    for expected_record in expected_records:
        actual_record, ambiguity_finding = _resolve_actual_record(
            expected_table=expected_table,
            actual_table=actual_table,
            expected_record=expected_record,
            expected_records=expected_records,
            actual_records=actual_records,
            task_id=task_id,
            clause_number=clause_number,
            table_number=table_number,
        )
        if ambiguity_finding is not None:
            findings.append(ambiguity_finding)
            continue
        if actual_record is None:
            findings.append(_missing_parameter_finding(expected_table, expected_record, task_id, clause_number, table_number))
            continue
        findings.extend(
            _compare_record_values(
                expected_table=expected_table,
                actual_table=actual_table,
                expected_record=expected_record,
                actual_record=actual_record,
                task_id=task_id,
                clause_number=clause_number,
                table_number=table_number,
            )
        )
    return findings


def _resolve_actual_record(
    *,
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    expected_record: ParameterRecord,
    expected_records: list[ParameterRecord],
    actual_records: list[ParameterRecord],
    task_id: str,
    clause_number: str,
    table_number: str,
) -> tuple[ParameterRecord | None, Finding | None]:
    exact_matches = [record for record in actual_records if _record_segment_key(record) == _record_segment_key(expected_record)]
    if len(exact_matches) == 1:
        return exact_matches[0], None
    if len(exact_matches) > 1:
        return None, _segment_ambiguous_finding(
            expected_table=expected_table,
            actual_table=actual_table,
            expected_record=expected_record,
            actual_records=exact_matches,
            task_id=task_id,
            clause_number=clause_number,
            table_number=table_number,
        )

    base_matches = [record for record in actual_records if _record_base_key(record) == _record_base_key(expected_record)]
    if not base_matches:
        return None, None
    if len(base_matches) == 1:
        if _comparison_conditions(expected_record) and _has_segment_siblings(expected_record, expected_records):
            return None, None
        return base_matches[0], None
    if _comparison_conditions(expected_record):
        return None, None
    return None, _segment_ambiguous_finding(
        expected_table=expected_table,
        actual_table=actual_table,
        expected_record=expected_record,
        actual_records=base_matches,
        task_id=task_id,
        clause_number=clause_number,
        table_number=table_number,
    )


def _has_segment_siblings(expected_record: ParameterRecord, expected_records: list[ParameterRecord]) -> bool:
    base_key = _record_base_key(expected_record)
    segment_keys = {
        _record_segment_key(record)
        for record in expected_records
        if _record_base_key(record) == base_key
    }
    return len(segment_keys) > 1


def _record_base_key(record: ParameterRecord) -> tuple[str, tuple[tuple[str, str], ...]]:
    dimensions = tuple(sorted((_norm(key), _norm(value)) for key, value in record.dimensions.items()))
    return (_norm(record.parameter_name or record.raw_name or ""), dimensions)


def _record_segment_key(record: ParameterRecord) -> tuple[str, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    name, dimensions = _record_base_key(record)
    conditions = tuple(sorted((_norm(key), _norm(value)) for key, value in _comparison_conditions(record).items()))
    return name, dimensions, conditions


def _compare_record_values(
    *,
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    expected_record: ParameterRecord,
    actual_record: ParameterRecord,
    task_id: str,
    clause_number: str,
    table_number: str,
) -> list[Finding]:
    findings: list[Finding] = []
    actual_values = {_norm(key): (key, value) for key, value in actual_record.values.items()}
    for expected_key, expected_value in expected_record.values.items():
        actual_pair = actual_values.get(_norm(expected_key))
        mismatch_code = "PTR_TABLE_TOLERANCE_MISMATCH" if _is_tolerance_key(expected_key) else "PTR_TABLE_VALUE_MISMATCH"
        if actual_pair is None:
            findings.append(
                _value_mismatch_finding(
                    expected_table=expected_table,
                    actual_table=actual_table,
                    expected_record=expected_record,
                    actual_record=actual_record,
                    value_key=expected_key,
                    expected_value=expected_value,
                    actual_value=None,
                    task_id=task_id,
                    clause_number=clause_number,
                    table_number=table_number,
                    code=mismatch_code,
                )
            )
            continue
        _, actual_value = actual_pair
        if not _values_equal(expected_value, actual_value, value_key=expected_key):
            findings.append(
                _value_mismatch_finding(
                    expected_table=expected_table,
                    actual_table=actual_table,
                    expected_record=expected_record,
                    actual_record=actual_record,
                    value_key=expected_key,
                    expected_value=expected_value,
                    actual_value=actual_value,
                    task_id=task_id,
                    clause_number=clause_number,
                    table_number=table_number,
                    code=mismatch_code,
                )
            )
    if expected_record.unit and actual_record.unit and _norm_value(expected_record.unit) != _norm_value(actual_record.unit):
        findings.append(
            _value_mismatch_finding(
                expected_table=expected_table,
                actual_table=actual_table,
                expected_record=expected_record,
                actual_record=actual_record,
                value_key="unit",
                expected_value=expected_record.unit,
                actual_value=actual_record.unit,
                task_id=task_id,
                clause_number=clause_number,
                table_number=table_number,
                code="PTR_TABLE_UNIT_MISMATCH",
            )
        )
    expected_conditions = _comparison_conditions(expected_record)
    actual_conditions = _comparison_conditions(actual_record)
    if _norm_mapping(expected_conditions) != _norm_mapping(actual_conditions):
        findings.append(
            _condition_mismatch_finding(
                expected_table=expected_table,
                actual_table=actual_table,
                expected_record=expected_record,
                actual_record=actual_record,
                expected_conditions=expected_conditions,
                actual_conditions=actual_conditions,
                task_id=task_id,
                clause_number=clause_number,
                table_number=table_number,
            )
        )
    return findings


def _missing_parameter_finding(
    expected_table: CanonicalTable,
    expected_record: ParameterRecord,
    task_id: str,
    clause_number: str,
    table_number: str,
) -> Finding:
    parameter_name = expected_record.parameter_name or ""
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:{_slug(parameter_name)}:missing",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.ERROR,
        code="PTR_TABLE_PARAM_MISSING",
        message=f"报告参数表缺少 PTR 表 {table_number} 的参数：{parameter_name}。",
        location=_first_location(expected_table),
        expected=parameter_name,
        actual=None,
        evidence=[_table_evidence(expected_table, expected_record, SourceType.PTR, "expected")],
        missing_evidence=[MissingEvidence(label=parameter_name, reason="报告参数表未找到同名同维度参数。", expected_source=SourceType.REPORT)],
        metadata={
            "clause_number": clause_number,
            "table_number": table_number,
            "parameter_name": parameter_name,
            "dimensions": expected_record.dimensions,
            "conditions": _comparison_conditions(expected_record),
        },
    )


def _value_mismatch_finding(
    *,
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    expected_record: ParameterRecord,
    actual_record: ParameterRecord,
    value_key: str,
    expected_value: str,
    actual_value: str | None,
    task_id: str,
    clause_number: str,
    table_number: str,
    code: str = "PTR_TABLE_VALUE_MISMATCH",
) -> Finding:
    parameter_name = expected_record.parameter_name or ""
    evidence = [_table_evidence(expected_table, expected_record, SourceType.PTR, "expected")]
    if actual_table is not None:
        evidence.append(_table_evidence(actual_table, actual_record, SourceType.REPORT, "actual"))
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:{_slug(parameter_name)}:{_slug(value_key)}:mismatch",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.ERROR,
        code=code,
        message=f"参数 {parameter_name} 的 {value_key} 与 PTR 表 {table_number} 不一致。",
        location=_first_location(expected_table),
        expected=expected_value,
        actual=actual_value,
        evidence=evidence,
        metadata={
            "clause_number": clause_number,
            "table_number": table_number,
            "parameter_name": parameter_name,
            "value_key": value_key,
            "dimensions": expected_record.dimensions,
            "conditions": _comparison_conditions(expected_record),
        },
    )


def _segment_ambiguous_finding(
    *,
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    expected_record: ParameterRecord,
    actual_records: list[ParameterRecord],
    task_id: str,
    clause_number: str,
    table_number: str,
) -> Finding:
    parameter_name = expected_record.parameter_name or ""
    evidence = [_table_evidence(expected_table, expected_record, SourceType.PTR, "expected")]
    if actual_table is not None:
        evidence.extend(
            _table_evidence(actual_table, actual_record, SourceType.REPORT, f"candidate-{index}")
            for index, actual_record in enumerate(actual_records, start=1)
        )
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:{_slug(parameter_name)}:segment:ambiguous",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.WARN,
        code="PTR_TABLE_SEGMENT_AMBIGUOUS",
        message=f"参数 {parameter_name} 的分段条件无法唯一匹配，已跳过该参数比对。",
        location=_first_location(expected_table),
        expected={
            "parameter_name": parameter_name,
            "dimensions": expected_record.dimensions,
            "conditions": _comparison_conditions(expected_record),
        },
        actual=[
            {
                "parameter_name": record.parameter_name,
                "dimensions": record.dimensions,
                "conditions": _comparison_conditions(record),
            }
            for record in actual_records
        ],
        evidence=evidence,
        metadata={
            "clause_number": clause_number,
            "table_number": table_number,
            "parameter_name": parameter_name,
            "dimensions": expected_record.dimensions,
            "conditions": _comparison_conditions(expected_record),
            "candidate_count": len(actual_records),
        },
    )


def _condition_mismatch_finding(
    *,
    expected_table: CanonicalTable,
    actual_table: CanonicalTable | None,
    expected_record: ParameterRecord,
    actual_record: ParameterRecord,
    expected_conditions: dict[str, str],
    actual_conditions: dict[str, str],
    task_id: str,
    clause_number: str,
    table_number: str,
) -> Finding:
    parameter_name = expected_record.parameter_name or ""
    evidence = [_table_evidence(expected_table, expected_record, SourceType.PTR, "expected")]
    if actual_table is not None:
        evidence.append(_table_evidence(actual_table, actual_record, SourceType.REPORT, "actual"))
    return Finding(
        id=f"{task_id}:PTR_TABLE:{clause_number}:table-{table_number}:{_slug(parameter_name)}:conditions:mismatch",
        task_id=task_id,
        check_id="PTR_TABLE",
        severity=FindingSeverity.ERROR,
        code="PTR_TABLE_CONDITION_MISMATCH",
        message=f"参数 {parameter_name} 的条件与 PTR 表 {table_number} 不一致。",
        location=_first_location(expected_table),
        expected=expected_conditions,
        actual=actual_conditions,
        evidence=evidence,
        metadata={
            "clause_number": clause_number,
            "table_number": table_number,
            "parameter_name": parameter_name,
            "field_name": "conditions",
            "dimensions": expected_record.dimensions,
            "conditions": expected_conditions,
        },
    )


def _table_evidence(table: CanonicalTable, record: ParameterRecord, source_type: SourceType, label: str) -> Evidence:
    raw_text = "；".join(
        [
            record.parameter_name or "",
            *[f"{key}:{value}" for key, value in record.dimensions.items()],
            *[f"{key}:{value}" for key, value in _comparison_conditions(record).items()],
            *([f"单位:{record.unit}"] if record.unit else []),
            *[f"{key}:{value}" for key, value in record.values.items()],
        ]
    )
    return Evidence(
        id=f"{table.table_id}:{label}:{_slug(record.parameter_name or 'parameter')}",
        source_type=source_type,
        location=record.location or _first_location(table),
        raw_text=raw_text,
        normalized_text=normalize_text(raw_text),
        method=EvidenceMethod.PDF_LAYOUT,
    )


def _first_location(table: CanonicalTable) -> Location | None:
    if table.source_locations:
        return table.source_locations[0]
    return None


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", "", normalize_text(value or "")).lower()


def _norm_value(value: str | None) -> str:
    return _norm(value)


def _values_equal(expected_value: str | None, actual_value: str | None, *, value_key: str) -> bool:
    field_kind = "tolerance" if _is_tolerance_key(value_key) else "value"
    if numeric_expressions_equivalent(expected_value, actual_value, field_kind=field_kind):
        return True
    return _norm_value(expected_value) == _norm_value(actual_value)


def _norm_mapping(values: dict[str, str]) -> dict[str, str]:
    return {_norm(key): _norm_value(value) for key, value in values.items() if _norm(key) or _norm_value(value)}


def _comparison_conditions(record: ParameterRecord) -> dict[str, str]:
    dimension_pairs = {_norm(key): _norm_value(value) for key, value in record.dimensions.items()}
    conditions: dict[str, str] = {}
    for key, value in record.conditions.items():
        normalized_key = _norm(key)
        if normalized_key in dimension_pairs and dimension_pairs[normalized_key] == _norm_value(value):
            continue
        if str(value or "").strip():
            conditions[key] = value
    return conditions


def _is_tolerance_key(value_key: str) -> bool:
    normalized = _norm(value_key).replace("_", "")
    tolerance_aliases = {
        "允许误差",
        "容差",
        "误差",
        "允差",
        "允许偏差",
        "偏差",
        "公差",
        "范围上限",
        "范围下限",
        "限值",
        "阈值",
        "标准要求",
        "要求",
        "tolerance",
        "allowederror",
        "alloweddeviation",
        "threshold",
        "limit",
        "range",
    }
    return any(alias in normalized for alias in tolerance_aliases)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value or "").strip("-")
    return slug or "value"
