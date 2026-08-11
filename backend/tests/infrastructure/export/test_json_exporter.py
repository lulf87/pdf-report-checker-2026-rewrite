import json

from app.domain.finding import Finding, FindingSeverity, MissingEvidence
from app.domain.result import CheckResult, CheckStatus
from app.infrastructure.export.json_exporter import export_check_results_to_json
from tests.fixtures.export_result_builder import sample_check_results


def test_json_exporter_preserves_full_check_result_structure() -> None:
    data = export_check_results_to_json(
        sample_check_results(task_id="task-json"),
        task_id="task-json",
        task_type="report_check",
        input_files=["report.pdf"],
        diagnostics=["测试诊断"],
    )

    payload = json.loads(data.decode("utf-8"))

    assert payload["task"] == {
        "task_id": "task-json",
        "task_type": "report_check",
        "input_files": ["report.pdf"],
    }
    assert payload["summary"]["total_checks"] == 3
    assert payload["summary"]["fail_count"] == 1
    assert payload["summary"]["review_count"] == 1
    assert payload["check_results"][0]["findings"][0]["expected"] == "ABC-1"
    assert payload["findings"][1]["actual"] == "电阻值应<10Ω。"
    assert payload["diagnostics"] == ["测试诊断"]


def test_json_exporter_is_deterministic_for_repeated_calls() -> None:
    results = sample_check_results(task_id="task-json-stable")

    first = export_check_results_to_json(results, task_id="task-json-stable")
    second = export_check_results_to_json(results, task_id="task-json-stable")

    assert first == second


def test_json_exporter_exposes_final_audit_and_per_check_final_summary() -> None:
    refuted = Finding(
        id="finding-refuted",
        task_id="task-json-final",
        check_id="C09",
        severity=FindingSeverity.ERROR,
        code="SERIAL_NUMBER_ERROR_002",
        message="规则候选序号问题",
        missing_evidence=[MissingEvidence(label="序号列", reason="测试候选")],
        metadata={"final_status": "refuted"},
    )
    confirmed = Finding(
        id="finding-confirmed",
        task_id="task-json-final",
        check_id="C07",
        severity=FindingSeverity.ERROR,
        code="CONCLUSION_MISMATCH_002",
        message="确认的单项结论问题",
        missing_evidence=[MissingEvidence(label="单项结论", reason="测试确认问题")],
        metadata={"final_status": "confirmed"},
    )
    results = [
        CheckResult(
            task_id="task-json-final",
            check_id="C09",
            check_name="序号连续性",
            status=CheckStatus.FAIL,
            summary="检验项目序号存在 1 项问题",
            findings=[refuted],
        ),
        CheckResult(
            task_id="task-json-final",
            check_id="C07",
            check_name="单项结论逻辑",
            status=CheckStatus.FAIL,
            summary="单项结论存在 1 项逻辑问题",
            findings=[confirmed],
        ),
    ]

    data = export_check_results_to_json(
        results,
        task_id="task-json-final",
        metadata={
            "codex_audit": {
                "final_audit_status": "failed",
                "candidate_findings_count": 2,
                "confirmed_findings_count": 1,
                "confirmed_errors_count": 1,
                "refuted_findings_count": 1,
                "manual_review_required_count": 0,
            }
        },
    )

    payload = json.loads(data.decode("utf-8"))
    by_check = {result["check_id"]: result for result in payload["check_results"]}
    assert payload["summary"]["final_audit_status"] == "failed"
    assert payload["summary"]["confirmed_errors_count"] == 1
    assert payload["summary"]["refuted_findings_count"] == 1
    assert by_check["C09"]["status"] == "fail"
    assert by_check["C09"]["deterministic_status"] == "fail"
    assert by_check["C09"]["final_status"] == "refuted"
    assert "均已排除" in by_check["C09"]["final_summary"]
    assert by_check["C07"]["final_status"] == "confirmed_error"
    assert "最终确认 1 项" in by_check["C07"]["final_summary"]


def test_final_json_export_contains_only_final_unresolved_findings() -> None:
    refuted = Finding(
        id="finding-refuted",
        task_id="task-json-final-view",
        check_id="C03",
        severity=FindingSeverity.WARN,
        code="DATE_FIELD_MISSING",
        message="规则阶段候选",
        missing_evidence=[MissingEvidence(label="中文铭牌", reason="测试候选")],
        metadata={
            "final_status": "refuted",
            "codex_review_id": "review-refuted",
            "codex_reasoning_summary": "候选已排除",
        },
    )
    confirmed_77 = Finding(
        id="finding-item-77",
        task_id="task-json-final-view",
        check_id="C07",
        severity=FindingSeverity.ERROR,
        code="CONCLUSION_MISMATCH_002",
        message="序号 77 单项结论应为符合",
        expected="符合",
        actual="/",
        missing_evidence=[MissingEvidence(label="单项结论", reason="测试确认问题")],
        metadata={"final_status": "confirmed", "item_no": "77", "codex_review_id": "review-77"},
    )
    confirmed_161 = Finding(
        id="finding-item-161",
        task_id="task-json-final-view",
        check_id="C07",
        severity=FindingSeverity.ERROR,
        code="CONCLUSION_MISMATCH_001",
        message="序号 161 空白结果的单项结论应为 /",
        expected="/",
        actual="符合",
        missing_evidence=[MissingEvidence(label="单项结论", reason="测试确认问题")],
        metadata={"final_status": "confirmed", "item_no": "161", "codex_review_id": "review-161"},
    )
    results = [
        CheckResult(
            task_id="task-json-final-view",
            check_id="C03",
            check_name="生产日期格式一致性",
            status=CheckStatus.REVIEW,
            summary="规则候选 1 项",
            findings=[refuted],
        ),
        CheckResult(
            task_id="task-json-final-view",
            check_id="C07",
            check_name="单项结论逻辑",
            status=CheckStatus.FAIL,
            summary="单项结论存在 2 项问题",
            findings=[confirmed_77, confirmed_161],
        ),
    ]

    data = export_check_results_to_json(
        results,
        task_id="task-json-final-view",
        metadata={
            "codex_audit": {
                "final_audit_status": "failed",
                "confirmed_errors_count": 2,
                "refuted_findings_count": 1,
            }
        },
        view="final",
    )

    payload = json.loads(data.decode("utf-8"))
    assert payload["view"] == "final"
    assert payload["summary"]["final_audit_status"] == "failed"
    assert payload["summary"]["confirmed_errors_count"] == 2
    assert "candidate_findings_count" not in payload["summary"]
    assert "refuted_findings_count" not in payload["summary"]
    assert [finding["id"] for finding in payload["findings"]] == [
        "finding-item-77",
        "finding-item-161",
    ]
    by_check = {result["check_id"]: result for result in payload["check_results"]}
    assert by_check["C03"]["status"] == "pass"
    assert by_check["C03"]["findings"] == []
    assert by_check["C03"]["final_status"] == "passed"
    assert "codex_reviews" not in by_check["C03"]
    assert [finding["metadata"]["item_no"] for finding in by_check["C07"]["findings"]] == ["77", "161"]
    assert "codex_audit" not in payload["metadata"]
    assert "codex_review_id" not in data.decode("utf-8")
    assert "refuted" not in data.decode("utf-8").lower()


def test_final_json_export_presents_unresolved_candidate_as_manual_review() -> None:
    unresolved = Finding(
        id="finding-needs-review",
        task_id="task-json-final-review",
        check_id="C04",
        severity=FindingSeverity.ERROR,
        code="LABEL_FIELD_UNRESOLVED",
        message="标签字段尚无法自动确认",
        missing_evidence=[MissingEvidence(label="标签字段", reason="需要人工确认")],
    )
    result = CheckResult(
        task_id="task-json-final-review",
        check_id="C04",
        check_name="样品描述表格与中文标签 OCR",
        status=CheckStatus.FAIL,
        findings=[unresolved],
    )

    data = export_check_results_to_json(
        [result],
        task_id="task-json-final-review",
        view="final",
    )

    payload = json.loads(data.decode("utf-8"))
    finding = payload["findings"][0]
    assert finding["metadata"]["user_facing_status"] == "needs_review"
    assert payload["check_results"][0]["final_status"] == "needs_review"
    assert payload["summary"]["manual_review_required_count"] == 1
    assert "candidate_issue" not in data.decode("utf-8")


def test_final_json_export_preserves_only_final_comparison_details() -> None:
    refuted = Finding(
        id="finding-final-detail",
        task_id="task-json-final-detail",
        check_id="C03",
        severity=FindingSeverity.ERROR,
        code="DATE_FIELD_MISSING",
        message="规则阶段未抽取到生产日期",
        missing_evidence=[MissingEvidence(label="生产日期", reason="等待视觉证据")],
        metadata={"final_status": "refuted"},
    )
    result = CheckResult(
        task_id="task-json-final-detail",
        check_id="C03",
        check_name="生产日期格式一致性",
        status=CheckStatus.REVIEW,
        findings=[refuted],
        metadata={
            "comparison_details": {
                "title": "旧规则候选",
                "overall_status": "needs_review",
                "fields": [{"field_key": "stale", "status": "missing"}],
            },
            "explanation_details": {
                "overall_reason": "旧候选明细",
                "comparison_rows": [{"field": "stale", "status": "missing"}],
            },
            "final_comparison_details": {
                "title": "生产日期格式一致性",
                "overall_status": "passed",
                "overall_reason": "报告首页与中文标签图像一致。",
                "sources": [],
                "fields": [
                    {
                        "field_key": "production_date",
                        "field_label": "生产日期",
                        "status": "match",
                        "reason": "两处日期一致。",
                        "left": {"label": "报告首页摘录", "raw_text": "2026-01-08"},
                        "right": {"label": "中文标签图像摘录", "raw_text": "2026-01-08"},
                    }
                ],
            },
        },
    )

    data = export_check_results_to_json(
        [result],
        task_id="task-json-final-detail",
        view="final",
    )

    payload = json.loads(data.decode("utf-8"))
    exported = payload["check_results"][0]
    assert exported["metadata"]["comparison_details"]["fields"][0]["field_key"] == "production_date"
    assert "final_comparison_details" not in exported["metadata"]
    assert "explanation_details" not in exported["metadata"]
    assert "旧规则候选" not in data.decode("utf-8")
