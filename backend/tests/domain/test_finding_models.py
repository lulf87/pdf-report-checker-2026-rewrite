import pytest
from pydantic import ValidationError

from app.domain.common import Evidence, EvidenceMethod, Location, SourceType
from app.domain.finding import Confidence, Finding, FindingSeverity, MissingEvidence, Severity
from app.domain.result import CheckResult, CheckStatus, CheckSummary


def test_finding_severity_enum_keeps_public_values_and_legacy_alias() -> None:
    assert FindingSeverity.ERROR.value == "error"
    assert FindingSeverity.WARN.value == "warn"
    assert FindingSeverity.INFO.value == "info"
    assert Severity.ERROR is FindingSeverity.ERROR


def test_error_and_warn_findings_require_traceable_evidence_or_missing_evidence() -> None:
    with pytest.raises(ValidationError, match="evidence or missing_evidence"):
        Finding(
            id="finding-without-trace",
            task_id="task-1",
            check_id="C01",
            severity=FindingSeverity.ERROR,
            code="C01_FIELD_MISMATCH",
            message="首页与第三页字段不一致",
        )

    missing = MissingEvidence(
        label="第三页型号规格",
        reason="PDF 文本层未抽取到字段",
        expected_source=SourceType.REPORT,
    )
    finding = Finding(
        id="finding-with-missing-evidence",
        task_id="task-1",
        check_id="C01",
        severity=FindingSeverity.WARN,
        code="C01_FIELD_MISSING",
        message="第三页型号规格缺少可定位证据",
        missing_evidence=[missing],
    )

    assert finding.confidence == Confidence.MEDIUM
    assert finding.model_dump(mode="json")["missing_evidence"][0]["expected_source"] == "report"


def test_check_summary_counts_results_and_finding_severities() -> None:
    location = Location(source_type=SourceType.REPORT, page_number=3)
    evidence = Evidence(
        id="ev-1",
        source_type=SourceType.REPORT,
        location=location,
        raw_text="型号规格：ABC-1",
        method=EvidenceMethod.PDF_TEXT,
    )
    error_finding = Finding(
        id="finding-error",
        task_id="task-1",
        check_id="C01",
        severity=FindingSeverity.ERROR,
        code="C01_FIELD_MISMATCH",
        message="字段不一致",
        evidence=[evidence],
    )
    warn_finding = Finding(
        id="finding-warn",
        task_id="task-1",
        check_id="C02",
        severity=FindingSeverity.WARN,
        code="C02_LABEL_MISSING",
        message="标签证据不足",
        missing_evidence=[
            MissingEvidence(
                label="中文标签",
                reason="OCR 未返回可定位字段",
                expected_source=SourceType.REPORT,
            )
        ],
    )
    results = [
        CheckResult(task_id="task-1", check_id="C01", check_name="首页与第三页一致性", status=CheckStatus.FAIL, findings=[error_finding]),
        CheckResult(task_id="task-1", check_id="C02", check_name="第三页扩展字段", status=CheckStatus.REVIEW, findings=[warn_finding]),
        CheckResult(task_id="task-1", check_id="C03", check_name="生产日期", status=CheckStatus.PASS),
    ]

    assert results[0].severity == FindingSeverity.ERROR
    assert results[1].severity == FindingSeverity.WARN
    assert results[2].severity == FindingSeverity.INFO

    summary = CheckSummary.from_results(results)
    payload = summary.model_dump(mode="json")

    assert payload == {
        "total_checks": 3,
        "pass_count": 1,
        "fail_count": 1,
        "review_count": 1,
        "skip_count": 0,
        "system_error_count": 0,
        "error_count": 1,
        "warn_count": 1,
        "info_count": 0,
    }
