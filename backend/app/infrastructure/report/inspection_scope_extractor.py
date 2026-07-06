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
        source_text = _best_scope_source_text(report, scope_field)
        declared_items, declared_ranges = _parse_declared_scope(source_text or "")
        scope_modifiers, clause_exclusions = _parse_clause_parentheticals(source_text or "")
        excluded_topics = _parse_excluded_topics(source_text or "")
        external_ranges = _parse_external_standard_ranges(report)

        return ReportInspectionScope(
            declared_scope_items=declared_items,
            declared_scope_ranges=declared_ranges,
            scope_modifiers=scope_modifiers,
            clause_exclusions=clause_exclusions,
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


def _best_scope_source_text(report: ReportDocument, scope_field: ReportField | None) -> str | None:
    field_text = _field_text(scope_field)
    page_text = _scope_text_from_page(report, scope_field)
    if _is_more_complete_scope_text(page_text, field_text):
        return page_text
    return field_text


def _scope_text_from_page(report: ReportDocument, scope_field: ReportField | None) -> str | None:
    if report.parsed_pdf is None:
        return None
    page_number = scope_field.location.page_number if scope_field and scope_field.location else None
    pages = [page for page in report.parsed_pdf.pages if page_number is None or page.page_number == page_number]
    for page in pages:
        text = str(page.text or "")
        match = re.search(r"检\s*验\s*项\s*目", text)
        if not match:
            continue
        rest = text[match.end() :]
        end_match = re.search(r"\n\s*检\s*验\s*依\s*据|\n\s*检\s*验\s*结\s*论|\n\s*备\s*注", rest)
        snippet = rest[: end_match.start()] if end_match else rest[:500]
        normalized = re.sub(r"\s+", " ", snippet).strip(" ：:;；")
        if normalized:
            return normalized
    return None


def _is_more_complete_scope_text(candidate: str | None, current: str | None) -> bool:
    candidate_text = str(candidate or "").strip()
    current_text = str(current or "").strip()
    if not candidate_text:
        return False
    if not current_text:
        return True
    if len(candidate_text) <= len(current_text):
        return False
    if "（除" in current_text and "）" not in current_text and "）" in candidate_text:
        return True
    candidate_numbers = set(SCOPE_NUMBER_RE.findall(candidate_text))
    current_numbers = set(SCOPE_NUMBER_RE.findall(current_text))
    return bool(current_numbers and current_numbers <= candidate_numbers and len(candidate_text) > len(current_text) + 10)


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
    topics: list[str] = []
    seen: set[str] = set()
    for pattern in EXCLUSION_PATTERNS:
        for match in pattern.finditer(text or ""):
            for topic in _split_scope_topics(match.group(1)):
                clean = _normalize_scope_topic(topic)
                if clean and clean not in seen:
                    seen.add(clean)
                    topics.append(clean)
    return topics


def _parse_clause_parentheticals(text: str) -> tuple[list[dict], list[dict]]:
    modifiers: list[dict] = []
    exclusions: list[dict] = []
    for match in re.finditer(r"(2(?:\.\d+)+)\s*（([^）]*)）", text or ""):
        clause = match.group(1)
        content = _normalize_scope_topic(match.group(2))
        compact = re.sub(r"\s+", "", content)
        if compact.startswith("仅检"):
            topic = _normalize_scope_topic(re.sub(r"^\s*仅\s*检\s*", "", content))
            only = _only_scope_terms(topic)
            if only:
                modifiers.append({"clause": clause, "only": only, "source_text": content})
        elif compact.startswith("除"):
            raw_topics = re.sub(r"^\s*除\s*", "", content)
            topics = [_normalize_scope_topic(topic) for topic in _split_scope_topics(raw_topics)]
            topics = [topic for topic in topics if topic]
            if topics:
                exclusions.append({"clause": clause, "excluded_topics": topics, "source_text": content})
    return modifiers, exclusions


def _split_scope_topics(value: str) -> list[str]:
    return [topic for topic in re.split(r"[、，,；;]", value or "") if topic.strip()]


def _normalize_scope_topic(value: str) -> str:
    text = str(value or "").strip("()（） \t\r\n")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\bGB\s+(\d)", r"GB \1", text, flags=re.IGNORECASE)
    return text.strip()


def _only_scope_terms(topic: str) -> list[str]:
    if not topic:
        return []
    terms = [_normalize_scope_topic(item) for item in _split_scope_topics(topic)]
    result: list[str] = []
    for term in terms:
        if term and term not in result:
            result.append(term)
        if re.search(r"\bPVC\b", term, flags=re.IGNORECASE) and "反应" in term and "PVC Response" not in result:
            result.append("PVC Response")
    return result


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
