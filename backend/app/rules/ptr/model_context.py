from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.domain.common import Confidence
from app.domain.report import ReportDocument, ReportField


class ReportModelCandidate(BaseModel):
    value: str
    source: str
    page: int | None = None
    confidence: str = "medium"


class ReportModelContext(BaseModel):
    primary_model: str | None = None
    model_candidates: list[ReportModelCandidate] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


def build_report_model_context(report_doc: ReportDocument) -> ReportModelContext:
    candidates: list[ReportModelCandidate] = []
    candidates.extend(_candidates_from_field(report_doc.first_page.model_spec if report_doc.first_page else None, "report_homepage"))
    if report_doc.first_page is not None:
        for field in report_doc.first_page.fields:
            candidates.extend(_candidates_from_field(field, "report_homepage"))
    for row in report_doc.sample_description_rows:
        candidates.extend(_candidates_from_field(row.model, "sample_description"))
    for component in report_doc.sample_components:
        for value in _model_values(component.model):
            candidates.append(
                ReportModelCandidate(
                    value=value,
                    source="sample_description",
                    page=component.row_location.page_number if component.row_location else None,
                    confidence="medium",
                )
            )
    for field in report_doc.fields:
        candidates.extend(_candidates_from_field(field, _field_source(field)))
    if report_doc.third_page is not None:
        candidates.extend(_candidates_from_field(report_doc.third_page.model_spec, "model_specification"))
        for field in report_doc.third_page.fields:
            candidates.extend(_candidates_from_field(field, "model_specification"))

    deduped = _dedupe_candidates(candidates)
    unique_values = _unique(candidate.value for candidate in deduped)
    diagnostics: list[str] = []
    primary_model = unique_values[0] if len(unique_values) == 1 else None
    if not unique_values:
        diagnostics.append("model_not_found")
    elif len(unique_values) > 1:
        diagnostics.append("multiple_model_candidates")
    return ReportModelContext(
        primary_model=primary_model,
        model_candidates=deduped,
        diagnostics=diagnostics,
    )


def coerce_report_model_context(value: Any) -> ReportModelContext:
    if isinstance(value, ReportModelContext):
        return value
    if isinstance(value, dict):
        return ReportModelContext.model_validate(value)
    return ReportModelContext()


def _candidates_from_field(field: ReportField | None, source: str) -> list[ReportModelCandidate]:
    if field is None or not _is_model_field(field):
        return []
    page = field.location.page_number if field.location else None
    confidence = _confidence_value(field.confidence)
    return [
        ReportModelCandidate(value=value, source=source, page=page, confidence=confidence)
        for value in _model_values(field.normalized_value or field.value or field.raw_value)
    ]


def _is_model_field(field: ReportField) -> bool:
    name_text = _compact(" ".join([field.name, *field.aliases]))
    if any(token in name_text for token in ("型号规格", "规格型号", "型号", "model", "modelspec")):
        return True
    metadata = " ".join(str(value or "") for value in field.metadata.values())
    return "型号" in metadata or "model" in metadata.lower()


def _field_source(field: ReportField) -> str:
    name_text = _compact(field.name)
    if "样品" in name_text:
        return "sample_description"
    if "首页" in str(field.metadata.get("source") or ""):
        return "report_homepage"
    return "model_specification"


def _model_values(value: str | None) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    if _looks_like_reference_to_sample_description(text):
        return []
    text = re.sub(r"^(?:型号规格|规格型号|型号|model(?:\s*spec(?:ification)?)?)\s*[:：]?", "", text, flags=re.IGNORECASE)
    parts = re.split(r"[、,，;/；\n]+", text)
    values: list[str] = []
    for part in parts:
        cleaned = _clean_model_value(part)
        if cleaned:
            values.append(cleaned)
    return _unique(values)


def _clean_model_value(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip("：:（）()[]【】")
    if not text or text in {"/", "／", "-", "—", "——", "无", "不适用"}:
        return ""
    if _looks_like_reference_to_sample_description(text):
        return ""
    if not re.search(r"[A-Za-z0-9]", text):
        return ""
    return text


def _looks_like_reference_to_sample_description(value: str) -> bool:
    compact = _compact(value)
    return "见样品描述" in compact or "见样品" in compact


def _confidence_value(value: Confidence | str | None) -> str:
    if value is None:
        return "medium"
    text = value.value if isinstance(value, Confidence) else str(value)
    return text if text in {"high", "medium", "low"} else "medium"


def _dedupe_candidates(candidates: list[ReportModelCandidate]) -> list[ReportModelCandidate]:
    best_by_value: dict[str, ReportModelCandidate] = {}
    order: list[str] = []
    priority = {"report_homepage": 0, "sample_description": 1, "model_specification": 2}
    confidence_priority = {"high": 0, "medium": 1, "low": 2}
    for candidate in candidates:
        key = candidate.value
        if key not in best_by_value:
            best_by_value[key] = candidate
            order.append(key)
            continue
        current = best_by_value[key]
        if (
            priority.get(candidate.source, 9),
            confidence_priority.get(candidate.confidence, 9),
            candidate.page or 10**9,
        ) < (
            priority.get(current.source, 9),
            confidence_priority.get(current.confidence, 9),
            current.page or 10**9,
        ):
            best_by_value[key] = candidate
    return [best_by_value[key] for key in order]


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


__all__ = [
    "ReportModelCandidate",
    "ReportModelContext",
    "build_report_model_context",
    "coerce_report_model_context",
]
