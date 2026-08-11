from __future__ import annotations

import json

from app.application.report_comparison_finalization import attach_final_comparison_details
from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.result import CheckResult, CheckStatus


def test_refuted_photo_finding_becomes_positive_final_coverage_detail() -> None:
    finding = _finding(
        finding_id="photo-missing",
        check_id="C05",
        final_status="refuted",
        metadata={
            "component_name": "线缆和电源线",
            "candidate_captions": [
                {
                    "caption_text": "№6 电源线",
                    "caption_subject": "电源线",
                    "page_number": 12,
                },
                {
                    "caption_text": "№7 线缆",
                    "caption_subject": "线缆",
                    "page_number": 13,
                },
            ],
            "codex_reasoning_summary": (
                "候选题注列表中已有“№6 电源线”（第12页）及“№7 线缆”（第13页），"
                "覆盖样品描述中合并列出的两个部件；“未匹配到照片”与该证据冲突。"
            ),
        },
    )
    result = CheckResult(
        task_id="task-final-details",
        check_id="C05",
        check_name="照片覆盖",
        status=CheckStatus.FAIL,
        findings=[finding],
        metadata={
            "explanation_details": {
                "comparison_rows": [
                    {
                        "field": "线缆和电源线",
                        "status": "missing",
                        "reason": "旧候选行",
                    }
                ]
            }
        },
    )

    attach_final_comparison_details([result])

    details = result.metadata["final_comparison_details"]
    assert details["overall_status"] == "passed"
    assert details["fields"] == [
        {
            "field_key": "线缆和电源线:coverage",
            "field_label": "线缆和电源线",
            "status": "match",
            "reason": "报告照片页已有“№6 电源线”（第12页）及“№7 线缆”（第13页），覆盖样品描述中合并列出的两个部件。",
            "evidence_ids": ["evidence-photo-missing"],
            "left": {
                "source_key": "report_extract",
                "label": "样品描述摘录",
                "raw_text": "线缆和电源线",
                "normalized_text": "线缆和电源线",
                "page_number": 4,
                "display_page_label": "PDF 第 4 页",
            },
            "right": {
                "source_key": "visual_evidence",
                "label": "照片页摘录",
                "raw_text": "№6 电源线；№7 线缆",
                "normalized_text": "№6 电源线；№7 线缆",
                "page_number": 12,
                "display_page_label": "PDF 第 12、13 页",
            },
        }
    ]
    serialized = json.dumps(details, ensure_ascii=False).lower()
    assert "codex" not in serialized
    assert "候选问题" not in serialized
    assert "未匹配到照片" not in serialized


def test_final_details_keep_only_actionable_findings_when_statuses_are_mixed() -> None:
    refuted = _finding(
        finding_id="refuted-row",
        check_id="C07",
        final_status="refuted",
        expected="符合",
        actual="/",
    )
    confirmed = _finding(
        finding_id="confirmed-row",
        check_id="C07",
        final_status="confirmed",
        expected="符合",
        actual="/",
        metadata={
            "item_no": "77",
            "item_name": "机械危险",
            "codex_reasoning_summary": "候选不一致成立。",
        },
    )
    manual = _finding(
        finding_id="manual-row",
        check_id="C07",
        final_status="manual_review_required",
        expected="/",
        actual="符合",
        metadata={"item_no": "161", "item_name": "电磁兼容要求"},
    )
    result = CheckResult(
        task_id="task-final-details",
        check_id="C07",
        check_name="单项结论逻辑",
        status=CheckStatus.FAIL,
        findings=[refuted, confirmed, manual],
    )

    attach_final_comparison_details([result])

    details = result.metadata["final_comparison_details"]
    assert details["overall_status"] == "confirmed_error"
    assert [field["field_key"] for field in details["fields"]] == ["77", "161"]
    assert [field["status"] for field in details["fields"]] == ["mismatch", "needs_review"]
    assert details["fields"][0]["reason"] == "该不一致已确认。"


def test_refuted_visual_details_omit_unscoped_unknown_observations() -> None:
    finding = _finding(
        finding_id="label-match",
        check_id="C04",
        final_status="refuted",
        metadata={
            "codex_field_comparisons": [
                {
                    "field_name": "component_name",
                    "expected_value": "主机",
                    "observed_value": "治疗仪",
                    "status": "match",
                    "reasoning": "标签产品名称与主机相符。",
                },
                {
                    "field_name": "model",
                    "expected_value": None,
                    "observed_value": "MODEL-1",
                    "status": "unknown",
                    "reasoning": "样品描述未提供待比对型号。",
                },
            ]
        },
    )
    result = CheckResult(
        task_id="task-final-details",
        check_id="C04",
        check_name="样品描述表格与中文标签 OCR",
        status=CheckStatus.REVIEW,
        findings=[finding],
    )

    attach_final_comparison_details([result])

    fields = result.metadata["final_comparison_details"]["fields"]
    assert len(fields) == 1
    assert fields[0]["field_label"] == "部件名称"
    assert fields[0]["right"]["raw_text"] == "治疗仪"


def _finding(
    *,
    finding_id: str,
    check_id: str,
    final_status: str,
    expected: str | None = None,
    actual: str | None = None,
    metadata: dict | None = None,
) -> Finding:
    finding_metadata = dict(metadata or {})
    finding_metadata["final_status"] = final_status
    return Finding(
        id=finding_id,
        task_id="task-final-details",
        check_id=check_id,
        severity=FindingSeverity.ERROR,
        code="TEST_FINDING",
        message=f"{finding_id} message",
        expected=expected,
        actual=actual,
        location=Location(
            source_id="report",
            source_type=SourceType.REPORT,
            page_number=4,
        ),
        evidence=[
            Evidence(
                id=f"evidence-{finding_id}",
                source_type=SourceType.REPORT,
                location=Location(
                    source_id="report",
                    source_type=SourceType.REPORT,
                    page_number=4,
                ),
                raw_text=expected or _component_name(finding_metadata),
                method=EvidenceMethod.PDF_TEXT,
            )
        ],
        metadata=finding_metadata,
    )


def _component_name(metadata: dict) -> str:
    value = metadata.get("component_name")
    return str(value) if value is not None else "evidence"
