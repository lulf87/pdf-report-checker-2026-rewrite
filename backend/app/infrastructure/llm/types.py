from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LLMProvider(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class LLMMode(StrEnum):
    ENHANCE = "enhance"
    FALLBACK = "fallback"
    DISABLED = "disabled"


class LLMServiceConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    mode: LLMMode = LLMMode.FALLBACK
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 30
    max_retries: int = 3

    def model_post_init(self, __context: Any) -> None:
        if self.base_url:
            return
        if self.provider == LLMProvider.OPENAI:
            self.base_url = "https://api.openai.com/v1"
        elif self.provider == LLMProvider.DEEPSEEK:
            self.base_url = "https://api.deepseek.com/v1"

    @property
    def is_configured(self) -> bool:
        return self.mode != LLMMode.DISABLED and bool(self.api_key and self.model and self.base_url)


class VLMServiceConfig(BaseModel):
    provider: str = "openrouter"
    model: str = "google/gemini-2.0-flash-exp"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 60

    def model_post_init(self, __context: Any) -> None:
        if self.base_url:
            return
        if self.provider == "openrouter":
            self.base_url = "https://openrouter.ai/api/v1"
        elif self.provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        elif self.provider == "deepseek":
            self.base_url = "https://api.deepseek.com/v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)


class LLMEnhancementResult(BaseModel):
    enhanced_text: str
    used: bool = False
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VLMTextResult(BaseModel):
    text: str = ""
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VLMFieldExtractionResult(BaseModel):
    raw_text: str = ""
    fields: dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.0
    uncertain_fields: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
