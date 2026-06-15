import json
from pathlib import Path

from app.domain.result import CheckStatus
from app.testing.golden_runner import collect_expected_cases, normalize_result
from tests.fixtures.export_result_builder import sample_check_results


FIXTURE_EXPECTED_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "golden" / "expected"


def test_normalize_result_handles_pydantic_models_and_rounds_floats() -> None:
    result = sample_check_results()[0]
    payload = normalize_result(
        {
            "result": result,
            "status": CheckStatus.FAIL,
            "ratio": 0.3333333333,
            "nested": [{"value": 1.23456789}],
        }
    )

    assert payload["result"]["check_id"] == "C01"
    assert payload["result"]["status"] == "fail"
    assert payload["result"]["findings"][0]["expected"] == "ABC-1"
    assert payload["ratio"] == 0.333333
    assert payload["nested"][0]["value"] == 1.234568


def test_migrated_expected_files_are_valid_legacy_snapshots() -> None:
    cases = collect_expected_cases(FIXTURE_EXPECTED_ROOT)

    assert len(cases) == 10
    for case in cases:
        with case.expected_json_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        assert isinstance(payload, dict)
        assert case.expected_json_path.name in {
            "report_check.expected.json",
            "ptr_compare.expected.json",
        }
        if case.kind == "report_check":
            assert "summary" in payload
            assert "checks" in payload
        else:
            assert "summary" in payload
            assert "clauses" in payload
