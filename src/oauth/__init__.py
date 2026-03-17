"""OAuth module for platform authentication and token management."""
from __future__ import annotations

from src.oauth.exceptions import (
    OAuthError,
    TokenEncryptionError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenRefreshError,
)
from src.oauth.platform_configs import PlatformConfig, get_platform_config
from src.oauth.token_manager import TokenManager

__all__ = [
    "OAuthError",
    "TokenEncryptionError",
    "TokenExpiredError",
    "TokenNotFoundError",
    "TokenRefreshError",
    "PlatformConfig",
    "get_platform_config",
    "TokenManager",
]
