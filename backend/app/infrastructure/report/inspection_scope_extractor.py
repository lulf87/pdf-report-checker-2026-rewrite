from __future__ import annotations

import re

from app.domain.report import ReportDocument, ReportField
from app.domain.report_scope import ExternalStandardRange, ReportInspectionScope, ReportScopeRange


SCOPE_RANGE_RE = re.compile(r"(\d+(?:\.\d+)*)\s*(?:[~～\-]|至|到)\s*(\d+(?:\.\d+)*)")
SCOPE_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")
EXCLUSION_PATTERNS = (
    re.compile(r"除([^）)。；;]+)"),
    re.compile(r"(?:不包括|不含|不检|排除)([^）)。；;]+)"),
)
EXTERNAL_RANGE_RE = re.compile(
    r"序号\s*(\d+)\s*(?:[~～\-]|至|到)\s*(?:序号\s*)?(\d+)\s*为\s*((?:GB/T|GB|YY/T|YY)\s*\d+(?:\s*\.\s*\d+)*(?:\s*-\s*\d{4})?)",
    re.IGNORECASE,
)


class ReportInspectionScopeExtractor:
    """Extract the report-declared inspection scope used by PTR comparison."""

    def extract(self, report: ReportDocument) -> ReportInspectionScope:
        scope_field = _first_scope_field(report)
        source_text = _field_text(scope_field) if scope_field is not None else None
        declared_items, declared_ranges = _parse_declared_scope(source_text or "")
        excluded_topics = _parse_excluded_topics(source_text or "")
        external_ranges = _parse_external_standard_ranges(report)

        return ReportInspectionScope(
            declared_scope_items=declared_items,
            declared_scope_ranges=declared_ranges,
            excluded_topics=excluded_topics,
            source_page=scope_field.location.page_number if scope_field and scope_field.location else None,
            source_text=source_text,
            external_standard_ranges=external_ranges,
            ptr_direct_content_starts_after=_max_end_item_no(external_ranges),
        )


def _first_scope_field(report: ReportDocument) -> ReportField | None:
    fields: list[ReportField] = []
    if report.third_page is not None:
        fields.extend(report.third_page.fields)
    fields.extend(report.fields)
    for field in fields:
        if field.name == "检验项目" and _field_text(field):
            return field
    return None


def _field_text(field: ReportField | None) -> str | None:
    if field is None:
        return None
    value = field.value or field.normalized_value or field.raw_value
    if value and value.strip():
        return value.strip()
    items = field.metadata.get("items")
    if isinstance(items, list):
        text = "、".join(str(item).strip() for item in items if str(item or "").strip())
        return text or None
    return None


def _parse_declared_scope(text: str) -> tuple[list[str], list[ReportScopeRange]]:
    normalized = _without_exclusion_text(re.sub(r"\s+", "", text or ""))
    declared_items: list[str] = []
    declared_ranges: list[ReportScopeRange] = []
    range_tokens: set[str] = set()

    for match in SCOPE_RANGE_RE.finditer(normalized):
        start, end = match.group(1), match.group(2)
        declared_ranges.append(ReportScopeRange(start=start, end=end, source_text=text))
        range_tokens.add(start)
        range_tokens.add(end)

    for token in SCOPE_NUMBER_RE.findall(normalized):
        if token in range_tokens:
            continue
        if token not in declared_items:
            declared_items.append(token)

    return declared_items, declared_ranges


def _without_exclusion_text(text: str) -> str:
    value = text
    for pattern in EXCLUSION_PATTERNS:
        value = pattern.sub("", value)
    return value


def _parse_excluded_topics(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text or "")
    topics: list[str] = []
    seen: set[str] = set()
    for pattern in EXCLUSION_PATTERNS:
        for match in pattern.finditer(normalized):
            for topic in re.split(r"[、，,；;/及和]", match.group(1)):
                clean = topic.strip("()（）")
                if clean and clean not in seen:
                    seen.add(clean)
                    topics.append(clean)
    return topics


def _parse_external_standard_ranges(report: ReportDocument) -> list[ExternalStandardRange]:
    if report.parsed_pdf is None:
        return []
    ranges: list[ExternalStandardRange] = []
    for page in report.parsed_pdf.pages:
        page_text = _normalize_page_text(page.text)
        for match in EXTERNAL_RANGE_RE.finditer(page_text):
            ranges.append(
                ExternalStandardRange(
                    start_item_no=match.group(1),
                    end_item_no=match.group(2),
                    standard=_normalize_standard(match.group(3)),
                    source_page=page.page_number,
                    source_text=_external_range_source_text(page_text, match),
                )
            )
    return ranges


def _normalize_page_text(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return _normalize_standard_punctuation(value)


def _normalize_standard(value: str) -> str:
    return _normalize_standard_punctuation(re.sub(r"\s+", " ", value or "").strip())


def _normalize_standard_punctuation(value: str) -> str:
    value = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", value)
    value = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", value)
    return value


def _external_range_source_text(page_text: str, match: re.Match[str]) -> str:
    next_match = re.search(r"\s+序号\s*\d+", page_text[match.end() :])
    end = match.end() + next_match.start() if next_match else len(page_text)
    return page_text[match.start() : end].strip()


def _max_end_item_no(ranges: list[ExternalStandardRange]) -> str | None:
    if not ranges:
        return None
    numeric_ranges = [(int(item.end_item_no), item.end_item_no) for item in ranges if item.end_item_no.isdigit()]
    if numeric_ranges:
        return max(numeric_ranges)[1]
    return ranges[-1].end_item_no


__all__ = ["ReportInspectionScopeExtractor"]
