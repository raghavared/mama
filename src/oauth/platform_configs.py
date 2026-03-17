"""OAuth platform configurations for social media platforms."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.config.settings import get_settings
from src.oauth.exceptions import PlatformConfigError

PlatformName = Literal["instagram", "facebook", "linkedin", "twitter", "youtube"]


@dataclass(frozen=True)
class PlatformConfig:
    """OAuth configuration for a social media platform."""

    name: str
    auth_url: str
    token_url: str
    scopes: list[str]
    client_id: str
    client_secret: str
    redirect_uri: str
    requires_pkce: bool = False  # Twitter requires PKCE

    def get_authorization_url(
        self,
        state: str,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate the OAuth authorization URL with required parameters.

        Args:
            state: CSRF state token
            code_challenge: PKCE code challenge (required for Twitter)
            code_challenge_method: PKCE challenge method (required for Twitter)

        Returns:
            Complete authorization URL
        """
        scope_str = " ".join(self.scopes)
        url = (
            f"{self.auth_url}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={scope_str}&"
            f"response_type=code&"
            f"state={state}"
        )

        # Add PKCE parameters if provided (required for Twitter)
        if code_challenge and code_challenge_method:
            url += f"&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}"

        return url


def get_platform_config(platform: PlatformName) -> PlatformConfig:
    """Get OAuth configuration for a specific platform.

    Args:
        platform: The platform name (instagram, facebook, linkedin, twitter, youtube)

    Returns:
        PlatformConfig for the specified platform

    Raises:
        PlatformConfigError: If platform is unsupported or credentials are missing
    """
    settings = get_settings()

    # Base redirect URI - will be handled by backend OAuth callback endpoint
    # Use localhost instead of 0.0.0.0 for OAuth redirects (Twitter requires exact match)
    api_host = "localhost" if settings.api_host == "0.0.0.0" else settings.api_host
    base_redirect_uri = f"http://{api_host}:{settings.api_port}/api/v1/oauth/callback"

    configs = {
        "instagram": PlatformConfig(
            name="instagram",
            auth_url="https://api.instagram.com/oauth/authorize",
            token_url="https://api.instagram.com/oauth/access_token",
            scopes=["instagram_basic", "instagram_content_publish"],
            client_id=settings.instagram_client_id,
            client_secret=settings.instagram_client_secret,
            redirect_uri=f"{base_redirect_uri}/instagram",
        ),
        "facebook": PlatformConfig(
            name="facebook",
            auth_url="https://www.facebook.com/v18.0/dialog/oauth",
            token_url="https://graph.facebook.com/v18.0/oauth/access_token",
            scopes=["pages_manage_posts", "pages_read_engagement"],
            client_id=settings.facebook_client_id,
            client_secret=settings.facebook_client_secret,
            redirect_uri=f"{base_redirect_uri}/facebook",
        ),
        "linkedin": PlatformConfig(
            name="linkedin",
            auth_url="https://www.linkedin.com/oauth/v2/authorization",
            token_url="https://www.linkedin.com/oauth/v2/accessToken",
            scopes=["w_member_social", "r_basicprofile"],
            client_id=settings.linkedin_client_id,
            client_secret=settings.linkedin_client_secret,
            redirect_uri=f"{base_redirect_uri}/linkedin",
        ),
        "twitter": PlatformConfig(
            name="twitter",
            auth_url="https://twitter.com/i/oauth2/authorize",
            token_url="https://api.twitter.com/2/oauth2/token",
            scopes=["tweet.read", "tweet.write", "users.read"],
            client_id=settings.twitter_client_id,
            client_secret=settings.twitter_client_secret,
            redirect_uri=f"{base_redirect_uri}/twitter",
            requires_pkce=True,  # Twitter OAuth 2.0 requires PKCE
        ),
        "youtube": PlatformConfig(
            name="youtube",
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"],
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
            redirect_uri=f"{base_redirect_uri}/youtube",
        ),
    }

    if platform not in configs:
        raise PlatformConfigError(f"Unsupported platform: {platform}")

    config = configs[platform]

    # Validate that credentials are configured
    if not config.client_id or not config.client_secret:
        raise PlatformConfigError(
            f"Missing OAuth credentials for {platform}. "
            f"Please set {platform.upper()}_CLIENT_ID and {platform.upper()}_CLIENT_SECRET in your .env file."
        )

    return config
