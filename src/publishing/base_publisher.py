"""Base publisher abstract class."""
from __future__ import annotations

from abc import ABC, abstractmethod

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import ContentJob, Platform, PublishedPost
from src.oauth.token_manager import TokenManager
from src.oauth.exceptions import TokenNotFoundError, TokenExpiredError, TokenRefreshError
from src.oauth.platform_configs import PlatformName
from src.oauth.token_refresh import TokenRefresher


class BasePublisher(ABC):
    """Abstract base for all social platform publishers."""

    platform: Platform
    platform_name: PlatformName  # Maps to OAuth platform name

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.token_manager = TokenManager()
        self.token_refresher = TokenRefresher()

    @abstractmethod
    async def publish(
        self,
        job: ContentJob,
        asset_path: str,
        caption: str,
    ) -> PublishedPost:
        """Publish content to the platform and return a PublishedPost record."""
        ...

    def format_caption(self, caption: str, platform: Platform) -> str:
        """Platform-specific caption formatting."""
        if platform == Platform.X_TWITTER:
            # Twitter: 280 char limit
            if len(caption) > 270:
                return caption[:267] + "..."
        elif platform == Platform.INSTAGRAM:
            # Instagram: 2200 char limit
            if len(caption) > 2200:
                return caption[:2197] + "..."
        elif platform == Platform.LINKEDIN:
            # LinkedIn: 3000 char limit
            if len(caption) > 3000:
                return caption[:2997] + "..."
        return caption

    def get_hashtags(self, job: ContentJob) -> list[str]:
        """Extract hashtags from job metadata."""
        extended = job.metadata.get("cst_script_extended") or job.metadata.get("vst_script_extended") or {}
        return extended.get("hashtags", [])

    async def get_access_token(self, fallback_env_var: str | None = None, auto_refresh: bool = True) -> str:
        """Get access token from database, with optional env var fallback.

        Args:
            fallback_env_var: Optional environment variable name to fall back to if DB token not found
            auto_refresh: If True, attempt to refresh expired tokens automatically

        Returns:
            Access token string

        Raises:
            TokenNotFoundError: If no token found in DB and no fallback provided
            TokenExpiredError: If token expired and refresh failed or disabled
        """
        try:
            token_data = await self.token_manager.get_token(self.db, self.platform_name)

            # Check if token is valid
            is_valid = await self.token_manager.is_token_valid(self.db, self.platform_name)
            if not is_valid:
                self.logger.warning("token_expired", platform=self.platform_name)

                # Attempt to refresh if enabled
                if auto_refresh:
                    try:
                        self.logger.info("attempting_token_refresh", platform=self.platform_name)
                        refreshed_data = await self.token_refresher.refresh_token_for_platform(
                            self.db, self.platform_name
                        )
                        return refreshed_data["access_token"]
                    except TokenRefreshError as refresh_error:
                        self.logger.error(
                            "token_refresh_failed",
                            platform=self.platform_name,
                            error=str(refresh_error),
                        )
                        raise TokenExpiredError(
                            f"Token expired for {self.platform_name} and refresh failed"
                        ) from refresh_error

                raise TokenExpiredError(f"Token expired for {self.platform_name}")

            return token_data["access_token"]

        except TokenNotFoundError:
            # Fallback to environment variable for backward compatibility
            if fallback_env_var:
                token = getattr(self.settings, fallback_env_var, None)
                if token:
                    self.logger.info("using_fallback_token", platform=self.platform_name, source="env")
                    return token
            raise
