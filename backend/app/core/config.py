"""Application settings for the FastAPI backend."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    app_name: str = Field(default="Report Checker API", description="FastAPI application title.")
    app_service: str = Field(default="report-checker-api", description="Service identifier for health checks.")
    app_description: str = Field(
        default="Backend service for medical device report verification and PTR comparison.",
        description="OpenAPI description.",
    )
    app_version: str = Field(default="0.1.0", description="Application version.")
    log_level: str = Field(default="INFO", description="Python logging level name.")

    host: str = Field(default="127.0.0.1", description="Server host address.")
    port: int = Field(default=8000, description="Server port.")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins for the frontend dev server.",
    )

    ocr_language: str = Field(default="ch", description="OCR language code.")

    llm_mode: Literal["enhance", "fallback", "disabled"] = Field(
        default="fallback",
        description="LLM mode: enhance, fallback, or disabled.",
    )
    llm_provider: Literal["openai", "deepseek"] = Field(
        default="openai",
        description="LLM provider name.",
    )
    openai_api_key: str = Field(default="", description="OpenAI API key.")
    deepseek_api_key: str = Field(default="", description="DeepSeek API key.")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key for VLM calls.")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model identifier.")
    vlm_primary_model: str = Field(
        default="qwen/qwen3-vl-8b-instruct",
        description="Primary VLM model for OCR or visual evidence enhancement.",
    )
    vlm_secondary_model: str = Field(
        default="qwen/qwen3-vl-30b-a3b-instruct",
        description="Secondary VLM model used when primary confidence is low.",
    )
    vlm_secondary_trigger_confidence: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Trigger threshold for secondary VLM enhancement.",
    )
    ptr_table_vlm_enabled: bool = Field(
        default=False,
        description="Whether PTR table VLM enhancement is enabled.",
    )
    ptr_table_vlm_min_rows: int = Field(
        default=20,
        ge=1,
        description="Minimum PTR table row count for optional VLM enhancement.",
    )
    ptr_table_vlm_max_pages: int = Field(
        default=4,
        ge=1,
        description="Maximum PTR table pages sent to one VLM enhancement call.",
    )
    codex_audit_enabled: bool = Field(
        default=False,
        description="Whether controlled Codex CLI runtime audit is enabled.",
    )
    codex_audit_backend: Literal["disabled", "fake", "codex-cli"] = Field(
        default="disabled",
        description="Codex audit backend: disabled, fake, or codex-cli.",
    )
    codex_audit_allow_real_execution: bool = Field(
        default=False,
        description="Whether the codex-cli backend may execute the real Codex CLI process.",
    )
    codex_audit_timeout_seconds: int = Field(
        default=120,
        ge=1,
        description="Timeout in seconds for real Codex CLI audit execution.",
    )
    codex_audit_runtime_dir: str = Field(
        default="runtime/codex_audit",
        description="Runtime root for controlled Codex audit evidence workspaces.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
