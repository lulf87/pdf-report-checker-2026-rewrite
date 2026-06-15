from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.infrastructure.llm.types import (
    LLMEnhancementResult,
    LLMMode,
    LLMProvider,
    LLMServiceConfig,
)


class LLMService:
    def __init__(self, config: LLMServiceConfig | None = None) -> None:
        if config is None:
            settings = get_settings()
            provider = LLMProvider.DEEPSEEK if settings.llm_provider == "deepseek" else LLMProvider.OPENAI
            config = LLMServiceConfig(
                provider=provider,
                mode=LLMMode(settings.llm_mode),
                model=settings.llm_model,
                api_key=settings.deepseek_api_key if provider == LLMProvider.DEEPSEEK else settings.openai_api_key,
            )
        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout))
        return self._client

    async def enhance_text(self, text: str, context: str = "") -> LLMEnhancementResult:
        if self.config.mode == LLMMode.DISABLED:
            return LLMEnhancementResult(enhanced_text=text, used=False, error="LLM disabled")
        if not self.config.is_configured:
            return LLMEnhancementResult(enhanced_text=text, used=False, error="LLM not configured")

        system_prompt = (
            "You enhance extracted technical document text. Preserve meaning, do not decide "
            "whether any report check passes or fails, and output only corrected text."
        )
        user_prompt = f"Text:\n{text}"
        if context:
            user_prompt += f"\n\nContext:\n{context}"
        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        enhanced = text
        if data.get("choices"):
            enhanced = str(data["choices"][0].get("message", {}).get("content", "")).strip()
        return LLMEnhancementResult(
            enhanced_text=enhanced,
            used=True,
            provider=self.config.provider.value,
            model=self.config.model,
            usage=data.get("usage", {}),
        )

    async def verify_extraction(self, text: str, expected_fields: list[str]) -> dict[str, Any]:
        if not self.config.is_configured:
            return {"verified": False, "error": "LLM not configured"}
        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return JSON describing extraction support only. Do not include pass/fail verdicts."
                        ),
                    },
                    {"role": "user", "content": f"Expected fields: {expected_fields}\n\n{text}"},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        import json

        content = response.json()["choices"][0]["message"]["content"]
        payload = json.loads(content)
        payload.pop("verdict", None)
        return payload

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def create_llm_service(mode: LLMMode | str = LLMMode.DISABLED) -> LLMService | None:
    resolved_mode = LLMMode(mode)
    if resolved_mode == LLMMode.DISABLED:
        return None
    settings = get_settings()
    provider = LLMProvider.DEEPSEEK if settings.llm_provider == "deepseek" else LLMProvider.OPENAI
    api_key = settings.deepseek_api_key if provider == LLMProvider.DEEPSEEK else settings.openai_api_key
    if not api_key:
        return None
    return LLMService(
        config=LLMServiceConfig(
            provider=provider,
            mode=resolved_mode,
            model=settings.llm_model,
            api_key=api_key,
        )
    )
