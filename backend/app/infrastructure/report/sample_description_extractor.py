from __future__ import annotations

import re

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfTable
from app.domain.report import ComponentKey, ReportField, SampleComponent, SampleDescriptionRow


FIELD_COLUMNS = {
    "sequence_raw": ("序号", "编号", "item_no"),
    "component_name": ("部件名称", "样品名称", "产品名称", "名称"),
    "model": ("规格型号", "型号规格", "型号/规格", "型号", "规格", "组件号"),
    "batch_or_serial": ("序列号批号", "批号/序列号", "序列号/批号", "产品编号/批号", "批号或序列号", "批号", "序列号", "SN", "LOT"),
    "production_date": ("生产日期", "制造日期", "MFG", "MFD"),
    "expiration_date": ("失效日期", "有效期至", "有效期", "EXP"),
    "remark": ("备注", "说明"),
}

DISPLAY_NAMES = {
    "sequence_raw": "序号",
    "component_name": "部件名称",
    "model": "规格型号",
    "batch_or_serial": "序列号批号",
    "production_date": "生产日期",
    "expiration_date": "失效日期",
    "remark": "备注",
}


class SampleDescriptionExtractor:
    """Extract sample-description table facts for C04-C06 inputs."""

    def extract_rows(self, parsed_pdf: ParsedPdf) -> list[SampleDescriptionRow]:
        rows: list[SampleDescriptionRow] = []
        row_counter = 0
        for page in parsed_pdf.pages:
            for table in page.tables:
                header_map, header_row_index = self._header_map(table)
                if not self._is_sample_description_table(header_map):
                    continue
                page_number = page.page_number or (table.page_numbers[0] if table.page_numbers else None)
                if page_number is None:
                    continue
                sample_role = self._sample_role(table=table, page_text=page.text)
                for row_index, values in self._data_rows(table, header_row_index):
                    if not any((value or "").strip() for value in values):
                        continue
                    row_counter += 1
                    row = self._row_from_values(
                        parsed_pdf=parsed_pdf,
                        table=table,
                        page_number=page_number,
                        row_index=row_index,
                        row_counter=row_counter,
                        values=values,
                        header_map=header_map,
                        sample_role=sample_role,
                    )
                    if row is not None:
                        rows.append(row)
        return rows

    def extract_components(self, parsed_pdf: ParsedPdf) -> list[SampleComponent]:
        components: list[SampleComponent] = []
        for row in self.extract_rows(parsed_pdf):
            component = SampleComponent(
                component_id=row.row_id,
                component_name=_field_value(row.component_name),
                model=_field_value(row.model),
                batch_or_serial=_field_value(row.batch_or_serial),
                production_date=_field_value(row.production_date),
                expiration_date=_field_value(row.expiration_date),
                remark=_field_value(row.remark),
                row_location=row.row_location,
                evidence=row.evidence,
                metadata={
                    **row.metadata,
                    "unused_note": _field_value(row.remark) if "本次检测未使用" in (_field_value(row.remark) or "") else "",
                    "sample_role": row.metadata.get("sample_role", "main_sample"),
                    "supporting_equipment": row.metadata.get("sample_role") == "supporting_equipment",
                    **({"source_context": row.metadata["source_context"]} if "source_context" in row.metadata else {}),
                },
            )
            components.append(component)
        return components

    def _row_from_values(
        self,
        *,
        parsed_pdf: ParsedPdf,
        table: PdfTable,
        page_number: int,
        row_index: int,
        row_counter: int,
        values: list[str],
        header_map: dict[str, int],
        sample_role: dict[str, str | bool],
    ) -> SampleDescriptionRow | None:
        get_value = lambda field_name: self._cell_value(values, header_map.get(field_name))
        row_id = f"sample-row-{row_counter}"
        row_location = Location(
            source_id=parsed_pdf.file_id,
            source_type=SourceType.REPORT,
            page_number=page_number,
            table_id=table.table_id,
            row_index=row_index,
        )

        fields = {
            field_name: self._report_field(
                parsed_pdf=parsed_pdf,
                table=table,
                page_number=page_number,
                row_index=row_index,
                column_index=header_map.get(field_name),
                field_name=field_name,
                display_name=display_name,
                raw_value=get_value(field_name),
            )
            for field_name, display_name in DISPLAY_NAMES.items()
            if field_name != "sequence_raw" and field_name in header_map
        }

        if not any((field.value or "").strip() for field in fields.values()):
            return None

        evidence = [evidence for field in fields.values() for evidence in field.evidence]
        component_key = ComponentKey(
            name=_field_value(fields.get("component_name")),
            model=_field_value(fields.get("model")),
            batch_or_serial=_field_value(fields.get("batch_or_serial")),
        )

        return SampleDescriptionRow(
            row_id=row_id,
            sequence_raw=get_value("sequence_raw"),
            sequence=_parse_int(get_value("sequence_raw")),
            component_key=component_key,
            component_name=fields.get("component_name"),
            model=fields.get("model"),
            batch_or_serial=fields.get("batch_or_serial"),
            production_date=fields.get("production_date"),
            expiration_date=fields.get("expiration_date"),
            remark=fields.get("remark"),
            row_location=row_location,
            evidence=evidence,
            metadata={
                "source_table_id": table.table_id,
                "field_columns": dict(header_map),
                **sample_role,
            },
        )

    def _report_field(
        self,
        *,
        parsed_pdf: ParsedPdf,
        table: PdfTable,
        page_number: int,
        row_index: int,
        column_index: int | None,
        field_name: str,
        display_name: str,
        raw_value: str,
    ) -> ReportField:
        value = (raw_value or "").strip()
        location = Location(
            source_id=parsed_pdf.file_id,
            source_type=SourceType.REPORT,
            page_number=page_number,
            table_id=table.table_id,
            row_index=row_index,
            column_name=display_name,
        )
        evidence = Evidence(
            id=f"{parsed_pdf.file_id}:{table.table_id}:sample:r{row_index}:c{column_index}:{field_name}",
            source_type=SourceType.REPORT,
            location=location,
            raw_text=raw_value,
            normalized_text=_compact(value),
            value=value,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata={"field_name": field_name, "column_index": column_index},
        )
        return ReportField(
            name=display_name,
            raw_value=raw_value,
            value=value,
            normalized_value=_compact(value),
            location=location,
            evidence=[evidence],
            confidence=Confidence.HIGH,
            aliases=[alias for alias in FIELD_COLUMNS[field_name] if alias != display_name],
            metadata={"field_name": field_name},
        )

    def _header_map(self, table: PdfTable) -> tuple[dict[str, int], int | None]:
        candidates: list[tuple[list[str], int | None]] = []
        if table.columns:
            candidates.append((table.columns, None))
        if table.rows:
            candidates.append((table.rows[0], 0))

        best_map: dict[str, int] = {}
        best_header_row: int | None = None
        for headers, header_row_index in candidates:
            current = self._map_headers(headers)
            if len(current) > len(best_map) or (
                header_row_index is not None and len(current) == len(best_map)
            ):
                best_map = current
                best_header_row = header_row_index
        return best_map, best_header_row

    def _map_headers(self, headers: list[str]) -> dict[str, int]:
        result: dict[str, int] = {}
        compact_headers = [_compact(header).upper() for header in headers]
        for field_name, aliases in FIELD_COLUMNS.items():
            for col_index, header in enumerate(compact_headers):
                if not header:
                    continue
                if any(_compact(alias).upper() in header for alias in aliases):
                    result[field_name] = col_index
                    break
        return result

    def _is_sample_description_table(self, header_map: dict[str, int]) -> bool:
        if "component_name" not in header_map:
            return False
        supporting_fields = {"model", "batch_or_serial", "production_date", "expiration_date", "remark"}
        return bool(supporting_fields.intersection(header_map))

    def _sample_role(self, *, table: PdfTable, page_text: str) -> dict[str, str | bool]:
        context = " ".join(part for part in (table.title, table.caption, page_text) if part)
        compact_context = _compact(context)
        if "本次检验配合使用" in compact_context or "配合使用设备" in compact_context:
            return {
                "sample_role": "supporting_equipment",
                "supporting_equipment": True,
                "source_context": "本次检验配合使用",
            }
        return {"sample_role": "main_sample", "supporting_equipment": False}

    def _data_rows(
        self,
        table: PdfTable,
        header_row_index: int | None,
    ) -> list[tuple[int, list[str]]]:
        result: list[tuple[int, list[str]]] = []
        for row_index, row in enumerate(table.rows):
            if header_row_index is not None and row_index == header_row_index:
                continue
            result.append((row_index, [str(value or "") for value in row]))
        return result

    def _cell_value(self, row: list[str], column_index: int | None) -> str:
        if column_index is None or column_index >= len(row):
            return ""
        return row[column_index]


def _field_value(field: ReportField | None) -> str | None:
    if field is None:
        return None
    return field.value


def _parse_int(value: str | None) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
