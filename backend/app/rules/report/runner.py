from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.domain.common import Confidence, Evidence, EvidenceMethod, SourceType
from app.domain.finding import Finding, FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckResult, CheckStatus, CheckSummary
from app.rules.report.c01_home_vs_third import check_c01_home_vs_third
from app.rules.report.c02_third_page_extended_fields import check_c02_third_page_extended_fields
from app.rules.report.c03_production_date import check_c03_production_date
from app.rules.report.c04_sample_description import check_c04_sample_description
from app.rules.report.c05_photo_coverage import check_c05_photo_coverage
from app.rules.report.c06_label_coverage import check_c06_label_coverage
from app.rules.report.c07_item_conclusion import check_c07_item_conclusion
from app.rules.report.c08_non_empty import check_c08_non_empty_fields
from app.rules.report.c09_sequence import check_c09_sequence
from app.rules.report.c10_continuation import check_c10_continuation
from app.rules.report.c11_page_number import check_c11_page_number
from app.rules.report.context import CheckContext


RuleCallable = Callable[[ReportDocument, CheckContext], CheckResult]


@dataclass(frozen=True)
class ReportRule:
    check_id: str
    check_name: str
    run: RuleCallable


class ReportRuleRunResult(BaseModel):
    task_id: str
    results: list[CheckResult] = Field(default_factory=list)
    summary: CheckSummary
    findings: list[Finding] = Field(default_factory=list)


class ReportRuleRunner:
    def __init__(self, rules: Sequence[ReportRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else default_report_rules()

    def run(self, document: ReportDocument, context: CheckContext | None = None) -> ReportRuleRunResult:
        context = context or CheckContext()
        results: list[CheckResult] = []
        for rule in self.rules:
            try:
                results.append(rule.run(document, context))
            except Exception as exc:  # pragma: no cover - behavior covered by runner tests
                results.append(_system_error_result(rule, context, exc))

        findings = [finding for result in results for finding in result.findings]
        return ReportRuleRunResult(
            task_id=context.task_id,
            results=results,
            summary=CheckSummary.from_results(results),
            findings=findings,
        )


def default_report_rules() -> list[ReportRule]:
    return [
        ReportRule("C01", "首页与第三页一致性", check_c01_home_vs_third),
        ReportRule("C02", "第三页扩展字段与中文标签 OCR", check_c02_third_page_extended_fields),
        ReportRule("C03", "生产日期格式一致性", check_c03_production_date),
        ReportRule("C04", "样品描述表格与中文标签 OCR", check_c04_sample_description),
        ReportRule("C05", "照片覆盖", check_c05_photo_coverage),
        ReportRule("C06", "中文标签覆盖", check_c06_label_coverage),
        ReportRule("C07", "单项结论逻辑", check_c07_item_conclusion),
        ReportRule("C08", "检验项目非空字段", check_c08_non_empty_fields),
        ReportRule("C09", "检验项目序号连续性", check_c09_sequence),
        ReportRule("C10", "续表标记", check_c10_continuation),
        ReportRule("C11", "页码连续性", check_c11_page_number),
    ]


def _system_error_result(rule: ReportRule, context: CheckContext, exc: Exception) -> CheckResult:
    evidence = Evidence(
        id=f"{context.task_id}-{rule.check_id.lower()}-system-error",
        source_type=SourceType.SYSTEM,
        raw_text=f"{exc.__class__.__name__}: {exc}",
        value=str(exc),
        method=EvidenceMethod.SYSTEM,
        confidence=Confidence.HIGH,
    )
    finding = Finding(
        id=f"{context.task_id}-{rule.check_id.lower()}-internal-error",
        task_id=context.task_id,
        check_id=rule.check_id,
        severity=FindingSeverity.WARN,
        code="REPORT_RULE_INTERNAL_ERROR",
        message=f"{rule.check_id} 规则执行异常",
        evidence=[evidence],
        confidence=Confidence.HIGH,
        metadata={"exception_type": exc.__class__.__name__},
    )
    return CheckResult(
        task_id=context.task_id,
        check_id=rule.check_id,
        check_name=rule.check_name,
        status=CheckStatus.SYSTEM_ERROR,
        summary=f"{rule.check_id} 规则执行异常，已隔离为系统错误",
        findings=[finding],
        evidence=[evidence],
    )


__all__ = ["ReportRule", "ReportRuleRunner", "ReportRuleRunResult", "default_report_rules"]
