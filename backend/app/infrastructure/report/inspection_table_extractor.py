from __future__ import annotations

import re
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.pdf import ParsedPdf, PdfTable
from app.domain.report import InspectionItem, InspectionTable


FIELD_COLUMNS = {
    "sequence_raw": ("序号", "编号", "item_no"),
    "item_name": ("检验项目", "检验项目名称", "项目名称", "item_name"),
    "standard_clause": ("标准条款", "条款", "standard_clause"),
    "standard_requirement": ("标准要求", "要求", "standard_requirement"),
    "test_result": ("检验结果", "结果", "test_result"),
    "conclusion": ("单项结论", "结论", "single_conclusion"),
    "remark": ("备注", "说明", "remark"),
}

DISPLAY_NAMES = {
    "sequence_raw": "序号",
    "item_name": "检验项目",
    "standard_clause": "标准条款",
    "standard_requirement": "标准要求",
    "test_result": "检验结果",
    "conclusion": "单项结论",
    "remark": "备注",
}


class InspectionTableExtractor:
    """Extract inspection-table facts for C07-C10 rule inputs.

    The extractor keeps one output item per source row. It preserves blank
    sequence continuation rows so later rules can group by sequence themselves.
    """

    def extract_table(self, parsed_pdf: ParsedPdf) -> InspectionTable | None:
        table_pages: list[tuple[int, PdfTable, dict[str, int], int]] = []

        for page in parsed_pdf.pages:
            for table in page.tables:
                header_map, header_row_index = self._header_map(table)
                if self._is_inspection_table(header_map):
                    table_pages.append((page.page_number, table, header_map, header_row_index))

        if not table_pages:
            return None

        items: list[InspectionItem] = []
        page_numbers: list[int] = []
        header_fields = [DISPLAY_NAMES[field_name] for field_name in FIELD_COLUMNS]

        previous_item: InspectionItem | None = None
        for page_number, table, header_map, header_row_index in table_pages:
            page_numbers.append(page_number)
            extracted = self._extract_items_from_table(
                parsed_pdf=parsed_pdf,
                page_number=page_number,
                table=table,
                header_map=header_map,
                header_row_index=header_row_index,
                previous_item=previous_item,
            )
            if extracted:
                previous_item = extracted[-1]
            items.extend(extracted)

        return InspectionTable(
            table_id="inspection-table",
            items=items,
            page_span=(min(page_numbers), max(page_numbers)) if page_numbers else None,
            header_fields=header_fields,
            evidence=[evidence for item in items for evidence in item.evidence],
        )

    def extract_items(self, parsed_pdf: ParsedPdf) -> list[InspectionItem]:
        table = self.extract_table(parsed_pdf)
        return table.items if table is not None else []

    def _extract_items_from_table(
        self,
        *,
        parsed_pdf: ParsedPdf,
        page_number: int,
        table: PdfTable,
        header_map: dict[str, int],
        header_row_index: int | None,
        previous_item: InspectionItem | None,
    ) -> list[InspectionItem]:
        row_values, provenance = self._rows_with_merge_semantics(table)
        items: list[InspectionItem] = []
        last_item = previous_item

        for row_index, row in enumerate(row_values):
            if header_row_index is not None and row_index == header_row_index:
                continue
            if not any((cell or "").strip() for cell in row):
                continue

            values = {
                field_name: self._cell_value(row, header_map.get(field_name))
                for field_name in FIELD_COLUMNS
            }
            if not any((value or "").strip() for value in values.values()):
                continue

            sequence_raw = values["sequence_raw"].strip()
            is_continuation = self._is_continuation_marker(sequence_raw)
            sequence = parse_sequence(sequence_raw)
            metadata: dict[str, Any] = {
                "item_no": sequence_raw,
                "item_name": values["item_name"],
                "single_conclusion": values["conclusion"],
                "source_table_id": table.table_id,
                "field_columns": dict(header_map),
                "row_text": " ".join(cell.strip() for cell in row if cell and cell.strip()),
            }
            visual_geometry = self._visual_geometry(table, row_index, header_map)
            if visual_geometry is not None:
                metadata["visual_geometry"] = visual_geometry

            item = InspectionItem(
                sequence_raw=sequence_raw,
                sequence=sequence,
                is_continuation=is_continuation,
                item_name=values["item_name"],
                standard_clause=values["standard_clause"],
                standard_requirement=values["standard_requirement"],
                test_result=values["test_result"],
                result_values=[values["test_result"]] if values["test_result"].strip() else [],
                conclusion=values["conclusion"],
                remark=values["remark"],
                source_page=page_number,
                row_index_in_page=row_index,
                field_provenance=self._field_provenance(header_map, provenance.get(row_index, {})),
                row_location=Location(
                    source_id=parsed_pdf.file_id,
                    source_type=SourceType.REPORT,
                    page_number=page_number,
                    table_id=table.table_id,
                    row_index=row_index,
                ),
                evidence=self._row_evidence(
                    parsed_pdf=parsed_pdf,
                    table=table,
                    page_number=page_number,
                    row_index=row_index,
                    values=values,
                    header_map=header_map,
                ),
                metadata=metadata,
            )

            if not item.sequence_raw and self._should_mark_blank_row_as_continuation(item, last_item):
                item.is_continuation = True
                item.metadata["logical_continuation"] = True

            items.append(item)
            last_item = item

        return items

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
        compact_headers = [_compact(header) for header in headers]
        for field_name, aliases in FIELD_COLUMNS.items():
            for col_index, header in enumerate(compact_headers):
                if not header:
                    continue
                if any(_compact(alias) in header for alias in aliases):
                    result[field_name] = col_index
                    break
        return result

    def _is_inspection_table(self, header_map: dict[str, int]) -> bool:
        required = {"sequence_raw", "item_name", "test_result", "conclusion"}
        return required.issubset(header_map)

    def _rows_with_merge_semantics(
        self,
        table: PdfTable,
    ) -> tuple[list[list[str]], dict[int, dict[int, str]]]:
        row_count = len(table.rows)
        col_count = max((len(row) for row in table.rows), default=0)
        rows = [
            [str(table.rows[row_index][col_index] or "").strip() if col_index < len(table.rows[row_index]) else "" for col_index in range(col_count)]
            for row_index in range(row_count)
        ]
        provenance: dict[int, dict[int, str]] = {
            row_index: {col_index: "native" for col_index in range(col_count)}
            for row_index in range(row_count)
        }

        for span in self._cell_spans(table):
            row_index = span.get("row", 0)
            col_index = span.get("col", 0)
            row_span = span.get("row_span", 1)
            if row_index >= row_count or col_index >= col_count or row_span <= 1:
                continue
            anchor = rows[row_index][col_index].strip()
            if not anchor:
                continue
            for offset in range(1, row_span):
                target_row = row_index + offset
                if target_row >= row_count:
                    break
                if rows[target_row][col_index]:
                    continue
                rows[target_row][col_index] = anchor
                provenance[target_row][col_index] = "merge_inferred"

        return rows, provenance

    def _cell_spans(self, table: PdfTable) -> list[dict[str, int]]:
        raw_spans = table.metadata.get("cell_spans") or table.metadata.get("spans") or []
        spans: list[dict[str, int]] = []
        if isinstance(raw_spans, dict):
            for key, value in raw_spans.items():
                if not isinstance(key, tuple) or len(key) != 2:
                    continue
                row_span = value[0] if isinstance(value, (tuple, list)) and value else 1
                spans.append({"row": int(key[0]), "col": int(key[1]), "row_span": int(row_span)})
        elif isinstance(raw_spans, list):
            for raw_span in raw_spans:
                if not isinstance(raw_span, dict):
                    continue
                spans.append(
                    {
                        "row": int(raw_span.get("row", 0)),
                        "col": int(raw_span.get("col", raw_span.get("column", 0))),
                        "row_span": int(raw_span.get("row_span", raw_span.get("rowspan", 1))),
                    }
                )
        return spans

    def _cell_value(self, row: list[str], col_index: int | None) -> str:
        if col_index is None or col_index >= len(row):
            return ""
        return row[col_index].strip()

    def _is_continuation_marker(self, sequence_raw: str) -> bool:
        return bool(re.match(r"^\s*续\s*[:：]?\s*\d+", sequence_raw or ""))

    def _should_mark_blank_row_as_continuation(
        self,
        item: InspectionItem,
        previous_item: InspectionItem | None,
    ) -> bool:
        if item.sequence_raw:
            return False
        if previous_item is None:
            return False
        if not (previous_item.sequence_raw or previous_item.is_continuation):
            return False
        payload = [
            item.item_name,
            item.standard_clause,
            item.standard_requirement,
            item.test_result,
            item.conclusion,
            item.remark,
        ]
        if not any((value or "").strip() for value in payload):
            return False
        if any(source == "merge_inferred" for source in item.field_provenance.values()):
            return True
        item_name = (item.item_name or "").strip()
        if not item_name:
            return True
        if re.match(r"^[a-zA-Z][\)）\.、]", item_name):
            return True
        if item_name.startswith(("注", "说明", "其中")):
            return True
        previous_clause = _compact(previous_item.standard_clause or "")
        current_clause = _compact(item.standard_clause or "")
        return bool(previous_clause and current_clause and previous_clause == current_clause)

    def _field_provenance(
        self,
        header_map: dict[str, int],
        row_provenance: dict[int, str],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for field_name, col_index in header_map.items():
            source = row_provenance.get(col_index)
            if source:
                result[field_name] = source
        return result

    def _visual_geometry(
        self,
        table: PdfTable,
        row_index: int,
        header_map: dict[str, int],
    ) -> dict[str, Any] | None:
        cell_bboxes = table.metadata.get("cell_bboxes")
        if not isinstance(cell_bboxes, list) or row_index >= len(cell_bboxes):
            return None
        row_cells = cell_bboxes[row_index]
        if not isinstance(row_cells, list):
            return None

        field_bboxes: dict[str, list[float]] = {}
        for field_name, col_index in header_map.items():
            bbox = self._bbox_list_from_cell(row_cells, col_index)
            if bbox is not None:
                field_bboxes[field_name] = bbox

        row_bbox = self._union_bboxes(list(field_bboxes.values()))
        table_bbox = self._bbox_list_from_model(table.bbox)
        if row_bbox is None and table_bbox is None and not field_bboxes:
            return None
        return {
            "table_id": table.table_id,
            "table_bbox": table_bbox,
            "row_bbox": row_bbox,
            "field_bboxes": field_bboxes,
        }

    def _bbox_list_from_model(self, bbox: Any) -> list[float] | None:
        if bbox is None:
            return None
        try:
            return [float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)]
        except (AttributeError, TypeError, ValueError):
            return self._bbox_list_from_cell([bbox], 0)

    def _bbox_list_from_cell(self, row_cells: list[Any], col_index: int | None) -> list[float] | None:
        if col_index is None or col_index < 0 or col_index >= len(row_cells):
            return None
        raw_bbox = row_cells[col_index]
        if raw_bbox is None:
            return None
        if isinstance(raw_bbox, dict):
            try:
                return [
                    float(raw_bbox["x0"]),
                    float(raw_bbox["y0"]),
                    float(raw_bbox["x1"]),
                    float(raw_bbox["y1"]),
                ]
            except (KeyError, TypeError, ValueError):
                return None
        if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
            return None
        try:
            return [float(value) for value in raw_bbox]
        except (TypeError, ValueError):
            return None

    def _union_bboxes(self, bboxes: list[list[float]]) -> list[float] | None:
        valid = [bbox for bbox in bboxes if len(bbox) == 4]
        if not valid:
            return None
        return [
            min(bbox[0] for bbox in valid),
            min(bbox[1] for bbox in valid),
            max(bbox[2] for bbox in valid),
            max(bbox[3] for bbox in valid),
        ]

    def _row_evidence(
        self,
        *,
        parsed_pdf: ParsedPdf,
        table: PdfTable,
        page_number: int,
        row_index: int,
        values: dict[str, str],
        header_map: dict[str, int],
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        for field_name, display_name in DISPLAY_NAMES.items():
            col_index = header_map.get(field_name)
            value = values.get(field_name, "")
            evidence.append(
                Evidence(
                    id=f"{parsed_pdf.file_id}:{table.table_id}:r{row_index}:c{col_index}:{field_name}",
                    source_type=SourceType.REPORT,
                    location=Location(
                        source_id=parsed_pdf.file_id,
                        source_type=SourceType.REPORT,
                        page_number=page_number,
                        table_id=table.table_id,
                        row_index=row_index,
                        column_name=display_name,
                    ),
                    raw_text=value,
                    normalized_text=_compact(value),
                    value=value,
                    method=EvidenceMethod.PDF_TEXT,
                    confidence=Confidence.HIGH,
                    metadata={
                        "field_name": field_name,
                        "column_index": col_index,
                    },
                )
            )
        return evidence


def parse_sequence(sequence_raw: str | None) -> int | None:
    text = _compact(sequence_raw or "").translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if not text:
        return None
    continuation_match = re.fullmatch(r"续[:：]?(\d+)", text)
    if continuation_match:
        return int(continuation_match.group(1))
    numeric_match = re.fullmatch(r"\d+", text)
    return int(numeric_match.group(0)) if numeric_match else None


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
