from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domain.common import Confidence, Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.report import FirstPageInfo, ReportDocument, ReportField, ThirdPageInfo
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.context import CheckContext


CHECK_ID = "C01"
CHECK_NAME = "首页与第三页一致性"


@dataclass(frozen=True)
class _ComparedField:
    display_name: str
    key: str
    first_attr: str
    third_attr: str | None = None


_FIELDS_TO_COMPARE = (
    _ComparedField("委托方", "client", "client", "client"),
    _ComparedField("样品名称", "sample_name", "sample_name", None),
    _ComparedField("型号规格", "model_spec", "model_spec", "model_spec"),
)


def check_c01_home_vs_third(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    """Run C01: homepage and third-page identity fields must match strictly."""
    context = context or CheckContext()
    findings: list[Finding] = []
    result_evidence: list[Evidence] = []
    field_results: list[dict[str, object]] = []

    for index, spec in enumerate(_FIELDS_TO_COMPARE, start=1):
        first_field = _field_from_first_page(document.first_page, spec)
        third_field = _field_from_third_page(document.third_page, spec)

        first_value = _strict_value(first_field)
        third_value = _strict_value(third_field)
        first_missing = first_value is None or first_value == ""
        third_missing = third_value is None or third_value == ""

        result_evidence.extend(_evidence_for_field(first_field, f"first-{spec.key}"))
        result_evidence.extend(_evidence_for_field(third_field, f"third-{spec.key}"))

        if first_missing or third_missing:
            findings.append(
                _missing_finding(
                    context=context,
                    document=document,
                    spec=spec,
                    index=index,
                    first_value=first_value,
                    third_value=third_value,
                    first_missing=first_missing,
                    third_missing=third_missing,
                    evidence=[
                        *_evidence_for_field(first_field, f"first-{spec.key}"),
                        *_evidence_for_field(third_field, f"third-{spec.key}"),
                    ],
                )
            )
            field_results.append({"field": spec.display_name, "matched": False})
            continue

        if first_value != third_value:
            findings.append(
                _mismatch_finding(
                    context=context,
                    spec=spec,
                    index=index,
                    first_field=first_field,
                    third_field=third_field,
                    first_value=first_value,
                    third_value=third_value,
                )
            )
            field_results.append({"field": spec.display_name, "matched": False})
            continue

        field_results.append({"field": spec.display_name, "matched": True})

    status = _status_from_findings(findings)
    return CheckResult(
        task_id=context.task_id,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        status=status,
        summary=_summary_for_status(status, findings),
        findings=findings,
        evidence=_deduplicate_evidence(result_evidence),
        metadata={"field_results": field_results},
    )


def _field_from_first_page(
    first_page: FirstPageInfo | None,
    spec: _ComparedField,
) -> ReportField | None:
    if first_page is None:
        return None
    field = getattr(first_page, spec.first_attr, None)
    return field or _field_from_collection(first_page.fields, spec.display_name)


def _field_from_third_page(
    third_page: ThirdPageInfo | None,
    spec: _ComparedField,
) -> ReportField | None:
    if third_page is None:
        return None
    if spec.third_attr:
        field = getattr(third_page, spec.third_attr, None)
        if field is not None:
            return field
    return _field_from_collection(third_page.fields, spec.display_name)


def _field_from_collection(
    fields: Iterable[ReportField],
    display_name: str,
) -> ReportField | None:
    for field in fields:
        if field.name == display_name or display_name in field.aliases:
            return field
    return None


def _strict_value(field: ReportField | None) -> str | None:
    if field is None:
        return None
    if field.raw_value is not None:
        return field.raw_value
    if field.value is not None:
        return field.value
    return field.normalized_value


def _mismatch_finding(
    *,
    context: CheckContext,
    spec: _ComparedField,
    index: int,
    first_field: ReportField | None,
    third_field: ReportField | None,
    first_value: str,
    third_value: str,
) -> Finding:
    evidence = [
        *_evidence_for_field(first_field, f"first-{spec.key}"),
        *_evidence_for_field(third_field, f"third-{spec.key}"),
    ]
    return Finding(
        id=f"{context.task_id}-c01-{index}-mismatch",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="C01_FIELD_MISMATCH",
        message=f"首页与第三页{spec.display_name}不一致",
        location=third_field.location if third_field else None,
        expected=first_value,
        actual=third_value,
        evidence=evidence,
        confidence=Confidence.HIGH,
        metadata={
            "field_name": spec.display_name,
            "source_a": "first_page",
            "source_b": "third_page",
            "comparison": "strict",
        },
    )


def _missing_finding(
    *,
    context: CheckContext,
    document: ReportDocument,
    spec: _ComparedField,
    index: int,
    first_value: str | None,
    third_value: str | None,
    first_missing: bool,
    third_missing: bool,
    evidence: list[Evidence],
) -> Finding:
    missing_evidence: list[MissingEvidence] = []
    if first_missing:
        missing_evidence.append(
            MissingEvidence(
                label=f"首页{spec.display_name}",
                reason="ReportDocument.first_page 未提供该字段或字段值为空",
                expected_source=SourceType.REPORT,
                location=_expected_location(document, "first_page", spec.display_name),
            )
        )
    if third_missing:
        missing_evidence.append(
            MissingEvidence(
                label=f"第三页{spec.display_name}",
                reason="ReportDocument.third_page 未提供该字段或字段值为空",
                expected_source=SourceType.REPORT,
                location=_expected_location(document, "third_page", spec.display_name),
            )
        )

    return Finding(
        id=f"{context.task_id}-c01-{index}-missing",
        task_id=context.task_id,
        check_id=CHECK_ID,
        severity=FindingSeverity.ERROR,
        code="C01_FIELD_MISSING",
        message=f"C01 无法定位{spec.display_name}的首页或第三页字段",
        location=_missing_location(missing_evidence),
        expected=first_value,
        actual=third_value,
        evidence=evidence,
        missing_evidence=missing_evidence,
        confidence=Confidence.MEDIUM,
        metadata={
            "field_name": spec.display_name,
            "source_a": "first_page",
            "source_b": "third_page",
            "comparison": "strict",
        },
    )


def _missing_location(missing_evidence: list[MissingEvidence]) -> Location | None:
    for item in missing_evidence:
        if item.location is not None:
            return item.location
    return None


def _expected_location(
    document: ReportDocument,
    page_key: str,
    field_name: str,
) -> Location:
    return Location(
        source_type=SourceType.REPORT,
        page_number=document.page_map.get(page_key),
        section=page_key,
        column_name=field_name,
    )


def _evidence_for_field(field: ReportField | None, fallback_id: str) -> list[Evidence]:
    if field is None:
        return []
    if field.evidence:
        return field.evidence

    value = _strict_value(field)
    if value is None:
        return []

    return [
        Evidence(
            id=f"c01-{fallback_id}",
            source_type=SourceType.REPORT,
            location=field.location,
            raw_text=field.raw_value,
            normalized_text=field.normalized_value,
            value=field.value if field.value is not None else value,
            method=EvidenceMethod.PDF_TEXT,
            confidence=field.confidence,
        )
    ]


def _deduplicate_evidence(evidence_items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    deduped: list[Evidence] = []
    for evidence in evidence_items:
        if evidence.id in seen:
            continue
        seen.add(evidence.id)
        deduped.append(evidence)
    return deduped


def _status_from_findings(findings: list[Finding]) -> CheckStatus:
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return CheckStatus.FAIL
    if any(finding.severity == FindingSeverity.WARN for finding in findings):
        return CheckStatus.REVIEW
    return CheckStatus.PASS


def _summary_for_status(status: CheckStatus, findings: list[Finding]) -> str:
    if status == CheckStatus.PASS:
        return "首页与第三页的委托方、样品名称、型号规格均严格一致"
    if status == CheckStatus.FAIL:
        return f"首页与第三页存在 {len(findings)} 项 C01 字段问题"
    return f"首页与第三页有 {len(findings)} 项 C01 字段证据缺失，需复核"


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "CheckContext",
    "check_c01_home_vs_third",
]
