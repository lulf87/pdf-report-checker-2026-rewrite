from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.domain.ptr import PTRClause, PTRDocument, PTRTable
from app.domain.ptr_comparison import PTRAtomicRequirement
from app.domain.table import ParameterRecord
from app.rules.ptr.model_context import ReportModelContext, coerce_report_model_context


class TableAxis(BaseModel):
    axis_type: str = "unknown"
    labels: list[str] = Field(default_factory=list)


class PTRTableRegistryEntry(BaseModel):
    parent_clause: str | None = None
    table_number: str
    table_title: str | None = None
    row_labels: list[str] = Field(default_factory=list)
    column_axes: list[TableAxis] = Field(default_factory=list)
    source_page: int | None = None
    table_id: str | None = None


def classify_table_axis(labels: list[str], model_context: ReportModelContext | dict[str, Any] | None = None) -> TableAxis:
    context = coerce_report_model_context(model_context)
    model_values = {_normalize_axis_label(candidate.value) for candidate in context.model_candidates}
    clean_labels = _expand_grouped_model_labels(labels, model_values)
    if clean_labels and model_values and any(_normalize_axis_label(label) in model_values for label in clean_labels):
        return TableAxis(axis_type="model", labels=clean_labels)
    if clean_labels and all(_looks_like_load_label(label) for label in clean_labels):
        return TableAxis(axis_type="load", labels=clean_labels)
    if clean_labels and all(_looks_like_preset_label(label) for label in clean_labels):
        return TableAxis(axis_type="preset", labels=clean_labels)
    if clean_labels and all(_looks_like_condition_label(label) for label in clean_labels):
        return TableAxis(axis_type="condition", labels=clean_labels)
    if clean_labels and len(clean_labels) >= 2 and all(_looks_like_model_label(label) for label in clean_labels):
        return TableAxis(axis_type="model", labels=clean_labels)
    return TableAxis(axis_type="unknown", labels=clean_labels)


def build_ptr_table_registry(
    ptr_doc: PTRDocument,
    model_context: ReportModelContext | dict[str, Any] | None = None,
) -> list[PTRTableRegistryEntry]:
    context = coerce_report_model_context(model_context)
    entries: list[PTRTableRegistryEntry] = []
    for table in ptr_doc.tables:
        if not table.table_number:
            continue
        labels = _table_value_labels(table)
        entry = PTRTableRegistryEntry(
            parent_clause=_parent_clause_for_table(table, ptr_doc),
            table_number=str(table.table_number),
            table_title=_table_title(table),
            row_labels=_table_row_labels(table),
            column_axes=[classify_table_axis(labels, context)] if labels else [],
            source_page=_table_page(table),
            table_id=table.table_id,
        )
        entries.append(entry)
    return entries


def model_aware_table_requirements(
    clause: PTRClause,
    ptr_doc: PTRDocument,
) -> list[PTRAtomicRequirement]:
    context = coerce_report_model_context(ptr_doc.metadata.get("report_model_context"))
    if not context.model_candidates:
        return []
    requirements: list[PTRAtomicRequirement] = []
    for table in _tables_for_clause(clause, ptr_doc):
        axis = classify_table_axis(_table_value_labels(table), context)
        if axis.axis_type != "model":
            continue
        table_requirements = _requirements_from_model_axis_table(clause, table, ptr_doc, context, axis)
        requirements.extend(table_requirements)
    return requirements


def generic_table_requirements(
    clause: PTRClause,
    ptr_doc: PTRDocument,
) -> list[PTRAtomicRequirement]:
    context = coerce_report_model_context(ptr_doc.metadata.get("report_model_context"))
    requirements: list[PTRAtomicRequirement] = []
    for table in _tables_for_clause(clause, ptr_doc):
        if classify_table_axis(_table_value_labels(table), context).axis_type == "model":
            continue
        raw_rows = _normalized_raw_rows(table)
        if len(raw_rows) < 2:
            continue
        requirements.extend(_requirements_from_generic_rows(clause, table, ptr_doc, raw_rows))
    return requirements


def _requirements_from_generic_rows(
    clause: PTRClause,
    table: PTRTable,
    ptr_doc: PTRDocument,
    rows: list[list[str]],
) -> list[PTRAtomicRequirement]:
    header = rows[0]
    if len(header) < 2:
        return []
    table_number = str(table.table_number or "")
    table_title = _table_title(table)
    table_key = _table_key(table, ptr_doc)
    parent_clause = _parent_clause_for_table(table, ptr_doc) or _ancestor_clause_number(str(clause.number))
    requirements: list[PTRAtomicRequirement] = []

    for row_index, row in enumerate(rows[1:], start=1):
        if _looks_like_continuation_header(row):
            header = row
            continue
        value_column = _single_value_column(header, clause)
        padded = [*row, *([""] * max(0, len(header) - len(row)))]
        if value_column is not None:
            expected = padded[value_column].strip()
            dimensions = [padded[index].strip() for index in range(value_column) if padded[index].strip()]
            if not expected or _not_applicable_cell(expected):
                continue
            label = " / ".join(dimensions) or str(clause.title or table_title or "参数")
            requirements.append(
                _generic_table_requirement(
                    clause=clause,
                    table_number=table_number,
                    table_title=table_title,
                    table_key=table_key,
                    parent_clause=parent_clause,
                    label=label,
                    condition=label,
                    row_label=dimensions[0] if dimensions else label,
                    expected=expected,
                    suffix=f"row{row_index}",
                )
            )
            continue

        row_label = padded[0].strip()
        if not row_label:
            continue
        for column_index in range(1, len(header)):
            expected = padded[column_index].strip()
            if not expected or _not_applicable_cell(expected):
                continue
            condition = header[column_index].strip() or f"条件{column_index}"
            requirements.append(
                _generic_table_requirement(
                    clause=clause,
                    table_number=table_number,
                    table_title=table_title,
                    table_key=table_key,
                    parent_clause=parent_clause,
                    label=row_label,
                    condition=condition,
                    row_label=row_label,
                    expected=expected,
                    suffix=f"row{row_index}:column{column_index}",
                )
            )
    return requirements


def _generic_table_requirement(
    *,
    clause: PTRClause,
    table_number: str,
    table_title: str,
    table_key: str,
    parent_clause: str | None,
    label: str,
    condition: str,
    row_label: str,
    expected: str,
    suffix: str,
) -> PTRAtomicRequirement:
    operator = "deviation_within_tolerance" if _contains_tolerance(expected) else _operator_for_projected_value(expected, row_label=row_label)
    return PTRAtomicRequirement(
        atomic_id=f"{clause.number}:table{table_number}:{suffix}:{_slug(label)}:{_slug(condition)}",
        clause_id=str(clause.number),
        label=label,
        condition=condition,
        expected_text=expected,
        operator=operator,
        source="ptr_table",
        table_number=table_number,
        table_title=table_title,
        table_key=table_key,
        metadata={
            "axis_type": "condition",
            "condition": condition,
            "table_row_label": row_label,
            "parent_clause": parent_clause,
            "match_keywords": _unique([row_label, condition, clause.title or ""]),
        },
    )


def _normalized_raw_rows(table: PTRTable) -> list[list[str]]:
    raw_rows = table.metadata.get("raw_rows")
    if not isinstance(raw_rows, list):
        return []
    rows: list[list[str]] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, list):
            continue
        row = [_clean_label(value) for value in raw_row]
        if any(row):
            rows.append(row)
    return rows


def _single_value_column(header: list[str], clause: PTRClause) -> int | None:
    clause_key = _compact(clause.title or "")
    for index in range(1, len(header)):
        header_key = _compact(header[index])
        if clause_key and header_key and (clause_key in header_key or header_key in clause_key):
            return index
    if (
        len(header) >= 3
        and _compact(header[1]) in {"事件", "参数", "项目"}
        and _compact(header[-1]) in {"心房", "心室", "正常状态", "单一故障状态"}
    ):
        return len(header) - 1
    return None


def _looks_like_continuation_header(row: list[str]) -> bool:
    compact = [_compact(value) for value in row]
    if len(compact) < 2:
        return False
    return compact[0] in {"模式", "事件", "参数", "项目"} and any(
        value in {"事件", "参数", "项目", "心房", "心室", "正常状态", "单一故障状态"}
        for value in compact[1:]
    )


def _contains_tolerance(value: str) -> bool:
    return "±" in str(value) or bool(re.search(r"-\s*\d+(?:\.\d+)?\s*/\s*\+?\d", str(value)))


def _not_applicable_cell(value: str) -> bool:
    return re.fullmatch(r"[-—–－/]+", re.sub(r"\s+", "", str(value or ""))) is not None


def _tolerance_text(value: str) -> str | None:
    text = str(value or "").replace("+/-", "±")
    match = re.search(r"±\s*\d+(?:\.\d+)?", text)
    if match is not None:
        return re.sub(r"\s+", "", match.group(0))
    match = re.search(r"-\s*\d+(?:\.\d+)?\s*/\s*\+?\s*\d+(?:\.\d+)?", text)
    return re.sub(r"\s+", "", match.group(0)) if match is not None else None


def _requirements_from_model_axis_table(
    clause: PTRClause,
    table: PTRTable,
    ptr_doc: PTRDocument,
    context: ReportModelContext,
    axis: TableAxis,
) -> list[PTRAtomicRequirement]:
    canonical = table.canonical_table
    if canonical is None:
        return []
    records = _records_for_clause(clause, list(canonical.parameter_records))
    if not records:
        return []
    primary_model = context.primary_model
    table_number = str(table.table_number or "")
    table_title = _table_title(table)
    table_key = _table_key(table, ptr_doc)
    parent_clause = _parent_clause_for_table(table, ptr_doc)
    requirements: list[PTRAtomicRequirement] = []
    for record in records:
        row_label = record.parameter_name or record.raw_name or record.parameter_id or "参数"
        for model_label in axis.labels:
            expected = _record_value_for_model(record, model_label)
            if expected is None:
                continue
            is_selected = primary_model is not None and _same_axis_label(model_label, primary_model)
            model_unknown = primary_model is None
            metadata = {
                "axis_type": "model",
                "model_column": model_label,
                "primary_model": primary_model,
                "table_row_label": row_label,
                "parent_clause": parent_clause or _ancestor_clause_number(str(clause.number)),
                "match_keywords": _match_keywords(clause, row_label),
            }
            tolerance_text = _tolerance_text(row_label)
            if tolerance_text:
                metadata["tolerance_text"] = tolerance_text
            if not is_selected and not model_unknown:
                metadata["not_applicable_by_model"] = True
            if model_unknown:
                metadata["model_projection_status"] = "model_unknown"
            requirements.append(
                PTRAtomicRequirement(
                    atomic_id=f"{clause.number}:table{table_number}:{_slug(row_label)}:{_slug(model_label)}",
                    clause_id=str(clause.number),
                    label=row_label,
                    expected_text=str(expected or ""),
                    operator=(
                        "deviation_within_tolerance"
                        if tolerance_text
                        else _operator_for_projected_value(str(expected or ""), row_label=row_label)
                    ),
                    source="ptr_table",
                    table_number=table_number,
                    table_title=table_title,
                    table_key=table_key,
                    metadata=metadata,
                )
            )
    return requirements


def _tables_for_clause(clause: PTRClause, ptr_doc: PTRDocument) -> list[PTRTable]:
    table_numbers = [reference.table_number for reference in clause.table_references] + list(clause.table_refs)
    if not table_numbers:
        return []
    ancestor_ids = {clause.clause_id, *(_ancestor_clause_ids(clause, ptr_doc))}
    tables: list[PTRTable] = []
    for table_number in table_numbers:
        candidates = ptr_doc.get_tables_by_number(table_number)
        anchored = [
            table
            for table in candidates
            if not table.referenced_by_clause_ids
            or any(clause_id in table.referenced_by_clause_ids for clause_id in ancestor_ids)
        ]
        tables.extend(anchored or candidates)
    return _unique_tables(tables)


def _records_for_clause(clause: PTRClause, records: list[ParameterRecord]) -> list[ParameterRecord]:
    title = str(clause.title or "").strip()
    body = _clause_body_without_attached_table(clause)
    matched = [record for record in records if _record_matches_clause(record, title, body)]
    if matched:
        return matched
    if "产品物理特性" in _compact(title + body):
        return records
    return []


def _clause_body_without_attached_table(clause: PTRClause) -> str:
    body = str(clause.body_text or clause.full_text or "")
    if clause.metadata.get("referenced_table_text_attached") is not True:
        return body
    table_numbers = [re.escape(str(number)) for number in clause.get_all_table_numbers() if str(number)]
    if not table_numbers:
        return body
    match = re.search(rf"\n\s*表\s*(?:{'|'.join(table_numbers)})(?:\D|$)", body)
    return body[: match.start()].strip() if match else body


def _record_matches_clause(record: ParameterRecord, title: str, body: str) -> bool:
    row_label = str(record.parameter_name or record.raw_name or record.parameter_id or "")
    compact_row = _compact(row_label)
    compact_clause = _semantic_label(" ".join([title, body]))
    if not compact_row or not compact_clause:
        return False
    semantic_row = _semantic_label(row_label)
    semantic_title = _semantic_label(title)
    return semantic_row in compact_clause or semantic_title in semantic_row or semantic_row in semantic_title


def _semantic_label(value: str) -> str:
    text = re.sub(r"[（(][^）)]*(?:只适用|适用于)[^）)]*[）)]", "", str(value or ""))
    text = re.sub(r"(?:心脏)?起搏器的", "", text)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def _table_value_labels(table: PTRTable) -> list[str]:
    canonical = table.canonical_table
    labels: list[str] = []
    if canonical is not None:
        labels.extend(canonical.value_columns)
        for record in canonical.parameter_records:
            labels.extend(record.values.keys())
    return _unique(_clean_label(label) for label in labels)


def _expand_grouped_model_labels(labels: list[str], model_values: set[str]) -> list[str]:
    expanded: list[str] = []
    for label in labels:
        clean = _clean_label(label)
        parts = [part.strip() for part in re.split(r"[、，,；;]+", clean) if part.strip()]
        if len(parts) > 1 and all(
            _looks_like_model_label(part) or _normalize_axis_label(part) in model_values
            for part in parts
        ):
            expanded.extend(parts)
        elif clean:
            expanded.append(clean)
    return _unique(expanded)


def _record_value_for_model(record: ParameterRecord, model_label: str) -> str | None:
    for column_label, value in record.values.items():
        if _same_axis_label(column_label, model_label):
            return value
        grouped = [part.strip() for part in re.split(r"[、，,；;]+", column_label) if part.strip()]
        if any(_same_axis_label(part, model_label) for part in grouped):
            return value
    return None


def _table_row_labels(table: PTRTable) -> list[str]:
    canonical = table.canonical_table
    if canonical is None:
        return []
    return _unique(
        str(record.parameter_name or record.raw_name or record.parameter_id or "").strip()
        for record in canonical.parameter_records
    )


def _parent_clause_for_table(table: PTRTable, ptr_doc: PTRDocument) -> str | None:
    parent_clause = str(table.metadata.get("parent_clause") or "").strip()
    if parent_clause:
        return parent_clause
    for clause_id in table.referenced_by_clause_ids:
        clause = next((item for item in ptr_doc.clauses if item.clause_id == clause_id), None)
        if clause is not None:
            section_parts = str(clause.number).split(".")[:2]
            section = ptr_doc.get_clause_by_string(".".join(section_parts)) if len(section_parts) == 2 else None
            if section is not None and section.children_ids:
                return str(section.number)
            return str(clause.number)
        match = re.search(r"ptr-(\d+(?:\.\d+)*)", clause_id)
        if match:
            return match.group(1)
    return None


def _ancestor_clause_ids(clause: PTRClause, ptr_doc: PTRDocument) -> list[str]:
    ids: list[str] = []
    parent_number = clause.number.parent()
    while parent_number is not None:
        parent = ptr_doc.get_clause_by_number(parent_number)
        if parent is not None:
            ids.append(parent.clause_id)
        parent_number = parent_number.parent()
    return ids


def _ancestor_clause_number(clause_number: str) -> str | None:
    parts = str(clause_number or "").split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def _operator_for_projected_value(value: str, *, row_label: str = "") -> str | None:
    compact = _compact(value)
    if not compact:
        return None
    if "模式" in _compact(row_label):
        return "functional_or_equal"
    if "符合" in compact or "具备" in compact:
        return "functional_or_equal"
    if re.fullmatch(r"[A-Z]{2,5}R?", compact, flags=re.IGNORECASE):
        return "functional_or_equal"
    if not re.search(r"\d", compact) and re.search(r"[\u4e00-\u9fffA-Za-z]", compact):
        return "functional_or_equal"
    return None


def _match_keywords(clause: PTRClause, row_label: str) -> list[str]:
    values = [row_label, clause.title or ""]
    return _unique(value for value in values if str(value or "").strip())


def _table_key(table: PTRTable, ptr_doc: PTRDocument) -> str:
    parent = _parent_clause_for_table(table, ptr_doc) or ""
    number = str(table.table_number or "")
    title = _table_title(table)
    return f"{parent}:表{number}:{title}".strip(":")


def _table_title(table: PTRTable) -> str:
    raw = table.caption or table.title or ""
    number = str(table.table_number or "")
    text = re.sub(r"\s+", "", raw)
    text = re.sub(rf"^表{re.escape(number)}", "", text)
    return text or raw or f"表{number}"


def _table_page(table: PTRTable) -> int | None:
    if table.canonical_table is not None and table.canonical_table.page_start:
        return table.canonical_table.page_start
    return table.page


def _looks_like_model_label(label: str) -> bool:
    text = _normalize_axis_label(label)
    if not text or _looks_like_load_label(label) or _looks_like_preset_label(label):
        return False
    if re.fullmatch(r"\d{3,6}[A-Z]?", text):
        return True
    if re.fullmatch(r"[A-Z]+[-_]?[A-Z0-9]+(?:[-_][A-Z0-9]+)*", text) and any(char.isdigit() for char in text):
        return True
    return False


def _looks_like_preset_label(label: str) -> bool:
    text = _normalize_axis_label(label)
    preset_tokens = {
        "PULSE3",
        "PFREVERSIBLE",
        "VVI",
        "VVIR",
        "DDD",
        "DDDR",
        "AAI",
        "AAIR",
        "ODO",
    }
    return text in preset_tokens or "预设" in str(label)


def _looks_like_load_label(label: str) -> bool:
    return "Ω" in str(label) or "OHM" in _normalize_axis_label(label)


def _looks_like_condition_label(label: str) -> bool:
    text = _compact(label)
    return any(token in text for token in ("正常", "单一故障", "条件", "状态", "模式"))


def _same_axis_label(left: str, right: str) -> bool:
    return _normalize_axis_label(left) == _normalize_axis_label(right)


def _normalize_axis_label(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper().replace("－", "-").replace("—", "-")


def _clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _slug(value: str) -> str:
    text = re.sub(r"\s+", "-", str(value or "").strip())
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "-", text).strip("-") or "item"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _unique_tables(tables: list[PTRTable]) -> list[PTRTable]:
    result: list[PTRTable] = []
    seen: set[str] = set()
    for table in tables:
        key = table.table_id or f"{table.table_number}:{table.page}"
        if key in seen:
            continue
        seen.add(key)
        result.append(table)
    return result


__all__ = [
    "PTRTableRegistryEntry",
    "TableAxis",
    "build_ptr_table_registry",
    "classify_table_axis",
    "generic_table_requirements",
    "model_aware_table_requirements",
]
