"""OAuth-related exceptions."""
from __future__ import annotations


class OAuthError(Exception):
    """Base exception for all OAuth-related errors."""

    pass


class TokenNotFoundError(OAuthError):
    """Raised when a token is not found in storage."""

    pass


class TokenExpiredError(OAuthError):
    """Raised when a token has expired and cannot be refreshed."""

    pass


class TokenRefreshError(OAuthError):
    """Raised when token refresh fails."""

    pass


class TokenEncryptionError(OAuthError):
    """Raised when token encryption or decryption fails."""

    pass


class PlatformConfigError(OAuthError):
    """Raised when platform configuration is invalid or missing."""

    pass
