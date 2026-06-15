from __future__ import annotations

import json
import re
from base64 import b64encode
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.infrastructure.llm.types import VLMFieldExtractionResult, VLMServiceConfig, VLMTextResult


class VLMService:
    def __init__(self, config: VLMServiceConfig | None = None) -> None:
        if config is None:
            settings = get_settings()
            config = VLMServiceConfig(model=settings.llm_model, api_key=settings.openrouter_api_key)
        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout))
        return self._client

    def parse_json_content(self, content: str) -> dict[str, Any]:
        text = (content or "").strip()
        if not text:
            return {}
        for candidate in [
            text,
            re.sub(r"^```(?:json)?\s*", "", re.sub(r"\s*```$", "", text), flags=re.IGNORECASE),
            *(re.findall(r"\{[\s\S]*\}", text) or []),
        ]:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return {}

    async def extract_text_from_image(
        self,
        image_path: str | Path,
        prompt: str = "Extract all text from this image. Preserve formatting and structure.",
        expect_json: bool = False,
    ) -> VLMTextResult:
        if not self.config.is_configured:
            return VLMTextResult(text="", error="VLM not configured")

        path = Path(image_path)
        mime_type = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        encoded = b64encode(path.read_bytes()).decode("utf-8")
        request_data: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                    ],
                }
            ],
            "temperature": 0.1,
        }
        if expect_json:
            request_data["response_format"] = {"type": "json_object"}

        response = await self.client.post(
            f"{self.config.base_url}/chat/completions",
            headers=self._headers(),
            json=request_data,
        )
        response.raise_for_status()
        data = response.json()
        text = ""
        if data.get("choices"):
            text = str(data["choices"][0].get("message", {}).get("content", "")).strip()
        return VLMTextResult(
            text=text,
            provider=self.config.provider,
            model=self.config.model,
            usage=data.get("usage", {}),
        )

    async def extract_label_fields_from_image(self, image_path: str | Path, base_text: str = "") -> VLMFieldExtractionResult:
        prompt = (
            "你是医疗器械标签OCR修订助手。只提取图片中的标签文本和字段，"
            "不要判断报告核对是否通过。返回严格JSON。"
        )
        if base_text.strip():
            prompt += f"\n已知OCR文本:\n{base_text}"
        text_result = await self.extract_text_from_image(image_path, prompt=prompt, expect_json=True)
        if text_result.error:
            return VLMFieldExtractionResult(error=text_result.error, provider=self.config.provider, model=self.config.model)
        payload = self.parse_json_content(text_result.text)
        fields_payload = payload.get("fields", {}) if isinstance(payload, dict) else {}
        if not isinstance(fields_payload, dict):
            fields_payload = {}
        allowed = {"model_spec", "production_date", "batch_number", "serial_number", "registrant", "registrant_address"}
        fields = {key: str(fields_payload.get(key, "") or "").strip() for key in allowed if str(fields_payload.get(key, "") or "").strip()}
        try:
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        uncertain = payload.get("uncertain_fields", [])
        return VLMFieldExtractionResult(
            raw_text=str(payload.get("raw_text", "") or "").strip(),
            fields=fields,
            confidence=max(0.0, min(confidence, 1.0)),
            uncertain_fields=uncertain if isinstance(uncertain, list) else [],
            provider=text_result.provider,
            model=text_result.model,
            usage=text_result.usage,
            metadata={"raw_response_text": text_result.text},
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.provider == "openrouter":
            headers["HTTP-Referer"] = "https://report-checker-pro.app"
        return headers

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _non_empty(value: Any) -> str:
    return str(value or "").strip()


def create_vlm_service(model_override: str | None = None, provider_override: str | None = None) -> VLMService | None:
    settings = get_settings()
    provider = _non_empty(provider_override or settings.llm_provider)
    keys = {
        "openrouter": _non_empty(settings.openrouter_api_key),
        "openai": _non_empty(settings.openai_api_key),
        "deepseek": _non_empty(settings.deepseek_api_key),
    }
    if provider not in keys or not keys[provider]:
        provider = next((name for name, key in keys.items() if key), "")
    if not provider:
        return None
    return VLMService(
        config=VLMServiceConfig(
            provider=provider,
            model=_non_empty(model_override or settings.llm_model) or "gpt-4o-mini",
            api_key=keys[provider],
        )
    )


async def extract_text_with_vlm(image_path: str | Path, prompt: str = "Extract all text from this image.") -> VLMTextResult:
    service = create_vlm_service()
    if service is None:
        return VLMTextResult(text="", error="VLM not configured")
    return await service.extract_text_from_image(image_path, prompt=prompt)
