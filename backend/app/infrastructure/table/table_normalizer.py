from __future__ import annotations

import re
from typing import Any

from app.domain.common import Location
from app.domain.pdf import PdfTable
from app.domain.table import (
    CanonicalTable,
    ParameterRecord,
    TableColumn,
    TableHeader,
    TableRow,
)
from app.infrastructure.table.table_semantics import TableSemantics


class TableNormalizer:
    MAX_HEADER_SCAN_ROWS = 4

    def __init__(self) -> None:
        self.semantics = TableSemantics()

    def normalize(self, table: PdfTable, *, continuation_of: str | None = None) -> CanonicalTable:
        self.semantics.reset()
        rows = [list(row) for row in table.rows]
        n_cols = max((len(row) for row in rows), default=0)
        rows = [row + [""] * (n_cols - len(row)) for row in rows]

        diagnostics: list[str] = []
        if not rows or n_cols == 0:
            return CanonicalTable(
                table_id=table.table_id,
                source_table_id=table.table_id,
                caption=table.caption,
                diagnostics=["empty_table"],
                confidence="low",
                metadata=self._metadata(table, continuation_of),
            )

        header_indices = self._detect_header_rows(rows)
        header_rows = [rows[index] for index in header_indices]
        column_paths = self._column_paths(header_rows, n_cols)
        roles = self.semantics.infer_column_roles(column_paths)
        columns = [
            TableColumn(name=" / ".join(path) if path else f"列{idx + 1}", normalized_name="".join(path), column_index=idx)
            for idx, path in enumerate(column_paths)
        ]
        body_indices = [index for index in range(len(rows)) if index not in header_indices]
        body_rows = [list(rows[index]) for index in body_indices]

        filled_body_rows = self._fill_down_dimensions(body_rows, roles, diagnostics)
        row_models = [
            TableRow(row_id=f"{table.table_id}:row:{body_indices[row_offset]}", values={
                columns[col].name: value for col, value in enumerate(row) if col < len(columns)
            })
            for row_offset, row in enumerate(filled_body_rows)
        ]

        canonical = CanonicalTable(
            table_id=f"canonical:{table.table_id}",
            source_table_id=table.table_id,
            caption=table.caption,
            columns=columns,
            rows=row_models,
            headers=[TableHeader(rows=header_rows, column_paths=column_paths)] if header_rows else [],
            header_rows=header_rows,
            dimension_columns=[columns[index].name for index, role in enumerate(roles) if role in {"parameter", "model", "group"}],
            parameter_name_column=self._first_column_name(columns, roles, {"parameter"}),
            unit_column=self._first_column_name(columns, roles, {"unit"}),
            value_columns=[columns[index].name for index, role in enumerate(roles) if role in {"value", "default", "tolerance", "remark"}],
            condition_columns=[columns[index].name for index, role in enumerate(roles) if role in {"model", "group"}],
            source_locations=[Location(page_number=page) for page in table.page_numbers],
            confidence="high" if header_rows and not self.semantics.unknown_role_count else "medium",
            normalization_profile="pymupdf-table-v1",
            diagnostics=diagnostics,
            metadata=self._metadata(table, continuation_of),
        )
        canonical.parameter_records = self._build_parameter_records(canonical, filled_body_rows, columns, roles)
        if continuation_of:
            canonical.diagnostics.append(f"continuation of {continuation_of}")
        return canonical

    def to_legacy_headers(self, canonical: CanonicalTable) -> list[str]:
        if canonical.headers and canonical.headers[0].column_paths:
            return [" / ".join(path) if path else f"列{idx + 1}" for idx, path in enumerate(canonical.headers[0].column_paths)]
        return [column.name for column in canonical.columns]

    def to_legacy_rows(self, canonical: CanonicalTable) -> list[list[str]]:
        headers = self.to_legacy_headers(canonical)
        return [
            [str(row.values.get(header, "") or "") for header in headers]
            for row in canonical.rows
        ]

    def _detect_header_rows(self, rows: list[list[str]]) -> list[int]:
        header_rows: list[int] = []
        for index, row in enumerate(rows[: self.MAX_HEADER_SCAN_ROWS]):
            if self._is_header_like_row(row, index):
                header_rows.append(index)
            elif header_rows:
                break
        return header_rows

    def _is_header_like_row(self, row: list[str], index: int) -> bool:
        compact = [re.sub(r"\s+", "", cell or "") for cell in row]
        non_empty = [cell for cell in compact if cell]
        if not non_empty:
            return False
        merged = "".join(non_empty)
        if any(token in merged for token in ["参数", "常规数值", "标准设置", "允许误差", "检验结果", "单项结论", "备注", "单位"]):
            return True
        numeric_ratio = sum(1 for value in non_empty if self._is_numeric_like(value)) / len(non_empty)
        if index == 0 and numeric_ratio <= 0.35 and len(non_empty) >= 2:
            return True
        if index in {1, 2} and numeric_ratio <= 0.2 and any(not cell for cell in compact):
            return True
        return False

    def _column_paths(self, header_rows: list[list[str]], n_cols: int) -> list[list[str]]:
        if not header_rows:
            return [[f"列{index + 1}"] for index in range(n_cols)]

        materialized: list[list[str]] = []
        for row in header_rows:
            row_labels: list[str] = []
            last = ""
            for index in range(n_cols):
                value = row[index].strip() if index < len(row) else ""
                if value:
                    last = value
                    row_labels.append(value)
                else:
                    row_labels.append(last)
            materialized.append(row_labels)

        paths: list[list[str]] = []
        for col in range(n_cols):
            labels: list[str] = []
            for row in materialized:
                label = row[col].strip()
                if label and (not labels or labels[-1] != label):
                    labels.append(label)
            paths.append(labels)
        return paths

    def _fill_down_dimensions(
        self,
        body_rows: list[list[str]],
        roles: list[str],
        diagnostics: list[str],
    ) -> list[list[str]]:
        dimension_cols = [index for index, role in enumerate(roles) if role in {"parameter", "model", "group"}]
        value_cols = [index for index, role in enumerate(roles) if role in {"value", "default", "tolerance", "remark"}]
        if not dimension_cols and roles:
            dimension_cols = [0]
        if not value_cols:
            value_cols = [index for index in range(len(roles)) if index not in dimension_cols]

        last_seen: dict[int, tuple[int, str]] = {}
        output = [list(row) for row in body_rows]
        for row_index, row in enumerate(output):
            row_has_value = any(index < len(row) and row[index].strip() for index in value_cols)
            for col in dimension_cols:
                if col >= len(row):
                    continue
                if row[col].strip():
                    last_seen[col] = (row_index, row[col])
                elif row_has_value and col in last_seen:
                    row[col] = last_seen[col][1]
                    diagnostics.append(f"fill_down r{row_index}c{col} from r{last_seen[col][0]}c{col}")
        return output

    def _build_parameter_records(
        self,
        canonical: CanonicalTable,
        rows: list[list[str]],
        columns: list[TableColumn],
        roles: list[str],
    ) -> list[ParameterRecord]:
        if not rows or not columns:
            return []
        parameter_col = self._first_role_index(roles, {"parameter"}, default=0)
        unit_col = self._first_role_index(roles, {"unit"}, default=None)
        condition_cols = [index for index, role in enumerate(roles) if role in {"model", "group"}]
        value_cols = [index for index, role in enumerate(roles) if role in {"value", "default", "tolerance", "remark"}]
        records: list[ParameterRecord] = []
        paths = canonical.headers[0].column_paths if canonical.headers else [[column.name] for column in columns]

        for row_index, row in enumerate(rows):
            if parameter_col >= len(row) or not row[parameter_col].strip():
                continue
            dimensions: dict[str, str] = {}
            for col in condition_cols:
                if col < len(row) and row[col].strip():
                    dimensions[columns[col].name] = row[col].strip()
            values: dict[str, str] = {}
            for col in value_cols:
                if col >= len(row) or not row[col].strip():
                    continue
                role = roles[col] if col < len(roles) else None
                label = self.semantics.infer_value_leaf_label(columns[col].name, role=role)
                dims, leaf, _ = self.semantics.split_path_semantics(paths[col] if col < len(paths) else columns[col].name)
                if dims and not any(dimensions.values()):
                    for axis, dim in enumerate(dims, start=1):
                        dimensions.setdefault(f"axis_{axis}", dim)
                values[leaf or label or columns[col].name] = row[col].strip()
            records.append(
                ParameterRecord(
                    parameter_name=row[parameter_col].strip(),
                    unit=row[unit_col].strip() if unit_col is not None and unit_col < len(row) and row[unit_col].strip() else None,
                    dimensions=dimensions,
                    conditions=dict(dimensions),
                    values=values,
                    source_rows=[row_index],
                )
            )
        return records

    def _first_role_index(self, roles: list[str], targets: set[str], default: int | None = 0) -> int | None:
        for index, role in enumerate(roles):
            if role in targets:
                return index
        return default

    def _first_column_name(self, columns: list[TableColumn], roles: list[str], targets: set[str]) -> str | None:
        index = self._first_role_index(roles, targets, default=None)
        return columns[index].name if index is not None and index < len(columns) else None

    def _metadata(self, table: PdfTable, continuation_of: str | None) -> dict[str, Any]:
        metadata = dict(table.metadata)
        if continuation_of:
            metadata["continuation_of"] = continuation_of
        elif table.metadata.get("continuation_of"):
            metadata["continuation_of"] = table.metadata["continuation_of"]
        return metadata

    def _is_numeric_like(self, value: str) -> bool:
        return bool(re.fullmatch(r"[-+]?[\d.]+(?:%|ms|mV|V|A|Ω|KΩ|ppm|μs|us)?", value, re.IGNORECASE))
