from __future__ import annotations

import re
from typing import Any

from app.domain.finding import Finding
from app.domain.result import CheckResult


_REPORT_CHECK_IDS = {f"C{index:02d}" for index in range(1, 12)}
_MATCH_STATUSES = {"match", "passed"}
_ACTIONABLE_FINAL_STATUSES = {"confirmed", "manual_review_required"}
_FIELD_LABELS = {
    "batch_or_serial": "产品编号/批号",
    "component_name": "部件名称",
    "expiration_date": "使用期限",
    "model": "型号规格",
    "production_date": "生产日期",
    "serial_number": "产品编号/序列号",
}


def attach_final_comparison_details(check_results: list[CheckResult]) -> None:
    """Build final-only, user-facing comparison rows from reviewed evidence."""

    for result in check_results:
        if result.check_id not in _REPORT_CHECK_IDS:
            continue
        details = _build_final_comparison_details(result)
        if details is not None:
            result.metadata["final_comparison_details"] = details


def _build_final_comparison_details(result: CheckResult) -> dict[str, Any] | None:
    base = result.metadata.get("comparison_details")
    base_details = base if isinstance(base, dict) else {}
    base_fields = base_details.get("fields")
    fields = base_fields if isinstance(base_fields, list) else []
    final_fields: list[dict[str, Any]] = []
    seen_rows: set[tuple[str, str, str]] = set()
    finalized_findings = [
        finding
        for finding in result.findings
        if str(finding.metadata.get("final_status") or "")
        in _ACTIONABLE_FINAL_STATUSES | {"refuted"}
    ]
    actionable_findings = [
        finding
        for finding in finalized_findings
        if str(finding.metadata.get("final_status") or "") in _ACTIONABLE_FINAL_STATUSES
    ]
    selected_findings = actionable_findings or finalized_findings

    for finding in selected_findings:
        final_status = str(finding.metadata.get("final_status") or "")
        comparisons = finding.metadata.get("codex_field_comparisons")
        selected = _select_finding_comparisons(
            finding,
            comparisons if isinstance(comparisons, list) else [],
        )
        if final_status == "refuted":
            selected = [
                comparison
                for comparison in selected
                if _text(comparison.get("status")).lower() in _MATCH_STATUSES
            ]
        rows_before_finding = len(final_fields)
        for comparison in selected:
            if not isinstance(comparison, dict):
                continue
            field_name = _text(comparison.get("field_name")) or _text(finding.metadata.get("field_name"))
            base_field = _matching_base_field(fields, field_name)
            row = _final_field_row(
                comparison,
                finding=finding,
                base_field=base_field,
                final_status=final_status,
            )
            row_key = (
                str(row.get("field_key") or ""),
                str((row.get("right") or {}).get("raw_text") or ""),
                str(row.get("status") or ""),
            )
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            final_fields.append(row)
        if len(final_fields) == rows_before_finding:
            fallback_row = _final_finding_row(finding, final_status=final_status)
            row_key = (
                str(fallback_row.get("field_key") or ""),
                str((fallback_row.get("right") or {}).get("raw_text") or ""),
                str(fallback_row.get("status") or ""),
            )
            if row_key not in seen_rows:
                seen_rows.add(row_key)
                final_fields.append(fallback_row)

    if not final_fields:
        return None

    statuses = {str(field.get("status") or "") for field in final_fields}
    if statuses <= {"match", "passed"}:
        overall_status = "passed"
        overall_reason = "结构化摘录与最终证据一致。"
    elif statuses & {"mismatch", "missing", "missing_left", "missing_right"}:
        overall_status = "confirmed_error"
        overall_reason = "最终核验确认存在字段差异。"
    elif statuses & {"needs_review", "unknown"}:
        overall_status = "needs_review"
        overall_reason = "仍有字段无法自动确认，需要人工复核。"
    else:
        overall_status = "needs_review"
        overall_reason = "现有证据不足以形成稳定结论，需要人工复核。"

    return {
        "title": base_details.get("title") or result.check_name,
        "overall_status": overall_status,
        "overall_reason": overall_reason,
        "sources": _comparison_sources(
            _final_sources(base_details.get("sources")),
            final_fields,
        ),
        "fields": final_fields,
    }


def _select_finding_comparisons(
    finding: Finding,
    comparisons: list[Any],
) -> list[dict[str, Any]]:
    valid = [item for item in comparisons if isinstance(item, dict)]
    field_hint = _text(finding.metadata.get("field_name"))
    if not field_hint:
        return valid
    hint_identity = _field_identity(field_hint)
    matching = [
        item
        for item in valid
        if _field_identity(_text(item.get("field_name"))) == hint_identity
    ]
    return matching or valid[:1]


def _matching_base_field(fields: list[Any], field_name: str) -> dict[str, Any]:
    identity = _field_identity(field_name)
    for field in fields:
        if not isinstance(field, dict):
            continue
        candidates = (
            _text(field.get("field_key")),
            _text(field.get("field_label")),
        )
        if any(_field_identity(candidate) == identity for candidate in candidates if candidate):
            return field
    return {}


def _final_field_row(
    comparison: dict[str, Any],
    *,
    finding: Finding,
    base_field: dict[str, Any],
    final_status: str,
) -> dict[str, Any]:
    field_name = _text(comparison.get("field_name")) or _text(finding.metadata.get("field_name"))
    observed_value = comparison.get("observed_value")
    expected_value = comparison.get("expected_value")
    left = _copy_record(base_field.get("left"))
    right = _copy_record(base_field.get("right"))

    if expected_value is not None and not left.get("raw_text"):
        left["raw_text"] = str(expected_value)
        left["normalized_text"] = str(expected_value)
    left.setdefault("source_key", "report_extract")
    left.setdefault("label", "报告摘录")

    right["source_key"] = "visual_evidence"
    right["label"] = _visual_source_label(_text(right.get("label")))
    right["raw_text"] = None if observed_value is None else str(observed_value)
    right["normalized_text"] = None if observed_value is None else str(observed_value)
    _attach_evidence_location(
        left,
        finding=finding,
        value=expected_value,
        excluded_page=None,
        default_label="报告摘录",
    )
    _attach_evidence_location(
        right,
        finding=finding,
        value=observed_value,
        excluded_page=_page_number(left),
        default_label="中文标签图像摘录",
    )

    evidence_ref = _text(comparison.get("evidence_ref"))
    evidence_ids = [evidence_ref] if evidence_ref else list(base_field.get("evidence_ids") or [])
    return {
        "field_key": base_field.get("field_key") or _field_identity(field_name) or "field",
        "field_label": base_field.get("field_label") or _field_label(field_name),
        "status": _final_field_status(_text(comparison.get("status")), final_status),
        "reason": _final_reason(_text(comparison.get("reasoning")), final_status),
        "evidence_ids": evidence_ids,
        "left": left,
        "right": right,
    }


def _final_finding_row(finding: Finding, *, final_status: str) -> dict[str, Any]:
    candidate_records = _selected_candidate_records(finding)
    if final_status == "refuted" and candidate_records:
        expected = _text(finding.metadata.get("component_name")) or _text(finding.expected)
        actual = "；".join(
            _candidate_text(candidate)
            for candidate in candidate_records
            if _candidate_text(candidate)
        )
        pages = _candidate_pages(candidate_records)
        left = {
            "source_key": "report_extract",
            "label": "样品描述摘录",
            "raw_text": expected or None,
            "normalized_text": expected or None,
        }
        right = {
            "source_key": "visual_evidence",
            "label": "照片页摘录",
            "raw_text": actual or None,
            "normalized_text": actual or None,
            "page_number": pages[0] if pages else None,
            "display_page_label": _display_pages(pages),
        }
        _attach_evidence_location(
            left,
            finding=finding,
            value=expected,
            excluded_page=None,
            default_label="样品描述摘录",
        )
        return {
            "field_key": f"{_field_identity(expected) or finding.id}:coverage",
            "field_label": expected or "照片覆盖",
            "status": "match",
            "reason": _final_reason(
                _text(finding.metadata.get("codex_reasoning_summary")),
                final_status,
            ),
            "evidence_ids": [item.id for item in finding.evidence],
            "left": left,
            "right": right,
        }

    expected = finding.expected
    actual = finding.actual
    page_number = finding.location.page_number if finding.location else None
    item_no = _text(finding.metadata.get("display_item_no")) or _text(
        finding.metadata.get("item_no")
    )
    item_name = re.sub(r"\s+", "", _text(finding.metadata.get("item_name")))
    label_parts = [f"序号 {item_no}" if item_no else "", item_name]
    field_label = " ".join(part for part in label_parts if part) or finding.message
    status = (
        "match"
        if final_status == "refuted"
        else "needs_review"
        if final_status == "manual_review_required"
        else "mismatch"
    )
    left = {
        "source_key": "expected",
        "label": "期望",
        "page_number": page_number,
        "display_page_label": _display_page(page_number),
        "raw_text": None if expected is None else str(expected),
        "normalized_text": None if expected is None else str(expected),
    }
    right = {
        "source_key": "report_actual",
        "label": "报告实际",
        "page_number": page_number,
        "display_page_label": _display_page(page_number),
        "raw_text": None if actual is None else str(actual),
        "normalized_text": None if actual is None else str(actual),
    }
    return {
        "field_key": item_no or finding.code or finding.id,
        "field_label": field_label or "核对项目",
        "status": status,
        "reason": _final_reason(
            _text(finding.metadata.get("codex_reasoning_summary")) or finding.message,
            final_status,
        ),
        "evidence_ids": [item.id for item in finding.evidence],
        "left": left,
        "right": right,
    }


def _final_field_status(comparison_status: str, final_status: str) -> str:
    if final_status == "refuted":
        return "match"
    if final_status == "manual_review_required":
        return "needs_review"
    normalized = comparison_status.lower()
    if normalized in {"match", "passed"}:
        return "match"
    if normalized in {"missing", "missing_left", "missing_right"}:
        return "missing"
    if normalized in {"mismatch", "not_match"}:
        return "mismatch"
    return "mismatch" if final_status == "confirmed" else "needs_review"


def _final_field_reason(final_status: str) -> str:
    if final_status == "refuted":
        return "现有证据确认该字段满足要求。"
    if final_status == "confirmed":
        return "最终核验证据确认该字段存在差异。"
    return "该字段仍需人工复核。"


def _final_reason(reason: str, final_status: str) -> str:
    if not reason:
        return _final_field_reason(final_status)
    cleaned = re.sub(r"codex", "自动核验", reason, flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace("候选不一致成立", "该不一致已确认")
    cleaned = cleaned.replace("候选问题", "问题")
    if final_status != "refuted":
        return cleaned

    cleaned = cleaned.replace("候选题注列表中已有", "报告照片页已有")
    for marker in (
        "；“未匹配",
        '；"未匹配',
        "；初判",
        "，不能支持",
        "；不能支持",
        "，与该证据冲突",
        "；与该证据冲突",
    ):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0]
    cleaned = re.sub(r"(候选问题|规则初判|初判|误报)(已)?(被)?排除", "", cleaned)
    return cleaned.strip("；;，,。 ") + "。" if cleaned.strip("；;，,。 ") else _final_field_reason(final_status)


def _final_sources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sources: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = dict(item)
        if source.get("source_key") == "label_ocr":
            source["source_key"] = "visual_evidence"
            source["label"] = _visual_source_label(_text(source.get("label")))
            source["section"] = "中文标签图像"
        sources.append(source)
    return sources


def _comparison_sources(
    base_sources: list[dict[str, Any]],
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources = [dict(source) for source in base_sources]
    seen = {
        (
            _text(source.get("source_key")),
            source.get("page_number"),
            _text(source.get("display_page_label")),
        )
        for source in sources
    }
    for field in fields:
        for side_name in ("left", "right"):
            extract = field.get(side_name)
            if not isinstance(extract, dict):
                continue
            page_number = extract.get("page_number")
            display_page_label = _text(extract.get("display_page_label"))
            if page_number is None and not display_page_label:
                continue
            source = {
                "source_key": extract.get("source_key"),
                "label": extract.get("label"),
                "page_number": page_number,
                "display_page_label": display_page_label or _display_page(page_number),
                "section": None,
            }
            key = (
                _text(source.get("source_key")),
                source.get("page_number"),
                _text(source.get("display_page_label")),
            )
            if key in seen:
                continue
            seen.add(key)
            sources.append(source)
    return sources


def _visual_source_label(value: str) -> str:
    if not value:
        return "中文标签图像摘录"
    label = re.sub(r"\s+", " ", value.replace("OCR", "")).strip()
    label = re.sub(r"\s*摘录", "摘录", label)
    if "摘录" in label:
        return label if "中文标签图像" in label else label.replace("中文标签", "中文标签图像")
    return f"{label}图像摘录" if "标签" in label else "视觉证据摘录"


def _field_label(value: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", value):
        return value
    identity = _field_identity(value)
    return _FIELD_LABELS.get(identity, value or "核对字段")


def _field_identity(value: str) -> str:
    normalized = re.sub(r"[\s_:/／\\（）()\-]+", "", value).lower()
    aliases = {
        "model": "model",
        "modelspec": "model",
        "型号": "model",
        "型号规格": "model",
        "productiondate": "production_date",
        "productiondateformat": "production_date",
        "生产日期": "production_date",
        "生产日期格式": "production_date",
        "batchorserial": "batch_or_serial",
        "serialnumber": "batch_or_serial",
        "产品编号批号": "batch_or_serial",
        "序列号批号": "batch_or_serial",
        "componentname": "component_name",
        "部件名称": "component_name",
        "expirationdate": "expiration_date",
        "使用期限": "expiration_date",
    }
    return aliases.get(normalized, normalized)


def _attach_evidence_location(
    extract: dict[str, Any],
    *,
    finding: Finding,
    value: Any,
    excluded_page: int | None,
    default_label: str,
) -> None:
    if extract.get("page_number") is not None or extract.get("display_page_label"):
        return
    evidence = _best_evidence(finding, value=value, excluded_page=excluded_page)
    if evidence is None:
        return
    page_number = evidence.location.page_number if evidence.location else None
    if page_number is None:
        return
    extract["page_number"] = page_number
    extract["display_page_label"] = _display_page(page_number)
    extract.setdefault("label", default_label)


def _best_evidence(
    finding: Finding,
    *,
    value: Any,
    excluded_page: int | None,
) -> Any | None:
    wanted = _compact(_text(value))
    candidates: list[tuple[int, int, Any]] = []
    for index, evidence in enumerate(finding.evidence):
        page_number = evidence.location.page_number if evidence.location else None
        if excluded_page is not None and page_number == excluded_page:
            continue
        text_value = _compact(
            " ".join(
                part
                for part in (
                    _text(evidence.raw_text),
                    _text(evidence.normalized_text),
                    _text(evidence.value),
                )
                if part
            )
        )
        score = 0
        if wanted and text_value == wanted:
            score = 4
        elif wanted and wanted in text_value:
            score = 3
        elif wanted and text_value and text_value in wanted:
            score = 2
        elif page_number is not None:
            score = 1
        candidates.append((score, -index, evidence))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _selected_candidate_records(finding: Finding) -> list[dict[str, Any]]:
    raw_records = finding.metadata.get("candidate_captions")
    if not isinstance(raw_records, list):
        raw_records = finding.metadata.get("candidate_labels")
    records = [record for record in raw_records or [] if isinstance(record, dict)]
    if not records:
        return []

    reasoning = _compact(_text(finding.metadata.get("codex_reasoning_summary")))
    explicit = [
        record
        for record in records
        if any(
            candidate and candidate in reasoning
            for candidate in (
                _compact(_candidate_text(record)),
                _compact(_candidate_subject(record)),
            )
        )
    ]
    if explicit:
        return explicit

    component_parts = [
        _compact(part)
        for part in re.split(
            r"[、，,；;]|(?:以及)|(?:及)|(?:和)|(?:与)",
            _text(finding.metadata.get("component_name")),
        )
        if _compact(part)
    ]
    semantic_matches = [
        record
        for record in records
        if any(
            subject and (subject in part or part in subject)
            for part in component_parts
            for subject in (_compact(_candidate_subject(record)),)
        )
    ]
    return semantic_matches[:6]


def _candidate_text(record: dict[str, Any]) -> str:
    return (
        _text(record.get("caption_text"))
        or _text(record.get("label_caption"))
        or _text(record.get("caption_subject"))
        or _text(record.get("label_subject"))
    )


def _candidate_subject(record: dict[str, Any]) -> str:
    return _text(record.get("caption_subject")) or _text(record.get("label_subject"))


def _candidate_pages(records: list[dict[str, Any]]) -> list[int]:
    return sorted(
        {
            page
            for record in records
            for page in (record.get("page_number"),)
            if isinstance(page, int)
        }
    )


def _page_number(extract: dict[str, Any]) -> int | None:
    value = extract.get("page_number")
    return value if isinstance(value, int) else None


def _display_page(page_number: Any) -> str | None:
    return f"PDF 第 {page_number} 页" if isinstance(page_number, int) else None


def _display_pages(page_numbers: list[int]) -> str | None:
    if not page_numbers:
        return None
    return f"PDF 第 {'、'.join(str(page) for page in page_numbers)} 页"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def _copy_record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


__all__ = ["attach_final_comparison_details"]
