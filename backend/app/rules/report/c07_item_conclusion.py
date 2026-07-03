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
from app.rules.report.explanation_details import (
    comparison_row,
    decision_detail,
    evidence_group,
    evidence_item,
    explanation_details,
    source_section,
)


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
            "explanation_details": _build_explanation_details(group_metadata, findings),
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
        "item_name": group.rows[0].item_name if group.rows else None,
        "standard_clause": group.rows[0].standard_clause if group.rows else None,
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
                "item_name": item.item_name,
                "standard_clause": item.standard_clause,
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


def _build_explanation_details(
    group_metadata: list[dict[str, Any]],
    findings: list[Finding],
) -> dict[str, Any]:
    status, label, reason = _decision_from_findings(findings)
    selected_groups = _selected_groups_for_explanation(group_metadata, findings)
    selected_groups = [_with_finding_metadata(group, findings) for group in selected_groups]
    rows: list[dict[str, Any]] = [
        comparison_row(
            field="项目组数量",
            left_label="InspectionItemGroup",
            left_value=len(group_metadata),
            right_label="C07",
            right_value="按同序号/续表聚合后判断",
            status="match" if not findings else "needs_review",
            reason="C07 基于聚合后的检验项目组判断检验结果与单项结论。",
        )
    ]
    for group in selected_groups:
        item_no = str(group.get("display_item_no") or group.get("item_no") or "")
        pages = group.get("pages") or []
        conclusion_status = "match" if group.get("expected_conclusion") == group.get("actual_conclusion") else "needs_review"
        if group.get("complex_matrix_table"):
            conclusion_status = "needs_review"
        rows.extend(
            [
                comparison_row(
                    field="序号",
                    left_label="检验项目组",
                    left_value=item_no,
                    right_label="涉及页码",
                    right_value=pages,
                    status="match",
                    reason=f"该项目组共 {group.get('group_row_count') or 0} 行。",
                ),
                comparison_row(
                    field="检验结果 tokens",
                    left_label="结构化检验结果",
                    left_value=group.get("effective_test_results") or group.get("result_values"),
                    right_label="推断原因",
                    right_value=group.get("decision_reason"),
                    status="match" if group.get("decision_reason") != "all_placeholders_or_blank" else "needs_review",
                    reason="用于推断 expected conclusion 的检验结果 token。",
                ),
                comparison_row(
                    field="单项结论 candidates",
                    left_label="实际单项结论",
                    left_value=group.get("actual_conclusion"),
                    right_label="期望单项结论",
                    right_value=group.get("expected_conclusion"),
                    status=conclusion_status,
                    reason=_group_reason(group),
                ),
                comparison_row(
                    field="备注",
                    left_label="备注摘录",
                    left_value=_remarks(group),
                    right_label="跨页续表",
                    right_value=bool(group.get("continuation_markers")),
                    status="match",
                    reason="备注和续表信息用于辅助判断结构化抽取是否完整。",
                ),
                comparison_row(
                    field="complex_matrix_table",
                    left_label="复杂矩阵标记",
                    left_value=bool(group.get("complex_matrix_table")),
                    right_label="复核建议",
                    right_value=group.get("complex_matrix_reason"),
                    status="needs_review" if group.get("complex_matrix_table") else "not_applicable",
                    reason=(
                        "该项目为复杂矩阵表，需要查看矩阵结果列、单项结论列和跨页续表结构。"
                        if group.get("complex_matrix_table")
                        else "该项目未标记为复杂矩阵表。"
                    ),
                ),
            ]
        )
    source_pages = sorted({page for group in group_metadata for page in (group.get("pages") or []) if page is not None})
    return explanation_details(
        check_goal="核对检验结果与单项结论是否一致。",
        user_question="当前检验项目摘录了哪些结果 token、单项结论和备注？为什么通过、候选问题或需复核？",
        overall_reason=reason,
        source_sections=[
            source_section(
                label="检验项目表",
                page_number=source_pages[0] if source_pages else None,
                description="按序号和续表行聚合后的检验项目组。",
            )
        ],
        comparison_rows=rows,
        evidence_groups=[
            evidence_group(
                "C07 检验项目组",
                [
                    evidence_item(
                        label=f"序号 {group.get('display_item_no') or group.get('item_no')}: {group.get('item_name') or ''}",
                        page_number=(group.get("pages") or [None])[0],
                        evidence_type="inspection_item_group",
                        status="complex_matrix" if group.get("complex_matrix_table") else "review_target",
                    )
                    for group in selected_groups
                ],
            )
        ],
        decision=decision_detail(status, label, reason),
        next_action="若显示复杂矩阵或抽取不确定，请查看该项目的表格视觉证据和 Codex 复核意见。",
    )


def _selected_groups_for_explanation(
    group_metadata: list[dict[str, Any]],
    findings: list[Finding],
) -> list[dict[str, Any]]:
    finding_item_numbers = {
        str(finding.metadata.get("item_no") or finding.metadata.get("display_item_no") or "")
        for finding in findings
        if finding.metadata
    }
    if finding_item_numbers:
        return [
            group
            for group in group_metadata
            if str(group.get("item_no") or group.get("display_item_no") or "") in finding_item_numbers
        ]
    return group_metadata[:10]


def _with_finding_metadata(group: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    item_no = str(group.get("item_no") or group.get("display_item_no") or "")
    for finding in findings:
        finding_item_no = str(finding.metadata.get("item_no") or finding.metadata.get("display_item_no") or "")
        if finding_item_no == item_no:
            return {**group, **finding.metadata}
    return group


def _decision_from_findings(findings: list[Finding]) -> tuple[str, str, str]:
    if not findings:
        return "passed", "通过", "该项目存在符合要求结果时单项结论为符合，或占位结果对应 /，逻辑一致。"
    if any(finding.code == "CONCLUSION_REVIEW_NEEDED_COMPLEX_MATRIX" for finding in findings):
        return "needs_review", "需复核", "存在复杂矩阵表，需要专门查看矩阵结果列、单项结论列和跨页续表结构。"
    if any(finding.severity == FindingSeverity.ERROR for finding in findings):
        return "candidate_issue", "候选问题", f"规则发现 {len(findings)} 项单项结论候选逻辑问题。"
    return "needs_review", "需复核", f"规则发现 {len(findings)} 项结构化表格抽取不确定项。"


def _group_reason(group: dict[str, Any]) -> str:
    if group.get("complex_matrix_table"):
        return "复杂矩阵表不按普通 C07 单项结论逻辑直接裁决。"
    if group.get("expected_conclusion") == group.get("actual_conclusion"):
        return "检验结果 token 支持当前单项结论。"
    return "结构化检验结果与单项结论存在候选不一致或需复核。"


def _remarks(group: dict[str, Any]) -> list[str]:
    remarks: list[str] = []
    for row in group.get("source_rows") or []:
        if isinstance(row, dict) and row.get("remark"):
            remarks.append(str(row["remark"]))
    return remarks


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "ConclusionDecision",
    "check_c07_item_conclusion",
    "infer_expected_conclusion",
    "normalize_item_no",
]
