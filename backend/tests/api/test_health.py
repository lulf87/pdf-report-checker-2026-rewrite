from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_uses_configured_app_metadata() -> None:
    settings = Settings(
        app_name="Custom Report Checker API",
        app_service="custom-report-checker",
        app_version="9.9.9",
        cors_origins=["http://example.test"],
    )
    client = TestClient(create_app(settings=settings))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "custom-report-checker",
        "version": "9.9.9",
    }


def test_settings_keep_legacy_ocr_llm_vlm_and_ptr_table_vlm_options(monkeypatch: MonkeyPatch) -> None:
    for name in (
        "OCR_LANGUAGE",
        "LLM_MODE",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "VLM_PRIMARY_MODEL",
        "VLM_SECONDARY_MODEL",
        "VLM_SECONDARY_TRIGGER_CONFIDENCE",
        "PTR_TABLE_VLM_ENABLED",
        "PTR_TABLE_VLM_MIN_ROWS",
        "PTR_TABLE_VLM_MAX_PAGES",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.ocr_language == "ch"
    assert settings.llm_mode == "fallback"
    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.vlm_primary_model == "qwen/qwen3-vl-8b-instruct"
    assert settings.vlm_secondary_model == "qwen/qwen3-vl-30b-a3b-instruct"
    assert settings.vlm_secondary_trigger_confidence == 0.75
    assert settings.ptr_table_vlm_enabled is False
    assert settings.ptr_table_vlm_min_rows == 20
    assert settings.ptr_table_vlm_max_pages == 4
