from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.result import CheckResult, CheckStatus


def sample_check_results(task_id: str = "task-export-1") -> list[CheckResult]:
    report_evidence = Evidence(
        id="ev-report-model",
        source_type=SourceType.REPORT,
        location=Location(source_type=SourceType.REPORT, page_number=3, column_name="型号规格"),
        raw_text="第三页型号规格：ABC-2",
        normalized_text="ABC-2",
        value="ABC-2",
        method=EvidenceMethod.PDF_TEXT,
    )
    ptr_evidence = Evidence(
        id="ev-ptr-clause",
        source_type=SourceType.PTR,
        location=Location(source_type=SourceType.PTR, page_number=5, section="2.1.1"),
        raw_text="电阻值应≤10Ω。",
        normalized_text="电阻值应<=10Ω。",
        value="电阻值应<=10Ω。",
        method=EvidenceMethod.PDF_TEXT,
    )
    error_finding = Finding(
        id="finding-c01-model",
        task_id=task_id,
        check_id="C01",
        severity=FindingSeverity.ERROR,
        code="C01_FIELD_MISMATCH",
        message="首页与第三页型号规格不一致",
        expected="ABC-1",
        actual="ABC-2",
        evidence=[report_evidence],
        metadata={"field_name": "型号规格"},
    )
    warn_finding = Finding(
        id="finding-ptr-symbol",
        task_id=task_id,
        check_id="PTR_CLAUSE",
        severity=FindingSeverity.WARN,
        code="PTR_CLAUSE_TEXT_MISMATCH",
        message="PTR 条款正文与报告标准要求存在符号差异",
        expected="电阻值应<=10Ω。",
        actual="电阻值应<10Ω。",
        evidence=[ptr_evidence],
        metadata={"clause_number": "2.1.1"},
    )

    return [
        CheckResult(
            task_id=task_id,
            check_id="C01",
            check_name="首页与第三页一致性",
            status=CheckStatus.FAIL,
            summary="发现 1 个字段不一致",
            findings=[error_finding],
            evidence=[report_evidence],
            metadata={
                "rule_version": "test",
                "comparison_details": {
                    "title": "首页与报告首页一致性",
                    "overall_status": "mismatch",
                    "overall_reason": "型号规格不一致。",
                    "sources": [
                        {
                            "source_key": "cover_page",
                            "label": "封面页",
                            "page_number": 1,
                            "display_page_label": "PDF 第 1 页",
                            "section": "报告封面",
                        },
                        {
                            "source_key": "report_home_page",
                            "label": "报告首页",
                            "page_number": 3,
                            "display_page_label": "PDF 第 3 页 / 报告第 1 页",
                            "section": "检验报告首页",
                        },
                    ],
                    "fields": [
                        {
                            "field_key": "model_spec",
                            "field_label": "型号规格",
                            "left": {
                                "source_key": "cover_page",
                                "label": "封面页摘录",
                                "page_number": 1,
                                "display_page_label": "PDF 第 1 页",
                                "raw_text": "ABC-1",
                                "normalized_text": "ABC-1",
                            },
                            "right": {
                                "source_key": "report_home_page",
                                "label": "报告首页摘录",
                                "page_number": 3,
                                "display_page_label": "PDF 第 3 页 / 报告第 1 页",
                                "raw_text": "ABC-2",
                                "normalized_text": "ABC-2",
                            },
                            "status": "mismatch",
                            "reason": "两处摘录不一致",
                            "evidence_ids": ["ev-report-model"],
                        }
                    ],
                },
                "explanation_details": {
                    "check_goal": "核对首页与报告首页字段是否一致",
                    "user_question": "系统摘录了哪些字段，为什么判定不一致？",
                    "overall_reason": "型号规格两处摘录不一致。",
                    "source_sections": [
                        {
                            "label": "封面页",
                            "page_number": 1,
                            "display_page_label": "PDF 第 1 页",
                            "description": "报告封面",
                        },
                        {
                            "label": "报告首页",
                            "page_number": 3,
                            "display_page_label": "PDF 第 3 页 / 报告第 1 页",
                            "description": "检验报告首页",
                        },
                    ],
                    "comparison_rows": [
                        {
                            "field": "型号规格",
                            "left_label": "封面页摘录",
                            "left_value": "ABC-1",
                            "right_label": "报告首页摘录",
                            "right_value": "ABC-2",
                            "status": "mismatch",
                            "reason": "两处摘录不一致",
                        }
                    ],
                    "evidence_groups": [
                        {
                            "title": "字段摘录",
                            "items": [
                                {
                                    "label": "第三页型号规格",
                                    "page_number": 3,
                                    "evidence_type": "field_extract",
                                    "status": "mismatch",
                                }
                            ],
                        }
                    ],
                    "decision": {
                        "user_facing_status": "candidate_issue",
                        "label": "候选问题",
                        "reason": "规则发现字段不一致，需结合最终审核确认。",
                    },
                    "next_action": "查看型号规格两处摘录。",
                },
            },
        ),
        CheckResult(
            task_id=task_id,
            check_id="PTR_CLAUSE",
            check_name="PTR 条款正文一致性",
            status=CheckStatus.REVIEW,
            summary="发现 1 个需复核条款",
            findings=[warn_finding],
            evidence=[ptr_evidence],
            metadata={"scope": "chapter_2"},
        ),
        CheckResult(
            task_id=task_id,
            check_id="C08",
            check_name="非空字段",
            status=CheckStatus.PASS,
            summary="未发现空字段",
        ),
    ]
