from app.application.performance_profile import PerformanceProfile


def test_performance_profile_records_stages_with_injected_clock() -> None:
    values = iter([10.0, 10.25, 11.0, 11.75])
    profile = PerformanceProfile(clock=lambda: next(values))

    with profile.measure("parse_pdf", page_count=12):
        pass
    with profile.measure("run_rules"):
        pass

    payload = profile.to_dict()

    assert payload["stages"] == [
        {"name": "parse_pdf", "duration_seconds": 0.25, "metadata": {"page_count": 12}},
        {"name": "run_rules", "duration_seconds": 0.75, "metadata": {}},
    ]
    assert payload["totals"]["parse_pdf"] == 0.25
    assert payload["totals"]["run_rules"] == 0.75
    assert payload["total_seconds"] == 1.0


def test_performance_profile_merges_package_profiles() -> None:
    profile = PerformanceProfile(clock=lambda: 1.0)

    profile.add_package_profile(
        {
            "package_id": "pkg-1",
            "target_count": 5,
            "codex_exec_seconds": 12.5,
            "image_count": 3,
            "image_bytes": 4096,
            "prompt_size_bytes": 2048,
            "evidence_package_size_bytes": 8192,
        }
    )

    payload = profile.to_dict()

    assert payload["packages"][0]["package_id"] == "pkg-1"
    assert payload["package_totals"]["package_count"] == 1
    assert payload["package_totals"]["target_count"] == 5
    assert payload["package_totals"]["codex_exec_seconds"] == 12.5
    assert payload["package_totals"]["image_count"] == 3
    assert payload["package_totals"]["image_bytes"] == 4096
