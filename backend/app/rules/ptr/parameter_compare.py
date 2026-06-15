from __future__ import annotations

import re

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.table import CanonicalTable, ParameterRecord
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
    actual_records = _index_records(actual_table.parameter_records if actual_table else [])

    for expected_record in expected_table.parameter_records:
        key = _record_key(expected_record)
        actual_record = actual_records.get(key)
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


def _index_records(records: list[ParameterRecord]) -> dict[tuple[str, tuple[tuple[str, str], ...]], ParameterRecord]:
    return {_record_key(record): record for record in records}


def _record_key(record: ParameterRecord) -> tuple[str, tuple[tuple[str, str], ...]]:
    dimensions = tuple(sorted((_norm(key), _norm(value)) for key, value in record.dimensions.items()))
    return (_norm(record.parameter_name or record.raw_name or ""), dimensions)


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
                )
            )
            continue
        _, actual_value = actual_pair
        if _norm_value(expected_value) != _norm_value(actual_value):
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
        },
    )


def _table_evidence(table: CanonicalTable, record: ParameterRecord, source_type: SourceType, label: str) -> Evidence:
    raw_text = "；".join(
        [
            record.parameter_name or "",
            *[f"{key}:{value}" for key, value in record.dimensions.items()],
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


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "-", value or "").strip("-")
    return slug or "value"
