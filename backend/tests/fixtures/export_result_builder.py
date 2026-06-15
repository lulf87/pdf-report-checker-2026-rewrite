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
            metadata={"rule_version": "test"},
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
