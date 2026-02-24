"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Application ===
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = Field(default="change_me", min_length=8)

    # === LLM ===
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = "claude-sonnet-4-6"

    # === LLM Fallback ===
    gemini_api_key: str = Field(default="")
    gemini_model: str = "gemini-2.0-flash-001"
    openai_model: str = "gpt-4o"
    llm_provider_priority: list[str] = ["claude", "gemini", "openai"]
    llm_fallback_enabled: bool = True
    llm_provider_failure_threshold: int = 3
    llm_provider_cooldown_seconds: int = 60

    # === Image Generation ===
    openai_api_key: str = Field(default="")
    image_generation_provider: Literal["dalle", "stable_diffusion", "gemini"] = "dalle"
    gemini_image_model: str = "imagen-3.0-generate-002"

    # === Video Generation ===
    veo3_api_key: str = Field(default="")
    kling_api_key: str = Field(default="")
    kling_api_secret: str = Field(default="")

    # === Programmatic Video ===
    renderio_api_key: str = Field(default="")

    # === Remotion ===
    use_remotion: bool = True
    remotion_composition: str = "MarketingVideo"
    remotion_project_path: str = "./remotion"

    # === Audio ===
    elevenlabs_api_key: str = Field(default="")
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # === Social Platforms ===
    instagram_access_token: str = Field(default="")
    instagram_account_id: str = Field(default="")
    linkedin_access_token: str = Field(default="")
    linkedin_org_id: str = Field(default="")
    facebook_access_token: str = Field(default="")
    facebook_page_id: str = Field(default="")
    twitter_bearer_token: str = Field(default="")
    twitter_api_key: str = Field(default="")
    twitter_api_secret: str = Field(default="")
    twitter_access_token: str = Field(default="")
    twitter_access_token_secret: str = Field(default="")
    youtube_api_key: str = Field(default="")
    youtube_channel_id: str = Field(default="")

    # === Database ===
    database_url: str = "postgresql+asyncpg://mama:mama_password@localhost:5432/mama_db"
    database_url_sync: str = "postgresql+psycopg://mama:mama_password@localhost:5432/mama_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # === Cache & Queue ===
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # === Storage ===
    s3_bucket_name: str = "mama-media-assets"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    use_local_storage: bool = True  # Use local filesystem in dev
    local_storage_path: str = "./media_assets"
    # Optional CDN domain — when set, all S3 URLs are rewritten to CDN URLs
    cdn_domain: str = Field(default="")  # e.g. d12wn0ddx5knud.cloudfront.net

    # === Brand Config ===
    brand_name: str = "YourBrand"
    brand_description: str = "An innovative company"
    brand_voice: str = "professional and engaging"
    content_goals: str = "drive engagement, build brand awareness"

    # === Pipeline Defaults ===
    max_improvement_cycles: int = 3
    script_approval_timeout_seconds: int = 300
    image_generation_timeout_seconds: int = 120
    video_generation_timeout_seconds: int = 1800
    audio_generation_timeout_seconds: int = 120

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def brand_context(self) -> str:
        return f"{self.brand_name}: {self.brand_description}. Voice: {self.brand_voice}."


@lru_cache
def get_settings() -> Settings:
    return Settings()
