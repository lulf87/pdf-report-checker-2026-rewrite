from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.c07_complex_matrix_evidence import C07ComplexMatrixEvidenceBuilder
from app.domain.evidence_package import EvidenceItem, EvidenceSourceType
from app.domain.finding import Finding
from app.domain.inspection_group import InspectionItemGroup


@dataclass(frozen=True)
class C07VisualEvidenceResult:
    items: list[EvidenceItem]
    metadata: dict[str, Any]


class C07VisualEvidenceBuilder:
    """Plan C07 table/page visual evidence items without materializing images."""

    def __init__(self, *, complex_matrix_builder: C07ComplexMatrixEvidenceBuilder | None = None) -> None:
        self.complex_matrix_builder = complex_matrix_builder or C07ComplexMatrixEvidenceBuilder()

    def build(
        self,
        *,
        finding: Finding,
        group: InspectionItemGroup | None,
        source_pdf_path: str | None,
        safe_id: Callable[[str], str],
    ) -> C07VisualEvidenceResult | None:
        if group is None or not group.pages:
            return None
        is_complex_matrix = self._is_complex_matrix(finding, group)
        if not source_pdf_path:
            metadata = self._metadata(
                has_visual_input=False,
                visual_review_mode="complex_matrix_table" if is_complex_matrix else "unavailable",
                missing_reasons={"source_pdf_path_missing"},
            )
            if is_complex_matrix:
                matrix_result = self.complex_matrix_builder.build(
                    finding=finding,
                    group=group,
                    source_pdf_path=source_pdf_path,
                    safe_id=safe_id,
                )
                metadata["expected_codex_when_complex_matrix"] = "uncertain_or_specialized_matrix_review"
                metadata["c07_complex_matrix_evidence"] = matrix_result.metadata
            return C07VisualEvidenceResult(items=[], metadata=metadata)

        base_id = safe_id(finding.id)
        items: list[EvidenceItem] = []
        page_image_refs: list[str] = []
        table_image_refs: list[str] = []
        item_group_crop_refs: list[str] = []
        result_column_crop_refs: list[str] = []
        conclusion_column_crop_refs: list[str] = []
        remark_column_crop_refs: list[str] = []
        missing_reasons: set[str] = set()

        for page_number in group.pages:
            page_item = self._page_item(finding=finding, base_id=base_id, page_number=page_number)
            items.append(page_item)
            page_image_refs.append(page_item.file_path or "")

            visual_rows = [
                self._visual_geometry(row.metadata.get("visual_geometry"))
                for row in group.rows
                if row.source_page == page_number
            ]
            visual_rows = [geometry for geometry in visual_rows if geometry is not None]
            if not visual_rows:
                missing_reasons.update({"table_bbox_missing", "row_bbox_missing", "field_bbox_missing"})
                continue

            table_bbox = self._union_bboxes(
                [geometry["table_bbox"] for geometry in visual_rows if geometry.get("table_bbox")]
            )
            row_bbox = self._union_bboxes(
                [row_bbox for row_bbox in (self._row_bbox(geometry) for geometry in visual_rows) if row_bbox]
            )

            if table_bbox is None:
                missing_reasons.add("table_bbox_missing")
            else:
                table_item = self._crop_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    kind="table",
                    bbox=table_bbox,
                    title=f"C07 table image evidence p{page_number}",
                    section="c07_visual_table",
                )
                items.append(table_item)
                table_image_refs.append(table_item.file_path or "")

            if row_bbox is None:
                missing_reasons.add("row_bbox_missing")
            else:
                row_item = self._crop_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    kind="item-group",
                    bbox=row_bbox,
                    title=f"C07 item group image evidence p{page_number}",
                    section="c07_visual_item_group",
                    ref_kind="item_group",
                )
                items.append(row_item)
                item_group_crop_refs.append(row_item.file_path or "")

            field_refs = {
                "test_result": result_column_crop_refs,
                "conclusion": conclusion_column_crop_refs,
                "remark": remark_column_crop_refs,
            }
            for field_name, ref_list in field_refs.items():
                field_bbox = self._field_bbox(visual_rows, field_name)
                if field_bbox is None:
                    missing_reasons.add("field_bbox_missing")
                    continue
                kind = "result" if field_name == "test_result" else field_name
                field_item = self._crop_item(
                    finding=finding,
                    base_id=base_id,
                    page_number=page_number,
                    kind=kind,
                    bbox=field_bbox,
                    title=f"C07 {kind} column image evidence p{page_number}",
                    section=f"c07_visual_{kind}",
                )
                items.append(field_item)
                ref_list.append(field_item.file_path or "")

        has_precise_geometry = bool(table_image_refs or item_group_crop_refs or result_column_crop_refs)
        visual_review_mode = "inspection_item_group" if has_precise_geometry else "page_only"
        if is_complex_matrix:
            visual_review_mode = "complex_matrix_table"

        metadata = self._metadata(
            has_visual_input=bool(page_image_refs),
            visual_review_mode=visual_review_mode,
            page_image_refs=page_image_refs,
            table_image_refs=table_image_refs,
            item_group_crop_refs=item_group_crop_refs,
            result_column_crop_refs=result_column_crop_refs,
            conclusion_column_crop_refs=conclusion_column_crop_refs,
            remark_column_crop_refs=remark_column_crop_refs,
            missing_reasons=missing_reasons,
        )
        if visual_review_mode == "complex_matrix_table":
            metadata["expected_codex_when_complex_matrix"] = "uncertain_or_specialized_matrix_review"
            matrix_result = self.complex_matrix_builder.build(
                finding=finding,
                group=group,
                source_pdf_path=source_pdf_path,
                safe_id=safe_id,
            )
            items.extend(matrix_result.items)
            metadata["c07_complex_matrix_evidence"] = matrix_result.metadata
        return C07VisualEvidenceResult(items=items, metadata=metadata)

    def _metadata(
        self,
        *,
        has_visual_input: bool,
        visual_review_mode: str,
        missing_reasons: set[str],
        page_image_refs: list[str] | None = None,
        table_image_refs: list[str] | None = None,
        item_group_crop_refs: list[str] | None = None,
        result_column_crop_refs: list[str] | None = None,
        conclusion_column_crop_refs: list[str] | None = None,
        remark_column_crop_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "has_visual_input": has_visual_input,
            "visual_review_mode": visual_review_mode,
            "page_image_refs": [ref for ref in page_image_refs or [] if ref],
            "table_image_refs": table_image_refs or [],
            "item_group_crop_refs": item_group_crop_refs or [],
            "result_column_crop_refs": result_column_crop_refs or [],
            "conclusion_column_crop_refs": conclusion_column_crop_refs or [],
            "remark_column_crop_refs": remark_column_crop_refs or [],
            "missing_visual_evidence_reasons": sorted(missing_reasons),
        }

    def _page_item(self, *, finding: Finding, base_id: str, page_number: int) -> EvidenceItem:
        return EvidenceItem(
            ref_id=f"c07_visual_page:{finding.id}:p{page_number}",
            source_type=EvidenceSourceType.IMAGE,
            title=f"C07 page image evidence p{page_number}",
            file_path=f"items/{base_id}-c07-page-p{page_number}.png",
            page_number=page_number,
            section="c07_visual_page",
            metadata={
                "finding_id": finding.id,
                "check_id": "C07",
                "codex_image_input": True,
                "render_source": "source_pdf",
                "source_pdf_ref": "package.metadata.source_pdf_path",
                "render_page_number": page_number,
                "crop_kind": "page",
            },
        )

    def _crop_item(
        self,
        *,
        finding: Finding,
        base_id: str,
        page_number: int,
        kind: str,
        bbox: list[float],
        title: str,
        section: str,
        ref_kind: str | None = None,
    ) -> EvidenceItem:
        normalized_kind = ref_kind or kind
        padded_bbox = self._pad_bbox(bbox)
        return EvidenceItem(
            ref_id=f"c07_visual_{normalized_kind}:{finding.id}:p{page_number}",
            source_type=EvidenceSourceType.IMAGE,
            title=title,
            file_path=f"items/{base_id}-c07-{kind}-p{page_number}.png",
            page_number=page_number,
            section=section,
            metadata={
                "finding_id": finding.id,
                "check_id": "C07",
                "codex_image_input": True,
                "render_source": "source_pdf",
                "source_pdf_ref": "package.metadata.source_pdf_path",
                "render_page_number": page_number,
                "render_bbox": padded_bbox,
                "crop_bbox": padded_bbox,
                "crop_kind": normalized_kind,
            },
        )

    def _visual_geometry(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None
        return value

    def _field_bbox(self, visual_rows: list[dict[str, Any]], field_name: str) -> list[float] | None:
        bboxes: list[list[float]] = []
        for geometry in visual_rows:
            field_bboxes = geometry.get("field_bboxes")
            if not isinstance(field_bboxes, dict):
                continue
            bbox = self._bbox(field_bboxes.get(field_name))
            if bbox is not None:
                bboxes.append(bbox)
        return self._union_bboxes(bboxes)

    def _row_bbox(self, geometry: dict[str, Any]) -> list[float] | None:
        row_bbox = self._bbox(geometry.get("row_bbox"))
        field_bboxes = geometry.get("field_bboxes")
        field_union = self._union_bboxes(list(field_bboxes.values())) if isinstance(field_bboxes, dict) else None
        if row_bbox is not None:
            if field_union is not None:
                return self._union_bboxes([row_bbox, field_union])
            return row_bbox

        return field_union

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
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None

    def _pad_bbox(self, bbox: list[float], *, x_pad: float = 4.0, y_pad: float = 3.0) -> list[float]:
        x0, y0, x1, y1 = bbox
        return [max(0.0, x0 - x_pad), max(0.0, y0 - y_pad), x1 + x_pad, y1 + y_pad]

    def _is_complex_matrix(self, finding: Finding, group: InspectionItemGroup) -> bool:
        if finding.metadata.get("complex_matrix_table") is True:
            return True
        if isinstance(finding.metadata.get("complex_matrix_table"), str):
            if str(finding.metadata["complex_matrix_table"]).strip().lower() in {"true", "1", "yes"}:
                return True
        if str(finding.metadata.get("normalized_item_no") or finding.metadata.get("item_no") or "").strip() == "59":
            return True
        if str(group.item_no or group.display_item_no or "").strip() == "59":
            return True
        for row in group.rows:
            value = row.metadata.get("complex_matrix_table") or row.metadata.get("is_complex_matrix_table")
            if value is True:
                return True
            if isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}:
                return True
        return False


__all__ = ["C07VisualEvidenceBuilder", "C07VisualEvidenceResult"]
