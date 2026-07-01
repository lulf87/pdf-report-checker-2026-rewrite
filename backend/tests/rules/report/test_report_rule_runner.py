from app.domain.finding import FindingSeverity
from app.domain.report import ReportDocument
from app.domain.result import CheckResult, CheckStatus
from app.rules.report.context import CheckContext
from app.rules.report.runner import ReportRule, ReportRuleRunner, default_report_rules


def _passing_rule(check_id: str):
    return lambda document, context: CheckResult(
        task_id=context.task_id,
        check_id=check_id,
        check_name=f"{check_id} test rule",
        status=CheckStatus.PASS,
    )


def test_default_report_rules_register_c01_to_c11_in_order() -> None:
    assert [rule.check_id for rule in default_report_rules()] == [
        "C01",
        "C02",
        "C03",
        "C04",
        "C05",
        "C06",
        "C07",
        "C08",
        "C09",
        "C10",
        "C11",
    ]


def test_report_rule_runner_runs_all_rules_and_summarizes_results() -> None:
    runner = ReportRuleRunner(
        rules=[
            ReportRule("C01", "one", _passing_rule("C01")),
            ReportRule("C02", "two", _passing_rule("C02")),
        ]
    )

    result = runner.run(ReportDocument(), CheckContext(task_id="task-runner"))

    assert [item.check_id for item in result.results] == ["C01", "C02"]
    assert result.summary.total_checks == 2
    assert result.summary.pass_count == 2
    assert result.findings == []


def test_report_rule_runner_emits_rule_progress_callbacks() -> None:
    events: list[tuple[str, str, str | None]] = []

    def on_check_start(check_id: str, check_name: str) -> None:
        events.append(("start", check_id, check_name))

    def on_check_complete(result: CheckResult) -> None:
        events.append(("complete", result.check_id, result.status.value))

    runner = ReportRuleRunner(
        rules=[
            ReportRule("C01", "one", _passing_rule("C01")),
            ReportRule(
                "C03",
                "three",
                lambda document, context: CheckResult(
                    task_id=context.task_id,
                    check_id="C03",
                    check_name="C03 test rule",
                    status=CheckStatus.SKIP,
                ),
            ),
        ]
    )

    runner.run(
        ReportDocument(),
        CheckContext(
            task_id="task-runner",
            on_check_start=on_check_start,
            on_check_complete=on_check_complete,
        ),
    )

    assert events == [
        ("start", "C01", "one"),
        ("complete", "C01", "pass"),
        ("start", "C03", "three"),
        ("complete", "C03", "skip"),
    ]


def test_report_rule_runner_isolates_single_rule_exception_as_system_error() -> None:
    def broken_rule(document, context):
        raise RuntimeError("boom")

    runner = ReportRuleRunner(
        rules=[
            ReportRule("C01", "one", _passing_rule("C01")),
            ReportRule("C02", "broken", broken_rule),
            ReportRule("C03", "three", _passing_rule("C03")),
        ]
    )

    result = runner.run(ReportDocument(), CheckContext(task_id="task-runner"))

    assert [item.status for item in result.results] == [
        CheckStatus.PASS,
        CheckStatus.SYSTEM_ERROR,
        CheckStatus.PASS,
    ]
    assert result.summary.system_error_count == 1
    assert result.findings[0].check_id == "C02"
    assert result.findings[0].severity == FindingSeverity.WARN
    assert result.findings[0].code == "REPORT_RULE_INTERNAL_ERROR"
