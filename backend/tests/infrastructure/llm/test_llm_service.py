from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infrastructure.llm.llm_service import LLMService, create_llm_service
from app.infrastructure.llm.types import LLMMode, LLMProvider, LLMServiceConfig


def test_llm_config_defaults_and_provider_base_urls() -> None:
    config = LLMServiceConfig()

    assert config.provider == LLMProvider.OPENAI
    assert config.model == "gpt-4o-mini"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.is_configured is False
    assert LLMServiceConfig(provider=LLMProvider.DEEPSEEK).base_url == "https://api.deepseek.com/v1"


@pytest.mark.asyncio
async def test_enhance_text_returns_original_when_disabled_or_unconfigured() -> None:
    service = LLMService(config=LLMServiceConfig(mode=LLMMode.DISABLED))

    result = await service.enhance_text("raw OCR")

    assert result.enhanced_text == "raw OCR"
    assert result.used is False
    assert result.error == "LLM disabled"
    assert result.metadata.get("verdict") is None


@pytest.mark.asyncio
async def test_enhance_text_success_uses_mocked_http_client_without_verdict() -> None:
    service = LLMService(config=LLMServiceConfig(api_key="test-key", mode=LLMMode.ENHANCE))
    response = MagicMock()
    response.json.return_value = {
        "choices": [{"message": {"content": "corrected text"}}],
        "usage": {"total_tokens": 12},
    }
    response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    service._client = mock_client

    result = await service.enhance_text("raw text", context="OCR")

    assert result.enhanced_text == "corrected text"
    assert result.used is True
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert "verdict" not in result.metadata
    mock_client.post.assert_awaited_once()


def test_create_llm_service_respects_disabled_mode() -> None:
    assert create_llm_service(mode=LLMMode.DISABLED) is None
