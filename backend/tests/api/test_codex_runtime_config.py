from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_codex_runtime_config_returns_default_and_deduplicated_options() -> None:
    client = TestClient(
        create_app(
            Settings(
                codex_audit_model="gpt-5.4",
                codex_audit_model_options="gpt-5.3-codex,gpt-5.4,gpt-5.3-codex",
                codex_audit_reasoning_effort="high",
                codex_audit_reasoning_effort_options="medium,high,xhigh",
                _env_file=None,
            )
        )
    )

    response = client.get("/api/runtime-config/codex")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_model"] == "gpt-5.4"
    assert payload["model_options"] == [
        "gpt-5.4",
        "gpt-5.3-codex",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "gpt-5.6-sol",
    ]
    assert payload["default_reasoning_effort"] == "high"
    assert payload["reasoning_effort_options"] == ["medium", "high", "xhigh"]
    assert payload["default_profile"] == "custom"
    assert payload["runtime_config_version"] == "codex-runtime-v2"
    assert [profile["profile_id"] for profile in payload["profiles"]] == [
        "balanced",
        "fast",
        "deep",
        "custom",
    ]
    assert payload["profiles"][0] == {
        "profile_id": "balanced",
        "label": "平衡",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "timeout_seconds": 600,
        "max_targets_per_batch": 3,
        "max_parallel_jobs": 2,
    }


def test_codex_runtime_config_does_not_expose_other_settings() -> None:
    client = TestClient(create_app(Settings(openai_api_key="secret", _env_file=None)))

    payload = client.get("/api/runtime-config/codex").json()

    assert payload["default_model"] == "gpt-5.6-terra"
    assert payload["default_reasoning_effort"] == "medium"
    assert payload["default_profile"] == "balanced"
    assert payload["runtime_config_version"] == "codex-runtime-v2"
    assert "openai_api_key" not in payload
