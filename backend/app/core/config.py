"""Application settings for the FastAPI backend."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.application.codex_model_config import (
    normalize_codex_model,
    normalize_codex_reasoning_effort,
    parse_codex_model_options,
    parse_codex_reasoning_effort_options,
)


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
    codex_cli_path: str = Field(
        default="codex",
        description="Codex CLI executable used by mandatory local runtime audit.",
    )
    codex_audit_model: str | None = Field(
        default="gpt-5.6-terra",
        description="Default model passed explicitly to Codex CLI audit with --model.",
    )
    codex_audit_model_options: str | None = Field(
        default="gpt-5.6-terra,gpt-5.6-luna,gpt-5.6-sol",
        description="Optional comma-separated Codex model identifiers exposed as frontend presets.",
    )
    codex_audit_reasoning_effort: str = Field(
        default="medium",
        description="Default reasoning effort passed explicitly to Codex CLI audit.",
    )
    codex_audit_reasoning_effort_options: str = Field(
        default="low,medium,high,xhigh,max",
        description="Comma-separated reasoning effort values exposed to the frontend.",
    )
    codex_audit_enabled: bool = Field(
        default=True,
        description="Deprecated compatibility field; product runtime always requires Codex CLI audit.",
    )
    codex_audit_backend: Literal["disabled", "fake", "codex-cli"] = Field(
        default="codex-cli",
        description="Deprecated compatibility field; product runtime always uses codex-cli.",
    )
    codex_audit_allow_real_execution: bool = Field(
        default=True,
        description="Deprecated compatibility field; product runtime requires real local Codex CLI execution.",
    )
    codex_audit_timeout_seconds: int = Field(
        default=600,
        ge=1,
        description="Timeout in seconds for real Codex CLI audit execution.",
    )
    codex_audit_max_targets_per_task: int = Field(
        default=5,
        description="Maximum Codex audit targets emitted for one business task; <=0 disables audit target emission.",
    )
    codex_audit_max_targets_per_batch: int = Field(
        default=3,
        description="Maximum Codex audit targets emitted for the current batch; <=0 disables audit target emission.",
    )
    codex_audit_max_parallel_jobs: int = Field(
        default=2,
        ge=1,
        description="Maximum number of independent Codex audit packages reviewed concurrently.",
    )
    codex_audit_missing_target_retry_batch_size: int = Field(
        default=1,
        ge=1,
        description="Maximum Codex targets per retry package when a runner output is missing target reviews.",
    )
    codex_audit_included_check_ids: str | None = Field(
        default=None,
        description="Optional comma-separated check IDs allowed for Codex audit targets.",
    )
    codex_audit_included_finding_codes: str | None = Field(
        default=None,
        description="Optional comma-separated finding codes allowed for Codex audit targets.",
    )
    codex_audit_excluded_check_ids: str | None = Field(
        default=None,
        description="Optional comma-separated check IDs excluded from Codex audit targets.",
    )
    codex_audit_priority_check_ids: str = Field(
        default="C02,C03,C07,C04,C05,C06",
        description="Comma-separated priority order for report Codex audit check IDs.",
    )
    codex_audit_runtime_dir: str = Field(
        default="runtime/codex_audit",
        description="Runtime root for controlled Codex audit evidence workspaces.",
    )
    codex_audit_cache_dir: str = Field(
        default="runtime/codex_audit_cache",
        description="Runtime root for schema-valid succeeded Codex audit review cache entries.",
    )
    task_repository_dir: str = Field(
        default="runtime/tasks",
        description="Runtime directory for restart-safe task state and result storage.",
    )
    codex_audit_sandbox: Literal["read-only"] = Field(
        default="read-only",
        description="Codex CLI sandbox mode. Product runtime only supports read-only.",
    )
    codex_audit_ephemeral: bool = Field(
        default=True,
        description="Whether Codex CLI audit runs with --ephemeral.",
    )

    @field_validator("codex_audit_model", mode="before")
    @classmethod
    def validate_codex_audit_model(cls, value: object) -> str | None:
        return normalize_codex_model(value)

    @field_validator("codex_audit_model_options", mode="before")
    @classmethod
    def validate_codex_audit_model_options(cls, value: object) -> object:
        parse_codex_model_options(value)
        return value

    @field_validator("codex_audit_reasoning_effort", mode="before")
    @classmethod
    def validate_codex_audit_reasoning_effort(cls, value: object) -> str:
        return normalize_codex_reasoning_effort(value) or "medium"

    @field_validator("codex_audit_reasoning_effort_options", mode="before")
    @classmethod
    def validate_codex_audit_reasoning_effort_options(cls, value: object) -> object:
        parse_codex_reasoning_effort_options(value)
        return value

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
