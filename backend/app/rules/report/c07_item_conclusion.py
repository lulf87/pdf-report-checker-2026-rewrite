from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from app.domain.common import Confidence, Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.inspection_group import InspectionItemGroup
from app.domain.report import ReportDocument
from app.domain.result import CheckResult
from app.infrastructure.report.inspection_item_group_builder import build_inspection_item_groups
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
    build_result = build_inspection_item_groups(list(document.inspection_items))

    for group in build_result.groups:
        decision = infer_expected_conclusion(group.effective_test_results)
        actual = _normalize_conclusion(group.effective_single_conclusion)
        metadata = _group_metadata(group, decision, actual)
        group_metadata.append(metadata)

        if actual != decision.expected:
            complex_matrix_reason = _complex_matrix_reason(group)
            if complex_matrix_reason is not None:
                complex_metadata = {
                    **metadata,
                    "complex_matrix_table": True,
                    "complex_matrix_reason": complex_matrix_reason,
                    "needs_codex_review": True,
                }
                findings.append(
                    Finding(
                        id=f"{context.task_id}-c07-{group.item_no}-complex-matrix-review",
                        task_id=context.task_id,
                        check_id=CHECK_ID,
                        severity=FindingSeverity.WARN,
                        code="CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX",
                        message=(
                            f"序号 {group.item_no} 为复杂矩阵表，普通 C07 单项结论逻辑无法稳定判断，"
                            "需人工或 Codex 复核列映射和续表结构。"
                        ),
                        location=group.rows[0].row_location if group.rows else None,
                        expected=decision.expected,
                        actual=actual,
                        evidence=_group_evidence(group, decision, actual),
                        confidence=Confidence.MEDIUM,
                        metadata=complex_metadata,
                    )
                )
                continue

            if _should_review_extraction_uncertainty(group, decision):
                findings.append(
                    Finding(
                        id=f"{context.task_id}-c07-{group.item_no}-result-token-recovery-uncertain",
                        task_id=context.task_id,
                        check_id=CHECK_ID,
                        severity=FindingSeverity.WARN,
                        code="CONCLUSION_REVIEW_NEEDED_EXTRACTION_UNCERTAIN",
                        message=(
                            f"序号 {group.item_no} 的结构化检验结果可能不完整，"
                            "需结合原始表格或 Codex evidence 复核后再判断单项结论。"
                        ),
                        location=group.rows[0].row_location if group.rows else None,
                        expected=decision.expected,
                        actual=actual,
                        evidence=_group_evidence(group, decision, actual),
                        confidence=Confidence.MEDIUM,
                        metadata={**metadata, "needs_codex_review": True},
                    )
                )
                continue

            findings.append(
                Finding(
                    id=f"{context.task_id}-c07-{group.item_no}-conclusion-mismatch",
                    task_id=context.task_id,
                    check_id=CHECK_ID,
                    severity=FindingSeverity.ERROR,
                    code=_mismatch_code(decision.expected, actual),
                    message=_mismatch_message(group.item_no, decision.expected, actual, decision.reason),
                    location=group.rows[0].row_location if group.rows else None,
                    expected=decision.expected,
                    actual=actual,
                    evidence=_group_evidence(group, decision, actual),
                    confidence=Confidence.HIGH,
                    metadata=metadata,
                )
            )

    return make_result(
        context=context,
        check_id=CHECK_ID,
        check_name=CHECK_NAME,
        findings=findings,
        metadata={
            "groups": group_metadata,
            "group_builder_diagnostics": build_result.diagnostics,
            "ungrouped_row_count": len(build_result.ungrouped_rows),
        },
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


def _group_metadata(group: InspectionItemGroup, decision: ConclusionDecision, actual: str) -> dict[str, Any]:
    source_rows = _source_rows(group)
    return {
        "item_no": group.item_no,
        "normalized_item_no": group.item_no,
        "display_item_no": group.display_item_no,
        "expected_conclusion": decision.expected,
        "actual_conclusion": actual,
        "effective_test_results": decision.result_values,
        "original_effective_test_results": list(group.original_effective_test_results),
        "recovered_result_tokens": list(group.recovered_result_tokens),
        "recovered_effective_test_results": list(group.recovered_effective_test_results),
        "result_token_recovery_applied": group.result_token_recovery_applied,
        "result_token_recovery_diagnostics": list(group.result_token_recovery_diagnostics),
        "result_token_recovery_confidence": group.result_token_recovery_confidence,
        "result_values": decision.result_values,
        "group_row_count": len(group.rows),
        "pages": list(group.pages),
        "continuation_markers": [marker.model_dump(mode="json") for marker in group.continuation_markers],
        "source_rows": source_rows,
        "result_summary": _result_summary(decision.result_values),
        "reasoning_basis": decision.reason,
        "decision_reason": decision.reason,
        "suppressed_physical_row_count": max(0, len(group.rows) - 1),
        "group_diagnostics": group.diagnostics,
    }


def _source_rows(group: InspectionItemGroup) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(group.rows):
        rows.append(
            {
                "source_index": _source_index(group, index),
                "page_number": item.source_page,
                "row_index": item.row_index_in_page,
                "sequence_raw": item.sequence_raw,
                "sequence": item.sequence,
                "is_continuation": item.is_continuation,
                "test_result": item.test_result,
                "result_values": list(item.result_values),
                "single_conclusion": item.conclusion,
                "remark": item.remark,
            }
        )
    return rows


def _should_review_extraction_uncertainty(group: InspectionItemGroup, decision: ConclusionDecision) -> bool:
    return (
        decision.reason == "all_placeholders_or_blank"
        and group.result_token_recovery_confidence == "uncertain"
        and bool(group.result_token_recovery_diagnostics)
    )


def _complex_matrix_reason(group: InspectionItemGroup) -> str | None:
    text = _group_text_blob(group)
    compact_text = compact(text).lower()
    row_count = len(group.rows)
    page_count = len(group.pages)
    matrix_keyword_count = sum(
        1
        for keyword in (
            "矩阵",
            "漏电流",
            "电流",
            "ma",
            "μa",
            "ua",
            "正常状态",
            "单一故障",
            "直流",
            "交流",
        )
        if keyword.lower() in compact_text
    )
    has_measurement_limit = bool(re.search(r"[≤＜<]\s*\d+(?:\.\d+)?\s*(?:m?a|μa|ua)", compact_text))
    has_conflicting_conclusion = any(
        diagnostic.get("code") == "CONFLICTING_EFFECTIVE_CONCLUSION" for diagnostic in group.diagnostics
    )
    has_non_conclusion_candidate = any(
        item.conclusion and re.search(r"\d|≤|＜|<|mA|μA|uA|正常状态|单一故障", item.conclusion, re.IGNORECASE)
        for item in group.rows
    )

    if (
        row_count > 10
        and (page_count >= 3 or "续" in compact_text)
        and matrix_keyword_count >= 4
        and (has_measurement_limit or has_conflicting_conclusion or has_non_conclusion_candidate)
    ):
        return (
            "复杂矩阵表/漏电流多页表存在列映射或续表歧义，"
            f"row_count={row_count}, page_count={page_count}, matrix_keyword_count={matrix_keyword_count}"
        )
    return None


def _group_text_blob(group: InspectionItemGroup) -> str:
    parts: list[str] = []
    for item in group.rows:
        parts.extend(
            str(value)
            for value in (
                item.sequence_raw,
                item.item_name,
                item.standard_clause,
                item.standard_requirement,
                item.test_result,
                item.conclusion,
                item.remark,
                item.metadata.get("row_text"),
            )
            if value
        )
        parts.extend(str(value) for value in item.result_values if value)
    return "\n".join(parts)


def _source_index(group: InspectionItemGroup, row_index: int) -> int | None:
    if row_index >= len(group.source_evidence):
        return None
    value = group.source_evidence[row_index].get("source_index")
    return value if isinstance(value, int) else None


def _result_summary(result_values: list[str]) -> dict[str, int]:
    nonconforming = sum(1 for value in result_values if _is_nonconforming_result(value))
    placeholders = sum(1 for value in result_values if _is_placeholder_result(value))
    conforming_or_non_empty = len(result_values) - nonconforming - placeholders
    return {
        "total_count": len(result_values),
        "nonconforming_count": nonconforming,
        "placeholder_count": placeholders,
        "conforming_or_non_empty_count": max(0, conforming_or_non_empty),
    }


def _group_evidence(group: InspectionItemGroup, decision: ConclusionDecision, actual: str) -> list[Evidence]:
    evidence_items: list[Evidence] = []
    evidence_items.append(
        Evidence(
            id=f"c07-{group.item_no}-group-summary",
            source_type=SourceType.REPORT,
            location=group.rows[0].row_location if group.rows else None,
            raw_text=(
                f"序号：{group.display_item_no or group.item_no}；"
                f"有效检验结果：{'；'.join(decision.result_values)}；"
                f"期望单项结论：{decision.expected}；"
                f"实际单项结论：{actual}"
            ),
            value=actual,
            method=EvidenceMethod.PDF_TEXT,
            confidence=Confidence.HIGH,
            metadata=_group_metadata(group, decision, actual),
        )
    )
    for index, item in enumerate(group.rows):
        evidence_items.extend(item.evidence)
        evidence_items.append(
            Evidence(
                id=f"c07-{group.item_no}-row-{index}",
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
