from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.common import Confidence, Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.report import InspectionItem, ReportDocument
from app.domain.result import CheckResult
from app.rules.report.common import PLACEHOLDER_MARKERS, compact, make_result
from app.rules.report.context import CheckContext


CHECK_ID = "C07"
CHECK_NAME = "单项结论逻辑"


@dataclass(frozen=True)
class ConclusionDecision:
    expected: str
    reason: str
    result_values: list[str]


def check_c07_item_conclusion(
    document: ReportDocument,
    context: CheckContext | None = None,
) -> CheckResult:
    context = context or CheckContext()
    findings: list[Finding] = []
    group_metadata: list[dict[str, object]] = []

    for sequence, items in _group_items(document.inspection_items):
        decision = infer_expected_conclusion(_collect_result_values(items))
        actual = _authoritative_conclusion(items)
        group_metadata.append(
            {
                "item_no": sequence,
                "normalized_item_no": sequence,
                "expected_conclusion": decision.expected,
                "actual_conclusion": actual,
                "result_values": decision.result_values,
                "decision_reason": decision.reason,
            }
        )

        if actual != decision.expected:
            findings.append(
                Finding(
                    id=f"{context.task_id}-c07-{sequence}-conclusion-mismatch",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code=_mismatch_code(decision.expected, actual),
                    message=_mismatch_message(sequence, decision.expected, actual, decision.reason),
                    location=items[0].row_location if items else None,
                    expected=decision.expected,
                    actual=actual,
                    evidence=_group_evidence(sequence, items),
                    confidence=Confidence.HIGH,
                    metadata={
                        "item_no": sequence,
                        "normalized_item_no": sequence,
                        "result_values": decision.result_values,
                        "actual_conclusion": actual,
                        "decision_reason": decision.reason,
                    },
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={"groups": group_metadata},
        pass_summary="检验项目单项结论逻辑一致",
        issue_summary=f"单项结论存在 {len(findings)} 项逻辑问题",
    )


def normalize_item_no(sequence: int | str | None) -> str | None:
    if sequence is None:
        return None
    if isinstance(sequence, int):
        return str(sequence)

    text = compact(str(sequence))
    if not text:
        return None
    match = re.search(r"\d+", text)
    if match:
        return match.group(0)
    return None


def infer_expected_conclusion(result_values: Iterable[str | None]) -> ConclusionDecision:
    tokens = [_normalize_result_token(value) for value in _split_result_values(result_values)]
    if any(_is_nonconforming_result(token) for token in tokens):
        return ConclusionDecision(
            expected="不符合",
            reason="has_nonconforming_result",
            result_values=tokens,
        )
    if not tokens or all(_is_placeholder_result(token) for token in tokens):
        return ConclusionDecision(
            expected="/",
            reason="all_placeholders_or_blank",
            result_values=tokens,
        )
    return ConclusionDecision(
        expected="符合",
        reason="has_conforming_or_non_empty_result",
        result_values=tokens,
    )


def _group_items(items: Iterable[InspectionItem]) -> list[tuple[str, list[InspectionItem]]]:
    groups: OrderedDict[str, list[InspectionItem]] = OrderedDict()
    current_sequence: str | None = None

    for item in items:
        sequence = normalize_item_no(item.sequence_raw) or normalize_item_no(item.sequence)
        if sequence is not None:
            current_sequence = sequence
            groups.setdefault(sequence, []).append(item)
            continue

        if current_sequence is not None and _row_has_c07_payload(item):
            groups[current_sequence].append(item)

    return list(groups.items())


def _row_has_c07_payload(item: InspectionItem) -> bool:
    return any(
        (value or "").strip()
        for value in (
            item.test_result,
            item.conclusion,
            item.remark,
            item.standard_requirement,
        )
    ) or bool(item.result_values)


def _collect_result_values(items: list[InspectionItem]) -> list[str | None]:
    values: list[str | None] = []
    for item in items:
        if item.result_values:
            values.extend(item.result_values)
        else:
            values.append(item.test_result)
    return values


def _split_result_values(result_values: Iterable[str | None]) -> list[str | None]:
    tokens: list[str | None] = []
    for value in result_values:
        if value is None:
            tokens.append(None)
            continue
        parts = re.split(r"[；;]", value)
        tokens.extend(parts if parts else [value])
    return tokens


def _normalize_result_token(value: str | None) -> str:
    return compact(value)


def _is_nonconforming_result(token: str) -> bool:
    return "不符合" in token


def _is_placeholder_result(token: str) -> bool:
    return token in {"", *PLACEHOLDER_MARKERS}


def _authoritative_conclusion(items: list[InspectionItem]) -> str:
    for item in items:
        conclusion = _normalize_conclusion(item.conclusion)
        if conclusion:
            return conclusion
    return ""


def _normalize_conclusion(value: str | None) -> str:
    text = compact(value)
    if text == "——":
        return "/"
    if text == "符合要求":
        return "符合"
    if text == "不符合要求":
        return "不符合"
    return text


def _mismatch_code(expected: str, actual: str) -> str:
    if expected == "/":
        return "CONCLUSION_MISMATCH_001"
    if expected == "符合":
        return "CONCLUSION_MISMATCH_002"
    if expected == "不符合":
        return "CONCLUSION_MISMATCH_003"
    if actual == "不符合":
        return "CONCLUSION_MISMATCH_004"
    return "CONCLUSION_MISMATCH_002"


def _mismatch_message(sequence: str, expected: str, actual: str, reason: str) -> str:
    actual_text = actual if actual else "空白"
    reason_text = {
        "has_nonconforming_result": "存在不符合的检验结果",
        "all_placeholders_or_blank": "检验结果全部为占位符或空白",
        "has_conforming_or_non_empty_result": "存在符合要求或其他非空检验结果",
    }.get(reason, reason)
    return f"序号 {sequence} 的检验结果与单项结论逻辑不一致：{reason_text}，期望单项结论为“{expected}”，实际为“{actual_text}”。"


def _group_evidence(sequence: str, items: list[InspectionItem]) -> list[Evidence]:
    evidence_items: list[Evidence] = []
    for index, item in enumerate(items):
        evidence_items.extend(item.evidence)
        evidence_items.append(
            Evidence(
                id=f"c07-{sequence}-row-{index}",
                source_type=SourceType.REPORT,
                location=item.row_location,
                raw_text=(
                    f"序号：{item.sequence_raw or item.sequence or ''}；"
                    f"检验结果：{item.test_result or ''}；"
                    f"单项结论：{item.conclusion or ''}"
                ),
                value=item.test_result,
                method=EvidenceMethod.PDF_TEXT,
                confidence=Confidence.HIGH,
                metadata={
                    "sequence_raw": item.sequence_raw,
                    "sequence": item.sequence,
                    "test_result": item.test_result,
                    "result_values": item.result_values,
                    "conclusion": item.conclusion,
                    "source_page": item.source_page,
                    "row_index_in_page": item.row_index_in_page,
                },
            )
        )
    return evidence_items


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "ConclusionDecision",
    "check_c07_item_conclusion",
    "infer_expected_conclusion",
    "normalize_item_no",
]
