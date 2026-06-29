from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import LabelOCRResult, PhotoCaption, ReportDocument, SampleComponent
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.c05_photo_coverage import extract_photo_caption_subject, match_photo_subject
from app.rules.report.common import (
    component_field_value,
    component_is_supporting_equipment,
    component_not_used,
    evidence_for_component,
    evidence_for_label,
    get_label_field,
    get_label_value,
    is_no_value,
    make_result,
)
from app.rules.report.context import CheckContext


CHECK_ID = "C06"
CHECK_NAME = "中文标签覆盖"

_KEY_FIELDS = ("部件名称", "规格型号", "序列号批号", "生产日期", "失效日期")
_IDENTITY_FIELDS = ("规格型号", "序列号批号", "生产日期", "失效日期")
_LABEL_KEYWORDS = ("中文标签样张", "中文标签", "标签样张", "标签")
_LABEL_SUBJECT_WORDS = ("中文标签样张", "中文标签", "标签样张", "包装标签", "标签", "铭牌", "标牌")
_DIRECTION_WORDS = (
    "前侧",
    "后侧",
    "左侧",
    "右侧",
    "上侧",
    "下侧",
    "正面",
    "背面",
    "侧面",
    "前面",
    "后面",
)


@dataclass(frozen=True)
class _LabelCandidate:
    label_id: str
    caption_text: str
    subject_name: str
    page_number: int | None
    label: LabelOCRResult | None = None
    caption: PhotoCaption | None = None
    confidence: str | None = None

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence == Confidence.LOW.value


@dataclass(frozen=True)
class _LabelMatch:
    candidate: _LabelCandidate
    strategy: str


def build_component_key(component: SampleComponent) -> dict[str, str]:
    values = {
        "部件名称": component.component_name,
        "规格型号": component.model,
        "序列号批号": component.batch_or_serial,
        "生产日期": component.production_date,
        "失效日期": component.expiration_date,
    }
    return {field_name: value for field_name, value in values.items() if not is_no_value(value)}


def check_c06_label_coverage(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    findings: list[Finding] = []
    coverage: list[dict[str, Any]] = []
    candidates = _label_candidates(document)
    active_components: list[SampleComponent] = []
    name_counts = _component_name_counts(document.sample_components)

    for component in document.sample_components:
        if component_not_used(component):
            coverage.append(
                _coverage_record(component, None, "unused_component_skipped", is_unused_component=True)
            )
            continue
        if component_is_supporting_equipment(component):
            coverage.append(
                _coverage_record(component, None, "supporting_equipment_skipped", is_unused_component=False)
            )
            continue
        active_components.append(component)

    used_candidate_ids: set[str] = set()
    for component in active_components:
        require_identity = name_counts.get(component.component_name or "", 0) > 1
        match = _find_label(component, candidates, used_candidate_ids, require_identity=require_identity)
        if match is None:
            findings.append(_missing_label_finding(context, component, candidates))
            coverage.append(_coverage_record(component, None, None, is_unused_component=False))
            continue

        candidate = match.candidate
        used_candidate_ids.add(candidate.label_id)
        coverage.append(_coverage_record(component, candidate, match.strategy, is_unused_component=False))
        if candidate.is_low_confidence:
            findings.append(_uncertain_label_finding(context, component, match))

    if not active_components:
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=findings,
            metadata={"coverage": coverage},
            pass_summary="无需要中文标签覆盖的样品部件",
            empty_status=CheckStatus.SKIP,
        )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={"coverage": coverage},
        pass_summary="样品描述部件均有对应中文标签",
        issue_summary=f"中文标签覆盖存在 {len(findings)} 项缺失或需复核",
    )


def _label_candidates(document: ReportDocument) -> list[_LabelCandidate]:
    candidates: list[_LabelCandidate] = []
    for label in document.labels:
        caption_text = label.caption_text or ""
        if not _is_label_caption(caption_text):
            continue
        candidates.append(
            _LabelCandidate(
                label_id=label.label_id,
                caption_text=caption_text,
                subject_name=extract_label_caption_subject(caption_text),
                page_number=label.page_number,
                label=label,
                confidence=_confidence_value(label),
            )
        )

    for caption in document.photo_captions:
        if not _is_label_caption(caption.text):
            continue
        candidates.append(
            _LabelCandidate(
                label_id=f"caption:{caption.caption_id}",
                caption_text=caption.text,
                subject_name=extract_label_caption_subject(caption.subject_name or caption.text),
                page_number=caption.page_number,
                caption=caption,
                confidence=_caption_confidence(caption),
            )
        )
    return candidates


def extract_label_caption_subject(caption_text: str) -> str:
    subject = extract_photo_caption_subject(caption_text)
    subject = _strip_label_prefix(subject)
    subject = _strip_suffix_words(subject, _LABEL_SUBJECT_WORDS)
    subject = _strip_suffix_words(subject, _DIRECTION_WORDS)
    subject = _strip_suffix_words(subject, _LABEL_SUBJECT_WORDS)
    return subject


def _find_label(
    component: SampleComponent,
    candidates: list[_LabelCandidate],
    used_candidate_ids: set[str],
    *,
    require_identity: bool,
) -> _LabelMatch | None:
    scored_matches: list[tuple[tuple[int, int, int, int], _LabelCandidate, str]] = []
    for candidate in candidates:
        if candidate.label_id in used_candidate_ids:
            continue
        score, strategy = _score_label(component, candidate, require_identity=require_identity)
        if score is None:
            continue
        scored_matches.append((score, candidate, strategy))

    if not scored_matches:
        return None
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    _, candidate, strategy = scored_matches[0]
    return _LabelMatch(candidate=candidate, strategy=strategy)


def _score_label(
    component: SampleComponent,
    candidate: _LabelCandidate,
    *,
    require_identity: bool,
) -> tuple[tuple[int, int, int, int] | None, str]:
    label_key = _label_key(candidate)
    identity_matches = 0
    identity_mismatches = 0
    comparable = 0

    for field_name in _IDENTITY_FIELDS:
        component_value = component_field_value(component, field_name)
        if is_no_value(component_value):
            continue
        label_value = label_key.get(field_name)
        if is_no_value(label_value):
            continue
        comparable += 1
        if _values_match(component_value, label_value):
            identity_matches += 1
        else:
            identity_mismatches += 1

    if identity_mismatches:
        return None, "identity_mismatch"

    caption_match = match_photo_subject(component.component_name, candidate.subject_name)
    label_name_match = match_photo_subject(component.component_name, label_key.get("部件名称"))
    if label_name_match == "exact" or caption_match == "exact":
        name_score = 2
    elif label_name_match or caption_match:
        name_score = 1
    else:
        name_score = 0

    if identity_matches:
        return (identity_matches, 0, name_score, comparable), "identity"
    if require_identity and _component_has_identity_fields(component):
        return None, "component_key_not_matched"
    if caption_match:
        return (0, 0, name_score, comparable), "caption_subject"
    if label_name_match:
        return (0, 0, name_score, comparable), "label_name"
    return None, "unmatched"


def _label_key(candidate: _LabelCandidate) -> dict[str, str]:
    if candidate.label is None:
        values = {
            "部件名称": candidate.subject_name,
            "规格型号": None,
            "序列号批号": None,
            "生产日期": None,
            "失效日期": None,
        }
    else:
        values = {
            "部件名称": get_label_value(candidate.label, "部件名称")
            or get_label_value(candidate.label, "样品名称")
            or candidate.subject_name,
            "规格型号": get_label_value(candidate.label, "规格型号"),
            "序列号批号": get_label_value(candidate.label, "序列号批号"),
            "生产日期": get_label_value(candidate.label, "生产日期"),
            "失效日期": get_label_value(candidate.label, "失效日期"),
        }
    return {field_name: value for field_name, value in values.items() if not is_no_value(value)}


def _component_has_identity_fields(component: SampleComponent) -> bool:
    return any(not is_no_value(component_field_value(component, field_name)) for field_name in _IDENTITY_FIELDS)


def _missing_label_finding(
    context: CheckContext,
    component: SampleComponent,
    candidates: list[_LabelCandidate],
) -> Finding:
    code = "LABEL_COMPONENT_KEY_NOT_MATCHED" if candidates else "LABEL_COVERAGE_MISSING"
    message = (
        f"样品描述部件「{component.component_name or component.component_id}」存在中文标签候选，"
        "但非空字段联合键未匹配"
        if candidates
        else f"样品描述部件「{component.component_name or component.component_id}」缺少对应中文标签"
    )
    return Finding(
        id=f"{context.task_id}-c06-{component.component_id}-label-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        location=component.row_location,
        expected="至少一张中文标签",
        actual="未匹配到中文标签",
        evidence=[
            *evidence_for_component(component),
            *[item for candidate in candidates for item in _candidate_evidence(candidate)],
        ],
        missing_evidence=[
            MissingEvidence(
                label=f"{component.component_name or component.component_id} 中文标签",
                reason="未找到可匹配该部件非空字段联合键的中文标签",
                expected_source=SourceType.REPORT,
                location=component.row_location,
            )
        ],
        confidence=Confidence.HIGH,
        metadata={
            **_component_metadata(component),
            "matched_label_key": None,
            "matching_strategy": None,
            "is_unused_component": False,
            "candidate_labels": [_candidate_metadata(candidate) for candidate in candidates],
        },
    )


def _uncertain_label_finding(context: CheckContext, component: SampleComponent, match: _LabelMatch) -> Finding:
    candidate = match.candidate
    return Finding(
        id=f"{context.task_id}-c06-{component.component_id}-{candidate.label_id}-label-uncertain",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code="LABEL_CAPTION_UNCERTAIN",
        message=f"部件「{component.component_name or component.component_id}」的中文标签 OCR 置信度低，需人工复核",
        location=Location(source_type=SourceType.REPORT, page_number=candidate.page_number, section="中文标签页"),
        expected="可靠可解析的中文标签",
        actual=candidate.caption_text,
        evidence=[*evidence_for_component(component), *_candidate_evidence(candidate)],
        confidence=Confidence.MEDIUM,
        metadata={
            **_component_metadata(component),
            "matched_label_key": candidate.label_id,
            "matching_strategy": match.strategy,
            "is_unused_component": False,
            "ocr_confidence": candidate.confidence,
            "label_caption": candidate.caption_text,
        },
    )


def _coverage_record(
    component: SampleComponent,
    candidate: _LabelCandidate | None,
    matching_strategy: str | None,
    *,
    is_unused_component: bool,
) -> dict[str, Any]:
    return {
        **_component_metadata(component),
        "component_id": component.component_id,
        "matched_label_key": candidate.label_id if candidate else None,
        "label_id": candidate.label_id if candidate else None,
        "label_caption": candidate.caption_text if candidate else None,
        "matching_strategy": matching_strategy,
        "is_unused_component": is_unused_component,
    }


def _component_metadata(component: SampleComponent) -> dict[str, Any]:
    return {
        "component_id": component.component_id,
        "component_name": component.component_name,
        "component_key": build_component_key(component),
        "sample_role": component.metadata.get("sample_role", "main_sample"),
        "supporting_equipment": component_is_supporting_equipment(component),
    }


def _candidate_metadata(candidate: _LabelCandidate) -> dict[str, Any]:
    return {
        "matched_label_key": candidate.label_id,
        "label_caption": candidate.caption_text,
        "label_subject": candidate.subject_name,
        "label_key": _label_key(candidate),
        "page_number": candidate.page_number,
        "ocr_confidence": candidate.confidence,
    }


def _candidate_evidence(candidate: _LabelCandidate) -> list[Evidence]:
    if candidate.label is not None:
        return evidence_for_label(candidate.label)
    if candidate.caption and candidate.caption.evidence:
        return candidate.caption.evidence
    return [
        Evidence(
            id=f"ev-{candidate.label_id}",
            source_type=SourceType.REPORT,
            location=Location(source_type=SourceType.REPORT, page_number=candidate.page_number),
            raw_text=candidate.caption_text,
            value=candidate.caption_text,
            method=EvidenceMethod.PDF_TEXT,
        )
    ]


def _component_name_counts(components: list[SampleComponent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for component in components:
        if component_not_used(component) or component_is_supporting_equipment(component):
            continue
        name = component.component_name or ""
        counts[name] = counts.get(name, 0) + 1
    return counts


def _is_label_caption(text: str | None) -> bool:
    return any(keyword in (text or "") for keyword in _LABEL_KEYWORDS)


def _strip_label_prefix(text: str) -> str:
    pattern = r"^(?:" + "|".join(re.escape(word) for word in _LABEL_SUBJECT_WORDS) + r")\s*[:：]?"
    return re.sub(pattern, "", text)


def _strip_suffix_words(text: str, words: tuple[str, ...]) -> str:
    changed = True
    while changed:
        changed = False
        for word in words:
            if text.endswith(word) and len(text) > len(word):
                text = text[: -len(word)]
                changed = True
                break
    return text


def _values_match(left: str | None, right: str | None) -> bool:
    return (left or "") == (right or "")


def _confidence_value(label: LabelOCRResult) -> str | None:
    if label.confidence:
        return str(label.confidence)
    for field_name in _KEY_FIELDS:
        field = get_label_field(label, field_name)
        confidence = field.confidence if field else None
        if confidence == Confidence.LOW:
            return Confidence.LOW.value
    return None


def _caption_confidence(caption: PhotoCaption) -> str | None:
    value = caption.metadata.get("ocr_confidence") or caption.metadata.get("confidence")
    if isinstance(value, Confidence):
        return value.value
    if isinstance(value, str):
        return value.lower()
    for item in caption.evidence:
        if item.confidence == Confidence.LOW:
            return Confidence.LOW.value
    return None


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "build_component_key",
    "check_c06_label_coverage",
    "extract_label_caption_subject",
]
