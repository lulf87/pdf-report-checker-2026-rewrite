from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import PhotoCaption, ReportDocument, SampleComponent
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.common import (
    component_is_supporting_equipment,
    component_not_used,
    evidence_for_component,
    make_result,
)
from app.rules.report.context import CheckContext


CHECK_ID = "C05"
CHECK_NAME = "照片覆盖"

_CAPTION_PREFIX_PATTERN = re.compile(
    r"^\s*(?:图|№|No\.?|NO\.?|Number|Photo|Plate|Fig\.?)\s*\d+\s*[:：、.\-]?\s*",
    re.IGNORECASE,
)
_PLAIN_NUMBER_PREFIX_PATTERN = re.compile(r"^\s*\d+\s*[:：、.\-]\s*")
_PHOTO_CATEGORY_WORDS = (
    "外观照片",
    "样品照片",
    "产品照片",
    "照片",
    "图片",
    "外观",
)
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
    "局部",
    "整体",
)
_LABEL_CAPTION_WORDS = (
    "中文标签样张",
    "中文标签",
    "标签样张",
    "包装标签",
    "英文标签",
    "标签",
    "铭牌",
    "标牌",
)
_COMPONENT_IN_SUBJECT_CONNECTORS = frozenset({"及", "和", "与", "-", "（", "(", "<", "《"})
_SUBJECT_IN_COMPONENT_CONNECTORS = frozenset({"-", "（", "(", "<", "《"})


@dataclass(frozen=True)
class _CaptionCandidate:
    caption: PhotoCaption
    subject_name: str
    is_uncertain: bool
    uncertainty_reason: str | None
    ocr_confidence: str | None


def extract_photo_caption_subject(caption_text: str) -> str:
    text = _compact(caption_text)
    text = _CAPTION_PREFIX_PATTERN.sub("", text)
    text = _PLAIN_NUMBER_PREFIX_PATTERN.sub("", text)
    text = _strip_suffix_words(text, _PHOTO_CATEGORY_WORDS)
    text = _strip_suffix_words(text, _DIRECTION_WORDS)
    text = _strip_suffix_words(text, _PHOTO_CATEGORY_WORDS)
    return text


def match_photo_subject(component_name: str | None, subject_name: str | None) -> str | None:
    component = extract_photo_caption_subject(component_name or "")
    subject = extract_photo_caption_subject(subject_name or "")
    if not component or not subject:
        return None
    if component == subject:
        return "exact"
    if subject.startswith(component):
        next_char = _following_char(subject, component)
        if next_char in _COMPONENT_IN_SUBJECT_CONNECTORS:
            return "component_in_subject_allowed_connector"
    if component.startswith(subject):
        next_char = _following_char(component, subject)
        if next_char in _SUBJECT_IN_COMPONENT_CONNECTORS:
            return "subject_in_component_allowed_connector"
    return None


def check_c05_photo_coverage(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    findings: list[Finding] = []
    coverage: list[dict[str, Any]] = []
    active_components: list[SampleComponent] = []
    photo_candidates = [
        _caption_candidate(caption)
        for caption in document.photo_captions
        if _is_photo_caption(caption)
    ]

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

    for component in active_components:
        match = _find_caption(component, photo_candidates)
        if match is None:
            uncertain_candidates = [candidate for candidate in photo_candidates if candidate.is_uncertain]
            if uncertain_candidates:
                findings.append(_caption_uncertain_finding(context, component, uncertain_candidates[0], []))
            findings.append(
                Finding(
                    id=f"{context.task_id}-c05-{component.component_id}-photo-missing",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code="PHOTO_COVERAGE_MISSING",
                    message=f"样品描述部件「{component.component_name or component.component_id}」缺少对应照片",
                    location=component.row_location,
                    expected="至少一张照片",
                    actual="未匹配到照片",
                    evidence=[
                        *evidence_for_component(component),
                        *[item for candidate in uncertain_candidates for item in _caption_evidence(candidate.caption)],
                    ],
                    missing_evidence=[
                        MissingEvidence(
                            label=f"{component.component_name or component.component_id} 照片",
                            reason="未找到非中文标签类型的照片题注匹配该部件",
                            expected_source=SourceType.REPORT,
                            location=component.row_location,
                        )
                    ],
                    confidence=Confidence.HIGH,
                    metadata={
                        **_component_metadata(component),
                        "matched_captions": [],
                        "matching_strategy": None,
                        "is_unused_component": False,
                        "candidate_captions": [_candidate_metadata(candidate) for candidate in photo_candidates],
                    },
                )
            )
            coverage.append(_coverage_record(component, None, None, is_unused_component=False))
            continue

        candidate, matching_strategy = match
        coverage.append(_coverage_record(component, candidate, matching_strategy, is_unused_component=False))
        if candidate.is_uncertain:
            findings.append(_caption_uncertain_finding(context, component, candidate, [candidate.caption.text]))

    if not active_components:
        return make_result(
            context=context,
            check_id=CHECK_ID,
            check_name=CHECK_NAME,
            findings=findings,
            metadata={"coverage": coverage},
            pass_summary="无需要照片覆盖的样品部件",
            empty_status=CheckStatus.SKIP,
        )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={"coverage": coverage},
        pass_summary="样品描述部件均有对应照片",
        issue_summary=f"照片覆盖存在 {len(findings)} 项缺失",
    )


def _is_photo_caption(caption: PhotoCaption) -> bool:
    caption_type = (caption.caption_type or "").lower()
    if caption_type in {"chinese_label", "label", "ocr_label"}:
        return False
    if any(keyword in caption.text for keyword in _LABEL_CAPTION_WORDS):
        return False
    return True


def _find_caption(component: SampleComponent, captions: list[_CaptionCandidate]) -> tuple[_CaptionCandidate, str] | None:
    for candidate in captions:
        match_type = match_photo_subject(component.component_name, candidate.subject_name)
        if match_type:
            return candidate, match_type
    return None


def _caption_evidence(caption: PhotoCaption) -> list[Evidence]:
    if caption.evidence:
        return caption.evidence
    return [
        Evidence(
            id=f"ev-caption-{caption.caption_id}",
            source_type=SourceType.REPORT,
            location=Location(source_type=SourceType.REPORT, page_number=caption.page_number),
            raw_text=caption.text,
            value=caption.text,
            method=EvidenceMethod.PDF_TEXT,
        )
    ]


def _caption_candidate(caption: PhotoCaption) -> _CaptionCandidate:
    subject = extract_photo_caption_subject(caption.subject_name or caption.text)
    confidence = _caption_confidence(caption)
    no_subject = not subject
    low_confidence = confidence == Confidence.LOW.value
    reason = None
    if no_subject:
        reason = "caption_subject_missing"
    elif low_confidence:
        reason = "caption_low_confidence"
    elif caption.metadata.get("subject_uncertain"):
        reason = "caption_subject_uncertain"
    return _CaptionCandidate(
        caption=caption,
        subject_name=subject,
        is_uncertain=reason is not None,
        uncertainty_reason=reason,
        ocr_confidence=confidence,
    )


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


def _caption_uncertain_finding(
    context: CheckContext,
    component: SampleComponent,
    candidate: _CaptionCandidate,
    matched_captions: list[str],
) -> Finding:
    return Finding(
        id=f"{context.task_id}-c05-{component.component_id}-{candidate.caption.caption_id}-caption-uncertain",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.WARN,
        code="PHOTO_CAPTION_UNCERTAIN",
        message=(
            f"部件「{component.component_name or component.component_id}」的照片 caption "
            "置信度或主体名不可靠，需人工复核"
        ),
        location=Location(source_type=SourceType.REPORT, page_number=candidate.caption.page_number, section="照片页"),
        expected="可靠可解析的照片 caption",
        actual=candidate.caption.text,
        evidence=[*evidence_for_component(component), *_caption_evidence(candidate.caption)],
        confidence=Confidence.MEDIUM,
        metadata={
            **_component_metadata(component),
            "matched_captions": matched_captions,
            "matching_strategy": "caption_uncertain",
            "is_unused_component": False,
            "caption_id": candidate.caption.caption_id,
            "caption_subject": candidate.subject_name,
            "ocr_confidence": candidate.ocr_confidence,
            "uncertainty_reason": candidate.uncertainty_reason,
        },
    )


def _coverage_record(
    component: SampleComponent,
    candidate: _CaptionCandidate | None,
    matching_strategy: str | None,
    *,
    is_unused_component: bool,
) -> dict[str, Any]:
    return {
        **_component_metadata(component),
        "component_id": component.component_id,
        "caption_id": candidate.caption.caption_id if candidate else None,
        "matched_captions": [candidate.caption.text] if candidate else [],
        "matching_strategy": matching_strategy,
        "is_unused_component": is_unused_component,
    }


def _component_metadata(component: SampleComponent) -> dict[str, Any]:
    return {
        "component_name": component.component_name,
        "component_key": component.identity_key or component.component_id,
        "sample_role": component.metadata.get("sample_role", "main_sample"),
        "supporting_equipment": component_is_supporting_equipment(component),
    }


def _candidate_metadata(candidate: _CaptionCandidate) -> dict[str, Any]:
    return {
        "caption_id": candidate.caption.caption_id,
        "caption_text": candidate.caption.text,
        "caption_subject": candidate.subject_name,
        "page_number": candidate.caption.page_number,
        "ocr_confidence": candidate.ocr_confidence,
        "is_uncertain": candidate.is_uncertain,
        "uncertainty_reason": candidate.uncertainty_reason,
    }


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


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


def _following_char(text: str, prefix: str) -> str | None:
    if len(text) <= len(prefix):
        return None
    return text[len(prefix)]


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "check_c05_photo_coverage",
    "extract_photo_caption_subject",
    "match_photo_subject",
]
