from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.domain.evidence_package import EvidenceItem, EvidenceSourceType
from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import InspectionItem


@dataclass(frozen=True)
class C07ComplexMatrixEvidenceResult:
    items: list[EvidenceItem]
    metadata: dict[str, Any]


class C07ComplexMatrixEvidenceBuilder:
    """Plan item-59 complex matrix visual evidence without materializing images."""

    def build(
        self,
        *,
        finding: Finding,
        group: InspectionItemGroup,
        source_pdf_path: str | None,
        safe_id: Callable[[str], str],
    ) -> C07ComplexMatrixEvidenceResult:
        base_id = safe_id(finding.id)
        pages = list(group.pages)
        missing_reasons: set[str] = set()
        structured_hints = self._structured_matrix_hints(finding=finding, group=group)

        if not source_pdf_path:
            missing_reasons.add("source_pdf_path_missing")
            return C07ComplexMatrixEvidenceResult(
                items=[],
                metadata=self._metadata(
                    has_complex_matrix_input=False,
                    finding=finding,
                    group=group,
                    pages=pages,
                    structured_hints=structured_hints,
                    missing_reasons=missing_reasons,
                ),
            )

        items: list[EvidenceItem] = []
        matrix_page_image_refs: list[str] = []
        matrix_table_image_refs: list[str] = []
        matrix_header_image_refs: list[str] = []
        matrix_body_image_refs: list[str] = []
        result_matrix_image_refs: list[str] = []
        conclusion_column_image_refs: list[str] = []
        continuation_page_image_refs: list[str] = []

        for index, page_number in enumerate(pages):
            page_item = self._image_item(
                finding=finding,
                base_id=base_id,
                page_number=page_number,
                role="page",
                file_kind="page",
                bbox=None,
                title=f"C07 complex matrix full page evidence p{page_number}",
            )
            items.append(page_item)
            matrix_page_image_refs.append(page_item.file_path or "")

            visual_rows = self._visual_rows_for_page(group, page_number)
            table_bbox = self._table_bbox(visual_rows)
            row_bbox = self._row_bbox(visual_rows)
            result_bbox = self._field_bbox(visual_rows, "test_result")
            conclusion_bbox = self._field_bbox(visual_rows, "conclusion")

            if table_bbox is None:
                missing_reasons.add("matrix_bbox_missing")
            else:
                table_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="table",
                    file_kind="table",
                    bbox=table_bbox,
                    title=f"C07 complex matrix table crop evidence p{page_number}",
                )
                items.append(table_item)
                matrix_table_image_refs.append(table_item.file_path or "")

                header_bbox = self._header_bbox(table_bbox=table_bbox, row_bbox=row_bbox)
                header_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="header",
                    file_kind="header",
                    bbox=header_bbox,
                    title=f"C07 complex matrix header crop evidence p{page_number}",
                )
                items.append(header_item)
                matrix_header_image_refs.append(header_item.file_path or "")

            if row_bbox is None:
                missing_reasons.add("matrix_bbox_missing")
            else:
                body_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="body",
                    file_kind="body",
                    bbox=row_bbox,
                    title=f"C07 complex matrix body crop evidence p{page_number}",
                )
                items.append(body_item)
                matrix_body_image_refs.append(body_item.file_path or "")

            if result_bbox is None:
                missing_reasons.add("column_bbox_missing")
            else:
                result_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="result",
                    file_kind="result",
                    bbox=result_bbox,
                    title=f"C07 complex matrix result crop evidence p{page_number}",
                )
                items.append(result_item)
                result_matrix_image_refs.append(result_item.file_path or "")

            if conclusion_bbox is None:
                missing_reasons.add("column_bbox_missing")
            else:
                conclusion_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="conclusion",
                    file_kind="conclusion",
                    bbox=conclusion_bbox,
                    title=f"C07 complex matrix conclusion crop evidence p{page_number}",
                )
                items.append(conclusion_item)
                conclusion_column_image_refs.append(conclusion_item.file_path or "")

            if index > 0:
                continuation_bbox = table_bbox or row_bbox
                continuation_item = self._image_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    role="continuation",
                    file_kind="continuation",
                    bbox=continuation_bbox,
                    title=f"C07 complex matrix continuation evidence p{page_number}",
                )
                items.append(continuation_item)
                continuation_page_image_refs.append(continuation_item.file_path or "")

        metadata = self._metadata(
            has_complex_matrix_input=bool(matrix_page_image_refs),
            finding=finding,
            group=group,
            pages=pages,
            structured_hints=structured_hints,
            missing_reasons=missing_reasons,
            matrix_page_image_refs=matrix_page_image_refs,
            matrix_table_image_refs=matrix_table_image_refs,
            matrix_header_image_refs=matrix_header_image_refs,
            matrix_body_image_refs=matrix_body_image_refs,
            result_matrix_image_refs=result_matrix_image_refs,
            conclusion_column_image_refs=conclusion_column_image_refs,
            continuation_page_image_refs=continuation_page_image_refs,
        )
        return C07ComplexMatrixEvidenceResult(items=items, metadata=metadata)

    def _metadata(
        self,
        *,
        has_complex_matrix_input: bool,
        finding: Finding,
        group: InspectionItemGroup,
        pages: list[int],
        structured_hints: dict[str, Any],
        missing_reasons: set[str],
        matrix_page_image_refs: list[str] | None = None,
        matrix_table_image_refs: list[str] | None = None,
        matrix_header_image_refs: list[str] | None = None,
        matrix_body_image_refs: list[str] | None = None,
        result_matrix_image_refs: list[str] | None = None,
        conclusion_column_image_refs: list[str] | None = None,
        continuation_page_image_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "has_complex_matrix_input": has_complex_matrix_input,
            "review_mode": "complex_matrix_specialized",
            "item_no": str(group.item_no or finding.metadata.get("item_no") or ""),
            "pages": pages,
            "matrix_page_image_refs": self._refs(matrix_page_image_refs),
            "matrix_table_image_refs": self._refs(matrix_table_image_refs),
            "matrix_header_image_refs": self._refs(matrix_header_image_refs),
            "matrix_body_image_refs": self._refs(matrix_body_image_refs),
            "result_matrix_image_refs": self._refs(result_matrix_image_refs),
            "conclusion_column_image_refs": self._refs(conclusion_column_image_refs),
            "continuation_page_image_refs": self._refs(continuation_page_image_refs),
            "structured_matrix_hints": structured_hints,
            "missing_complex_matrix_evidence_reasons": sorted(missing_reasons),
        }

    def _image_item(
        self,
        *,
        finding: Finding,
        base_id: str,
        page_number: int,
        role: str,
        file_kind: str,
        bbox: list[float] | None,
        title: str,
    ) -> EvidenceItem:
        metadata: dict[str, Any] = {
            "finding_id": finding.id,
            "check_id": "C07",
            "codex_image_input": True,
            "render_source": "source_pdf",
            "source_pdf_ref": "package.metadata.source_pdf_path",
            "render_page_number": page_number,
            "crop_kind": f"complex_matrix_{role}",
            "matrix_evidence_role": role,
        }
        if bbox is not None:
            padded_bbox = self._pad_bbox(bbox)
            metadata["render_bbox"] = padded_bbox
            metadata["crop_bbox"] = padded_bbox
        return EvidenceItem(
            ref_id=f"c07_complex_matrix_{role}:{finding.id}:p{page_number}",
            source_type=EvidenceSourceType.IMAGE,
            title=title,
            file_path=f"items/{base_id}-c07-matrix-{file_kind}-p{page_number}.png",
            page_number=page_number,
            section="c07_complex_matrix_visual",
            metadata=metadata,
        )

    def _structured_matrix_hints(self, *, finding: Finding, group: InspectionItemGroup) -> dict[str, Any]:
        rows = [self._source_row_summary(row) for row in group.rows]
        continuation_markers = [marker.model_dump(mode="json") for marker in group.continuation_markers]
        effective_results = list(group.effective_test_results)
        conclusion_candidates = self._actual_conclusion_candidates(finding=finding, group=group)
        placeholder_tokens, non_placeholder_tokens = self._result_token_summary(group, conclusion_candidates)
        known_columns = self._known_columns(group)
        return {
            "item_no": str(group.item_no or finding.metadata.get("item_no") or ""),
            "pages": list(group.pages),
            "group_row_count": len(group.rows),
            "continuation_markers": continuation_markers,
            "source_rows": rows,
            "effective_test_results": effective_results,
            "actual_conclusion_candidates": conclusion_candidates,
            "complex_matrix_table": True,
            "complex_matrix_reason": finding.metadata.get("complex_matrix_reason") or self._complex_reason_from_rows(group),
            "known_columns": known_columns,
            "placeholder_tokens": placeholder_tokens,
            "non_placeholder_tokens": non_placeholder_tokens,
            "candidate_conclusion": self._candidate_conclusion(finding=finding, group=group),
        }

    def _source_row_summary(self, row: InspectionItem) -> dict[str, Any]:
        visual_geometry = row.metadata.get("visual_geometry")
        table_id = visual_geometry.get("table_id") if isinstance(visual_geometry, dict) else None
        return {
            "sequence_raw": row.sequence_raw,
            "sequence": row.sequence,
            "is_continuation": row.is_continuation,
            "item_name": row.item_name,
            "standard_clause": row.standard_clause,
            "standard_requirement": row.standard_requirement,
            "test_result": row.test_result,
            "result_values": list(row.result_values),
            "conclusion": row.conclusion,
            "remark": row.remark,
            "source_page": row.source_page,
            "row_index_in_page": row.row_index_in_page,
            "condition": row.metadata.get("condition"),
            "row_text": row.metadata.get("row_text"),
            "field_provenance": dict(row.field_provenance),
            "table_id": table_id,
        }

    def _actual_conclusion_candidates(
        self,
        *,
        finding: Finding,
        group: InspectionItemGroup,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for source, value in (
            ("finding_metadata.actual_conclusion", finding.metadata.get("actual_conclusion")),
            ("finding.actual", finding.actual),
            ("group.effective_single_conclusion", group.effective_single_conclusion),
        ):
            self._append_candidate(candidates, source=source, value=value)
        for row in group.rows:
            self._append_candidate(
                candidates,
                source="row.conclusion",
                value=row.conclusion,
                page=row.source_page,
                row_index=row.row_index_in_page,
            )
        return candidates

    def _append_candidate(
        self,
        candidates: list[dict[str, Any]],
        *,
        source: str,
        value: Any,
        page: int | None = None,
        row_index: int | None = None,
    ) -> None:
        text = self._text(value)
        if text is None:
            return
        if any(candidate["value"] == text and candidate["source"] == source for candidate in candidates):
            return
        candidate: dict[str, Any] = {"value": text, "source": source}
        if page is not None:
            candidate["page_number"] = page
        if row_index is not None:
            candidate["row_index"] = row_index
        candidates.append(candidate)

    def _result_token_summary(
        self,
        group: InspectionItemGroup,
        conclusion_candidates: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        placeholder_tokens: list[str] = []
        non_placeholder_tokens: list[str] = []
        values: list[Any] = [
            *group.effective_test_results,
            *group.original_effective_test_results,
            *group.recovered_effective_test_results,
            group.effective_remark,
            *(candidate["value"] for candidate in conclusion_candidates),
        ]
        for row in group.rows:
            values.extend([row.test_result, *row.result_values, row.conclusion, row.remark])

        for value in values:
            text = self._text(value)
            if text is None:
                continue
            bucket = placeholder_tokens if text in {"——", "/"} else non_placeholder_tokens
            if text not in bucket:
                bucket.append(text)
        return placeholder_tokens, non_placeholder_tokens

    def _known_columns(self, group: InspectionItemGroup) -> list[str]:
        columns: list[str] = []
        field_map = [
            ("sequence_raw", "序号"),
            ("item_name", "检验项目"),
            ("standard_requirement", "检验要求"),
            ("test_result", "检验结果"),
            ("conclusion", "单项结论"),
            ("remark", "备注"),
        ]
        for field_name, label in field_map:
            if any(self._text(getattr(row, field_name)) for row in group.rows):
                columns.append(label)
        return columns

    def _candidate_conclusion(self, *, finding: Finding, group: InspectionItemGroup) -> str | None:
        for value in (finding.metadata.get("actual_conclusion"), finding.actual, group.effective_single_conclusion):
            text = self._text(value)
            if text is not None:
                return text
        for row in group.rows:
            text = self._text(row.conclusion)
            if text is not None:
                return text
        return None

    def _complex_reason_from_rows(self, group: InspectionItemGroup) -> str | None:
        for row in group.rows:
            reason = row.metadata.get("complex_matrix_reason")
            if isinstance(reason, str) and reason.strip():
                return reason
        return "complex_matrix_table"

    def _visual_rows_for_page(self, group: InspectionItemGroup, page_number: int) -> list[dict[str, Any]]:
        visual_rows: list[dict[str, Any]] = []
        for row in group.rows:
            if row.source_page != page_number:
                continue
            value = row.metadata.get("visual_geometry")
            if isinstance(value, dict):
                visual_rows.append(value)
        return visual_rows

    def _table_bbox(self, visual_rows: list[dict[str, Any]]) -> list[float] | None:
        return self._union_bboxes([row.get("table_bbox") for row in visual_rows])

    def _row_bbox(self, visual_rows: list[dict[str, Any]]) -> list[float] | None:
        row_bboxes = [row.get("row_bbox") for row in visual_rows]
        field_bboxes: list[Any] = []
        for row in visual_rows:
            fields = row.get("field_bboxes")
            if isinstance(fields, dict):
                field_bboxes.extend(fields.values())
        return self._union_bboxes([*row_bboxes, *field_bboxes])

    def _field_bbox(self, visual_rows: list[dict[str, Any]], field_name: str) -> list[float] | None:
        bboxes: list[Any] = []
        for row in visual_rows:
            fields = row.get("field_bboxes")
            if isinstance(fields, dict):
                bboxes.append(fields.get(field_name))
        return self._union_bboxes(bboxes)

    def _header_bbox(self, *, table_bbox: list[float], row_bbox: list[float] | None) -> list[float]:
        x0, y0, x1, y1 = table_bbox
        if row_bbox is None:
            header_bottom = y0 + min(80.0, max(24.0, (y1 - y0) * 0.18))
        else:
            header_bottom = max(y0 + 12.0, min(row_bbox[1] - 2.0, y1))
        return [x0, y0, x1, header_bottom]

    def _union_bboxes(self, bboxes: list[Any]) -> list[float] | None:
        normalized = [bbox for bbox in (self._bbox(value) for value in bboxes) if bbox is not None]
        if not normalized:
            return None
        return [
            min(bbox[0] for bbox in normalized),
            min(bbox[1] for bbox in normalized),
            max(bbox[2] for bbox in normalized),
            max(bbox[3] for bbox in normalized),
        ]

    def _bbox(self, value: Any) -> list[float] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None
        try:
            bbox = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            return None
        return bbox

    def _pad_bbox(self, bbox: list[float], *, x_pad: float = 4.0, y_pad: float = 3.0) -> list[float]:
        x0, y0, x1, y1 = bbox
        return [max(0.0, x0 - x_pad), max(0.0, y0 - y_pad), x1 + x_pad, y1 + y_pad]

    def _text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _refs(self, refs: list[str] | None) -> list[str]:
        return [ref for ref in refs or [] if ref]


__all__ = ["C07ComplexMatrixEvidenceBuilder", "C07ComplexMatrixEvidenceResult"]
