from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.llm.vision_service import VLMService, create_vlm_service, extract_text_with_vlm
from app.infrastructure.llm.types import VLMServiceConfig


def test_vlm_config_defaults_and_custom_base_url() -> None:
    config = VLMServiceConfig()

    assert config.provider == "openrouter"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.is_configured is False
    assert VLMServiceConfig(api_key="key").is_configured is True


def test_parse_json_content_tolerates_code_fences() -> None:
    service = VLMService(config=VLMServiceConfig(api_key="key"))

    assert service.parse_json_content('```json\n{"fields":{"model_spec":"RMD01"}}\n```') == {
        "fields": {"model_spec": "RMD01"}
    }


@pytest.mark.asyncio
async def test_extract_label_fields_from_image_returns_structured_enhancement(tmp_path: Path) -> None:
    image_path = tmp_path / "label.png"
    image_path.write_bytes(b"fake-image")
    service = VLMService(config=VLMServiceConfig(api_key="key", model="vision-model"))
    response = MagicMock()
    response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"raw_text":"规格型号：RMD01",'
                        '"fields":{"model_spec":"RMD01","production_date":"20251230"},'
                        '"confidence":0.91,"uncertain_fields":[]}'
                    )
                }
            }
        ],
        "usage": {"total_tokens": 20},
    }
    response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    service._client = mock_client

    result = await service.extract_label_fields_from_image(image_path, base_text="规格型号：RMD0I")

    assert result.raw_text == "规格型号：RMD01"
    assert result.fields["model_spec"] == "RMD01"
    assert result.confidence == 0.91
    assert result.provider == "openrouter"
    assert "verdict" not in result.metadata


@pytest.mark.asyncio
async def test_extract_text_with_vlm_returns_error_when_service_unavailable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.infrastructure.llm.vision_service.create_vlm_service", lambda: None)

    result = await extract_text_with_vlm(tmp_path / "missing.png")

    assert result.text == ""
    assert result.error == "VLM not configured"


def test_create_vlm_service_returns_none_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr("app.infrastructure.llm.vision_service.get_settings", lambda: type("S", (), {
        "openrouter_api_key": "",
        "openai_api_key": "",
        "deepseek_api_key": "",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    })())

    assert create_vlm_service() is None
