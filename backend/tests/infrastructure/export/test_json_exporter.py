import json

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
