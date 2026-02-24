"""System configuration API endpoints."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.config import get_settings
from .auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/config")

# In-memory config override (in production, store in DB)
_config_override: dict = {}


class SystemConfigResponse(BaseModel):
    brand_name: str
    brand_description: str
    brand_voice: str
    content_goals: str
    max_improvement_cycles: int
    active_platforms: list[str]
    api_keys_configured: dict[str, bool]
    image_generation_provider: str  # 'dalle' | 'gemini' | 'stable_diffusion'


class SystemConfigUpdate(BaseModel):
    brand_name: str | None = None
    brand_description: str | None = None
    brand_voice: str | None = None
    content_goals: str | None = None
    max_improvement_cycles: int | None = None
    active_platforms: list[str] | None = None
    image_generation_provider: str | None = None


def _build_config() -> SystemConfigResponse:
    settings = get_settings()
    base = {
        "brand_name": settings.brand_name,
        "brand_description": settings.brand_description,
        "brand_voice": getattr(settings, "brand_voice", "professional"),
        "content_goals": getattr(settings, "content_goals", ""),
        "max_improvement_cycles": settings.max_improvement_cycles,
        "active_platforms": ["instagram", "linkedin", "facebook"],
        "api_keys_configured": {
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "gemini": bool(settings.gemini_api_key),
            "elevenlabs": bool(settings.elevenlabs_api_key),
            "veo3": bool(settings.veo3_api_key),
            "kling": bool(settings.kling_api_key),
            "instagram": bool(settings.instagram_access_token),
            "linkedin": bool(settings.linkedin_access_token),
            "facebook": bool(settings.facebook_access_token),
            "twitter": bool(settings.twitter_api_key),
            "youtube": bool(settings.youtube_api_key),
        },
        "image_generation_provider": settings.image_generation_provider,
    }
    base.update(_config_override)
    return SystemConfigResponse(**base)


@router.get("", response_model=SystemConfigResponse)
async def get_config(
    user: dict = Depends(get_current_user),
) -> SystemConfigResponse:
    """Get current system configuration."""
    return _build_config()


@router.patch("", response_model=SystemConfigResponse)
async def update_config(
    update: SystemConfigUpdate,
    user: dict = Depends(get_current_user),
) -> SystemConfigResponse:
    """Update system configuration. Admin only."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    for field, value in update.model_dump(exclude_none=True).items():
        _config_override[field] = value

    logger.info("Config updated", by=user["id"], fields=list(update.model_dump(exclude_none=True).keys()))
    return _build_config()
