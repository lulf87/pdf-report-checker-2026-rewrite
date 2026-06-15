from pathlib import Path

from app.testing.golden_runner import collect_expected_cases


FIXTURE_EXPECTED_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "golden" / "expected"


def test_migrated_expected_inventory_is_available() -> None:
    cases = collect_expected_cases(FIXTURE_EXPECTED_ROOT)

    assert FIXTURE_EXPECTED_ROOT.exists()
    assert {case.sample_id for case in cases} == {"1539", "2795", "3940", "5780", "5782"}
    assert {case.kind for case in cases} == {"report_check", "ptr_compare"}
    assert all(case.expected_json_path.is_file() for case in cases)


def test_expected_inventory_does_not_include_macos_metadata() -> None:
    if not FIXTURE_EXPECTED_ROOT.exists():
        raise AssertionError(f"missing expected fixture root: {FIXTURE_EXPECTED_ROOT}")

    migrated_files = [path.name for path in FIXTURE_EXPECTED_ROOT.rglob("*") if path.is_file()]

    assert ".DS_Store" not in migrated_files
