"""Platform-specific OAuth token refresh implementations."""
from __future__ import annotations

from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.oauth.exceptions import TokenRefreshError
from src.oauth.platform_configs import PlatformName, get_platform_config
from src.oauth.token_manager import TokenManager

logger = structlog.get_logger(__name__)


class TokenRefresher:
    """Handles platform-specific OAuth token refresh flows."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.token_manager = TokenManager()

    async def refresh_instagram_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh Instagram long-lived access token.

        Instagram tokens can be refreshed to extend their validity.
        Tokens are valid for 60 days and can be refreshed before expiry.
        """
        config = get_platform_config("instagram")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://graph.instagram.com/refresh_access_token",
                    params={
                        "grant_type": "ig_refresh_token",
                        "access_token": refresh_token,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Update token in database
                await self.token_manager.store_token(
                    db=db,
                    platform="instagram",
                    access_token=data["access_token"],
                    expires_in=data.get("expires_in"),
                )

                logger.info("instagram_token_refreshed")
                return data

        except Exception as e:
            logger.error("instagram_token_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh Instagram token: {e}") from e

    async def refresh_facebook_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh Facebook long-lived access token.

        Facebook tokens can be exchanged for long-lived tokens (60 days).
        """
        config = get_platform_config("facebook")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{config.token_url}",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                        "fb_exchange_token": refresh_token,
                    },
                )
                response.raise_for_status()
                data = response.json()

                await self.token_manager.store_token(
                    db=db,
                    platform="facebook",
                    access_token=data["access_token"],
                    expires_in=data.get("expires_in"),
                )

                logger.info("facebook_token_refreshed")
                return data

        except Exception as e:
            logger.error("facebook_token_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh Facebook token: {e}") from e

    async def refresh_linkedin_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh LinkedIn OAuth 2.0 access token.

        LinkedIn refresh tokens are valid for 1 year.
        """
        config = get_platform_config("linkedin")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()

                await self.token_manager.store_token(
                    db=db,
                    platform="linkedin",
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_in=data.get("expires_in"),
                )

                logger.info("linkedin_token_refreshed")
                return data

        except Exception as e:
            logger.error("linkedin_token_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh LinkedIn token: {e}") from e

    async def refresh_twitter_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh Twitter OAuth 2.0 access token.

        Twitter uses OAuth 2.0 with PKCE for user authentication.
        """
        config = get_platform_config("twitter")

        try:
            # Twitter OAuth 2.0 requires Basic Auth with client credentials
            import base64

            credentials = f"{config.client_id}:{config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={
                        "Authorization": f"Basic {encoded_credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
                data = response.json()

                await self.token_manager.store_token(
                    db=db,
                    platform="twitter",
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", refresh_token),
                    expires_in=data.get("expires_in"),
                )

                logger.info("twitter_token_refreshed")
                return data

        except Exception as e:
            logger.error("twitter_token_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh Twitter token: {e}") from e

    async def refresh_youtube_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Refresh YouTube (Google) OAuth 2.0 access token.

        YouTube uses Google's OAuth 2.0 implementation.
        """
        config = get_platform_config("youtube")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()

                await self.token_manager.store_token(
                    db=db,
                    platform="youtube",
                    access_token=data["access_token"],
                    refresh_token=refresh_token,  # Google doesn't return new refresh token
                    expires_in=data.get("expires_in"),
                )

                logger.info("youtube_token_refreshed")
                return data

        except Exception as e:
            logger.error("youtube_token_refresh_failed", error=str(e))
            raise TokenRefreshError(f"Failed to refresh YouTube token: {e}") from e

    async def refresh_token_for_platform(
        self,
        db: AsyncSession,
        platform: PlatformName,
    ) -> dict[str, Any]:
        """Refresh token for a specific platform.

        Args:
            db: Database session
            platform: Platform name

        Returns:
            New token data

        Raises:
            TokenRefreshError: If refresh fails
        """
        # Get current token to extract refresh token
        token_data = await self.token_manager.get_token(db, platform)
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            raise TokenRefreshError(f"No refresh token available for {platform}")

        # Route to platform-specific refresh method
        if platform == "instagram":
            return await self.refresh_instagram_token(db, refresh_token)
        elif platform == "facebook":
            return await self.refresh_facebook_token(db, refresh_token)
        elif platform == "linkedin":
            return await self.refresh_linkedin_token(db, refresh_token)
        elif platform == "twitter":
            return await self.refresh_twitter_token(db, refresh_token)
        elif platform == "youtube":
            return await self.refresh_youtube_token(db, refresh_token)
        else:
            raise TokenRefreshError(f"Token refresh not implemented for {platform}")
