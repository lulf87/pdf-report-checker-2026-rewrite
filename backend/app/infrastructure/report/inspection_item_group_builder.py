from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.inspection_group import (
    ContinuationMarker,
    InheritedField,
    InspectionItemGroup,
    InspectionItemGroupBuildResult,
)
from app.domain.report import InspectionItem


_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
_GROUP_FIELDS = ("test_result", "conclusion", "remark")


@dataclass(frozen=True)
class _IndexedItem:
    item: InspectionItem
    source_index: int


@dataclass(frozen=True)
class _EffectiveRightFields:
    single_conclusion: str | None
    remark: str | None
    diagnostics: list[dict[str, Any]]


class InspectionItemGroupBuilder:
    """Group physical inspection table rows into business-level item groups."""

    def build(self, items: list[InspectionItem]) -> InspectionItemGroupBuildResult:
        diagnostics: list[dict[str, Any]] = []
        ungrouped_rows: list[InspectionItem] = []
        groups_by_item_no: dict[str, list[_IndexedItem]] = {}
        group_order: list[str] = []
        active_item_no: str | None = None

        indexed_items = [_IndexedItem(item=item, source_index=index) for index, item in enumerate(items)]
        ordered_items = self._ordered_items(indexed_items, diagnostics)

        for indexed in ordered_items:
            item = indexed.item
            item_no, _, _ = _normalized_item_no(item)

            if item_no is not None:
                if item_no not in groups_by_item_no:
                    groups_by_item_no[item_no] = []
                    group_order.append(item_no)
                groups_by_item_no[item_no].append(indexed)
                active_item_no = item_no
                continue

            if _raw_sequence_text(item):
                diagnostic_code = _invalid_sequence_diagnostic_code(item)
                if _has_payload(item) and active_item_no is not None and _should_attach_invalid_sequence_to_active_group(item):
                    diagnostics.append(
                        self._diagnostic(
                            code=diagnostic_code,
                            message="Invalid inspection item sequence text was treated as a payload row in the active group.",
                            indexed=indexed,
                            raw_sequence=_raw_sequence_text(item),
                            active_item_no=active_item_no,
                        )
                    )
                    groups_by_item_no[active_item_no].append(indexed)
                    continue

                if _has_payload(item) and active_item_no is None and _should_attach_invalid_sequence_to_active_group(item):
                    diagnostic_code = "UNGROUPED_PAYLOAD_WITH_INVALID_SEQUENCE"
                diagnostics.append(
                    self._diagnostic(
                        code=diagnostic_code if diagnostic_code != "INVALID_SEQUENCE_TEXT" else "UNPARSEABLE_ITEM_NO",
                        message="Inspection item sequence could not be parsed.",
                        indexed=indexed,
                        raw_sequence=_raw_sequence_text(item),
                    )
                )
                ungrouped_rows.append(item)
                continue

            if _has_payload(item):
                if active_item_no is None:
                    diagnostics.append(
                        self._diagnostic(
                            code="PAYLOAD_ROW_WITHOUT_ACTIVE_ITEM",
                            message="Blank-sequence payload row has no active inspection item group.",
                            indexed=indexed,
                        )
                    )
                    ungrouped_rows.append(item)
                    continue
                groups_by_item_no[active_item_no].append(indexed)
                continue

            diagnostics.append(
                self._diagnostic(
                    code="EMPTY_ROW_WITHOUT_PAYLOAD",
                    message="Blank inspection row has no payload and was not grouped.",
                    indexed=indexed,
                )
            )
            ungrouped_rows.append(item)

        groups = [
            self._build_group(item_no=item_no, indexed_items=groups_by_item_no[item_no])
            for item_no in group_order
        ]
        return InspectionItemGroupBuildResult(
            groups=groups,
            ungrouped_rows=ungrouped_rows,
            diagnostics=diagnostics,
            metadata={
                "source": "inspection_item_group_builder",
                "input_row_count": len(items),
                "group_count": len(groups),
                "ungrouped_row_count": len(ungrouped_rows),
            },
        )

    def _ordered_items(
        self,
        indexed_items: list[_IndexedItem],
        diagnostics: list[dict[str, Any]],
    ) -> list[_IndexedItem]:
        missing_context = [
            indexed
            for indexed in indexed_items
            if indexed.item.source_page is None or indexed.item.row_index_in_page is None
        ]
        for indexed in missing_context:
            diagnostics.append(
                self._diagnostic(
                    code="ROW_CONTEXT_MISSING",
                    message="Inspection item row is missing page or row context; original order is preserved.",
                    indexed=indexed,
                )
            )
        if missing_context:
            return list(indexed_items)
        return sorted(
            indexed_items,
            key=lambda indexed: (
                indexed.item.source_page or 0,
                indexed.item.row_index_in_page or 0,
                indexed.source_index,
            ),
        )

    def _build_group(
        self,
        *,
        item_no: str,
        indexed_items: list[_IndexedItem],
    ) -> InspectionItemGroup:
        rows = [indexed.item for indexed in indexed_items]
        display_item_no = _first_display_item_no(rows)
        right_fields = _effective_right_fields(rows)
        group = InspectionItemGroup(
            item_no=item_no,
            display_item_no=display_item_no,
            rows=rows,
            pages=_ordered_pages(rows),
            continuation_markers=_continuation_markers(indexed_items),
            effective_test_results=_effective_values(rows, "test_result", include_result_values=True),
            effective_single_conclusion=right_fields.single_conclusion,
            effective_remark=right_fields.remark,
            inherited_merged_fields=_inherited_fields(indexed_items),
            source_evidence=[_source_evidence(indexed) for indexed in indexed_items],
            diagnostics=list(right_fields.diagnostics),
        )
        if len(set(_effective_values(rows, "conclusion"))) > 1:
            group.diagnostics.append(
                {
                    "code": "CONFLICTING_EFFECTIVE_CONCLUSION",
                    "item_no": item_no,
                    "values": _effective_values(rows, "conclusion"),
                }
            )
        return group

    def _diagnostic(
        self,
        *,
        code: str,
        message: str,
        indexed: _IndexedItem,
        **extra: Any,
    ) -> dict[str, Any]:
        item = indexed.item
        diagnostic = {
            "code": code,
            "message": message,
            "source_index": indexed.source_index,
            "page_number": item.source_page,
            "row_index": item.row_index_in_page,
            "sequence_raw": item.sequence_raw,
        }
        diagnostic.update(extra)
        return diagnostic


def build_inspection_item_groups(items: list[InspectionItem]) -> InspectionItemGroupBuildResult:
    return InspectionItemGroupBuilder().build(items)


def _normalized_item_no(item: InspectionItem) -> tuple[str | None, bool, str | None]:
    raw = _raw_sequence_text(item)
    if raw:
        marker = _continuation_item_no(raw)
        if marker is not None:
            return marker, True, raw
        match = re.fullmatch(r"\d+", _compact(raw))
        if match:
            return str(int(match.group(0))), False, None
        return None, bool(item.is_continuation or item.metadata.get("logical_continuation")), raw
    if item.sequence is not None:
        return str(item.sequence), False, None
    return None, bool(item.is_continuation or item.metadata.get("logical_continuation")), raw or None


def _continuation_item_no(raw: str) -> str | None:
    text = _compact(raw).translate(_FULLWIDTH_DIGITS)
    match = re.fullmatch(r"续(\d+)", text)
    if not match:
        return None
    return str(int(match.group(1)))


def _raw_sequence_text(item: InspectionItem) -> str:
    return str(item.sequence_raw or "").strip()


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "")).translate(_FULLWIDTH_DIGITS)


def _invalid_sequence_diagnostic_code(item: InspectionItem) -> str:
    raw = _raw_sequence_text(item)
    if _looks_like_requirement_text(raw):
        return "SEQUENCE_TEXT_LOOKS_LIKE_REQUIREMENT"
    return "INVALID_SEQUENCE_TEXT"


def _should_attach_invalid_sequence_to_active_group(item: InspectionItem) -> bool:
    raw = _raw_sequence_text(item)
    return (
        _looks_like_requirement_text(raw)
        or _looks_like_alpha_subitem(raw)
        or _looks_like_standard_clause(raw)
        or _looks_like_long_chinese_text(raw)
    )


def _looks_like_requirement_text(raw: str) -> bool:
    text = raw.strip()
    compact = _compact(text)
    if text.startswith("——"):
        return True
    requirement_keywords = (
        "外壳",
        "ME设备",
        "ME系统",
        "一次性使用",
        "材料",
        "元器件",
        "附件",
        "SI单位",
        "单位的倍数",
        "标准要求",
    )
    return len(compact) > 12 and any(keyword in compact for keyword in requirement_keywords)


def _looks_like_alpha_subitem(raw: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][\)）\.、]", raw.strip()))


def _looks_like_standard_clause(raw: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)+", _compact(raw)))


def _looks_like_long_chinese_text(raw: str) -> bool:
    compact = _compact(raw)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", compact)
    return len(compact) > 12 and len(chinese_chars) >= 6


def _is_non_empty_value(value: str | None) -> bool:
    return value is not None and bool(str(value).strip())


def _value(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _has_payload(item: InspectionItem) -> bool:
    values = [
        item.item_name,
        item.standard_clause,
        item.standard_requirement,
        item.test_result,
        item.conclusion,
        item.remark,
        *item.result_values,
    ]
    return any(_is_non_empty_value(value) for value in values)


def _first_display_item_no(rows: list[InspectionItem]) -> str | None:
    for item in rows:
        raw = _raw_sequence_text(item)
        if raw and _continuation_item_no(raw) is None:
            return raw
    for item in rows:
        raw = _raw_sequence_text(item)
        if raw:
            return raw
    return None


def _ordered_pages(rows: list[InspectionItem]) -> list[int]:
    pages: list[int] = []
    for item in rows:
        page = item.source_page
        if page is not None and page not in pages:
            pages.append(page)
    return pages


def _continuation_markers(indexed_items: list[_IndexedItem]) -> list[ContinuationMarker]:
    markers: list[ContinuationMarker] = []
    for indexed in indexed_items:
        item = indexed.item
        raw = _raw_sequence_text(item)
        normalized = _continuation_item_no(raw)
        if normalized is None:
            continue
        markers.append(
            ContinuationMarker(
                raw_text=raw,
                normalized_item_no=normalized,
                page_number=item.source_page,
                row_index=item.row_index_in_page,
                source_index=indexed.source_index,
            )
        )
    return markers


def _effective_values(
    rows: list[InspectionItem],
    field_name: str,
    *,
    include_result_values: bool = False,
) -> list[str]:
    values: list[str] = []
    for item in rows:
        candidates = item.result_values if include_result_values and item.result_values else [getattr(item, field_name)]
        for candidate in candidates:
            text = _value(candidate)
            if text is None:
                continue
            values.append(text)
    return values


def _first_effective_value(rows: list[InspectionItem], field_name: str) -> str | None:
    seen: set[str] = set()
    for value in _effective_values(rows, field_name):
        if value in seen:
            continue
        seen.add(value)
        return value
    return None


def _effective_right_fields(rows: list[InspectionItem]) -> _EffectiveRightFields:
    explicit_remark = _first_effective_value(rows, "remark")
    if explicit_remark is not None:
        return _EffectiveRightFields(
            single_conclusion=_first_effective_value(rows, "conclusion"),
            remark=explicit_remark,
            diagnostics=[],
        )

    for item in rows:
        split = _split_combined_conclusion_remark(item.conclusion)
        if split is None:
            continue
        conclusion, remark = split
        return _EffectiveRightFields(
            single_conclusion=conclusion,
            remark=remark,
            diagnostics=[
                _right_field_diagnostic(
                    "SPLIT_COMBINED_CONCLUSION_REMARK",
                    item=item,
                    source_field="conclusion",
                    raw_value=item.conclusion,
                    single_conclusion=conclusion,
                    remark=remark,
                )
            ],
        )

    for item in rows:
        shifted = _shifted_conclusion_remark(item)
        if shifted is None:
            continue
        conclusion, remark = shifted
        return _EffectiveRightFields(
            single_conclusion=conclusion,
            remark=remark,
            diagnostics=[
                _right_field_diagnostic(
                    "RECOVERED_SHIFTED_REMARK_PLACEHOLDER",
                    item=item,
                    source_field="conclusion",
                    raw_value=item.conclusion,
                    single_conclusion=conclusion,
                    remark=remark,
                )
            ],
        )

    for item in rows:
        if _value(item.conclusion) is not None:
            continue
        split = _split_combined_conclusion_remark(item.test_result)
        if split is None:
            continue
        conclusion, remark = split
        return _EffectiveRightFields(
            single_conclusion=conclusion,
            remark=remark,
            diagnostics=[
                _right_field_diagnostic(
                    "SPLIT_COMBINED_TEST_RESULT_AS_CONCLUSION_REMARK",
                    item=item,
                    source_field="test_result",
                    raw_value=item.test_result,
                    single_conclusion=conclusion,
                    remark=remark,
                )
            ],
        )

    return _EffectiveRightFields(
        single_conclusion=_first_effective_value(rows, "conclusion"),
        remark=None,
        diagnostics=[],
    )


def _split_combined_conclusion_remark(value: str | None) -> tuple[str, str] | None:
    text = _value(value)
    if text is None:
        return None
    match = re.fullmatch(r"(不符合|符合|/|——)\s*/", text)
    if not match:
        return None
    return match.group(1), "/"


def _shifted_conclusion_remark(item: InspectionItem) -> tuple[str, str] | None:
    if _value(item.remark) is not None:
        return None
    if _value(item.conclusion) != "/":
        return None
    result = _value(item.test_result)
    if result not in {"符合", "不符合"}:
        return None
    return result, "/"


def _right_field_diagnostic(
    code: str,
    *,
    item: InspectionItem,
    source_field: str,
    raw_value: str | None,
    single_conclusion: str,
    remark: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "source_field": source_field,
        "raw_value": raw_value,
        "effective_single_conclusion": single_conclusion,
        "effective_remark": remark,
        "page_number": item.source_page,
        "row_index": item.row_index_in_page,
        "sequence_raw": item.sequence_raw,
    }


def _inherited_fields(indexed_items: list[_IndexedItem]) -> list[InheritedField]:
    inherited: list[InheritedField] = []
    for field_name in _GROUP_FIELDS:
        source: _IndexedItem | None = None
        source_value: str | None = None
        blank_targets: list[int] = []
        for indexed in indexed_items:
            value = _value(getattr(indexed.item, field_name))
            if value is None:
                blank_targets.append(indexed.source_index)
                continue
            if source is None:
                source = indexed
                source_value = value
        if source is None or source_value is None:
            continue
        target_indexes = [index for index in blank_targets if index != source.source_index]
        if target_indexes:
            inherited.append(
                InheritedField(
                    field_name=field_name,
                    value=source_value,
                    source_row_index=source.source_index,
                    target_row_indexes=target_indexes,
                    reason=_inheritance_reason(indexed_items, field_name),
                )
            )
    return inherited


def _inheritance_reason(indexed_items: list[_IndexedItem], field_name: str) -> str:
    if any(indexed.item.field_provenance.get(field_name) == "merge_inferred" for indexed in indexed_items):
        return "merge_inferred"
    if any(indexed.item.metadata.get("logical_continuation") for indexed in indexed_items):
        return "logical_continuation"
    return "group_effective_value"


def _source_evidence(indexed: _IndexedItem) -> dict[str, Any]:
    item = indexed.item
    return {
        "source_index": indexed.source_index,
        "page_number": item.source_page,
        "row_index": item.row_index_in_page,
        "item_no": item.sequence_raw if item.sequence_raw is not None else item.sequence,
        "normalized_item_no": (_normalized_item_no(item)[0]),
        "is_continuation": item.is_continuation,
        "item_name": item.item_name,
        "standard_clause": item.standard_clause,
        "standard_requirement": item.standard_requirement,
        "test_result": item.test_result,
        "result_values": list(item.result_values),
        "single_conclusion": item.conclusion,
        "remark": item.remark,
        "field_provenance": dict(item.field_provenance),
        "metadata": _safe_metadata(item.metadata),
    }


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and "/Users/" in value:
            result[key] = "[redacted-path]"
        else:
            result[key] = value
    return result


__all__ = ["InspectionItemGroupBuilder", "build_inspection_item_groups"]
