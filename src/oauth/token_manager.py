"""Token manager for secure storage and retrieval of OAuth tokens."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.database.models import OAuthTokenORM
from src.oauth.exceptions import (
    TokenEncryptionError,
    TokenExpiredError,
    TokenNotFoundError,
)
from src.oauth.platform_configs import PlatformName

logger = structlog.get_logger(__name__)


class TokenManager:
    """Manages encrypted OAuth tokens for social media platforms."""

    def __init__(self) -> None:
        """Initialize the TokenManager with encryption key from settings."""
        settings = get_settings()
        # Use the SECRET_KEY to derive a Fernet key
        # In production, this should be a dedicated OAUTH_ENCRYPTION_KEY
        # For now, we'll hash the SECRET_KEY to get a proper Fernet key
        import base64
        import hashlib

        key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def _encrypt_token(self, token_data: dict[str, Any]) -> str:
        """Encrypt token data.

        Args:
            token_data: Dictionary containing token information

        Returns:
            Encrypted token as a string

        Raises:
            TokenEncryptionError: If encryption fails
        """
        try:
            json_str = json.dumps(token_data)
            encrypted = self.fernet.encrypt(json_str.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error("token_encryption_failed", error=str(e))
            raise TokenEncryptionError(f"Failed to encrypt token: {e}") from e

    def _decrypt_token(self, encrypted_token: str) -> dict[str, Any]:
        """Decrypt token data.

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Decrypted token data as dictionary

        Raises:
            TokenEncryptionError: If decryption fails
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_token.encode())
            return json.loads(decrypted.decode())
        except InvalidToken as e:
            logger.error("token_decryption_failed", error="invalid_token")
            raise TokenEncryptionError("Invalid token or encryption key") from e
        except Exception as e:
            logger.error("token_decryption_failed", error=str(e))
            raise TokenEncryptionError(f"Failed to decrypt token: {e}") from e

    async def store_token(
        self,
        db: AsyncSession,
        platform: PlatformName,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
        token_type: str = "Bearer",
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        """Store or update an encrypted OAuth token.

        Args:
            db: Database session
            platform: Platform name
            access_token: OAuth access token
            refresh_token: Optional refresh token
            expires_in: Token expiration time in seconds
            token_type: Token type (usually "Bearer")
            extra_data: Additional platform-specific data
        """
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "extra_data": extra_data or {},
        }

        encrypted_token = self._encrypt_token(token_data)

        # Check if token already exists for this platform
        stmt = select(OAuthTokenORM).where(OAuthTokenORM.platform == platform)
        result = await db.execute(stmt)
        existing_token = result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.encrypted_token = encrypted_token
            existing_token.expires_at = expires_at
            existing_token.updated_at = datetime.now(timezone.utc)
            logger.info("oauth_token_updated", platform=platform)
        else:
            # Create new token
            new_token = OAuthTokenORM(
                platform=platform,
                encrypted_token=encrypted_token,
                expires_at=expires_at,
            )
            db.add(new_token)
            logger.info("oauth_token_stored", platform=platform)

        await db.commit()

    async def get_token(
        self,
        db: AsyncSession,
        platform: PlatformName,
    ) -> dict[str, Any]:
        """Retrieve and decrypt an OAuth token.

        Args:
            db: Database session
            platform: Platform name

        Returns:
            Decrypted token data

        Raises:
            TokenNotFoundError: If token doesn't exist
            TokenEncryptionError: If decryption fails
        """
        stmt = select(OAuthTokenORM).where(OAuthTokenORM.platform == platform)
        result = await db.execute(stmt)
        token_orm = result.scalar_one_or_none()

        if not token_orm:
            raise TokenNotFoundError(f"No token found for platform: {platform}")

        token_data = self._decrypt_token(token_orm.encrypted_token)
        logger.info("oauth_token_retrieved", platform=platform)
        return token_data

    async def is_token_valid(
        self,
        db: AsyncSession,
        platform: PlatformName,
    ) -> bool:
        """Check if a token exists and is not expired.

        Args:
            db: Database session
            platform: Platform name

        Returns:
            True if token is valid and not expired
        """
        try:
            stmt = select(OAuthTokenORM).where(OAuthTokenORM.platform == platform)
            result = await db.execute(stmt)
            token_orm = result.scalar_one_or_none()

            if not token_orm:
                return False

            # If no expiration, assume it's valid
            if not token_orm.expires_at:
                return True

            # Check if token is expired (with 5-minute buffer)
            # Make sure to use timezone-aware datetime for comparison
            buffer = timedelta(minutes=5)
            now = datetime.now(timezone.utc)
            # Ensure expires_at is timezone-aware
            expires_at = token_orm.expires_at
            if expires_at.tzinfo is None:
                # If somehow the database value is naive, make it aware
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return now < (expires_at - buffer)

        except Exception as e:
            logger.error("token_validation_failed", platform=platform, error=str(e))
            return False

    async def refresh_token(
        self,
        db: AsyncSession,
        platform: PlatformName,
    ) -> dict[str, Any]:
        """Refresh an expired OAuth token.

        Args:
            db: Database session
            platform: Platform name

        Returns:
            New token data

        Raises:
            TokenNotFoundError: If token doesn't exist
            TokenExpiredError: If refresh token is missing or invalid
        """
        # Get current token
        token_data = await self.get_token(db, platform)
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            raise TokenExpiredError(f"No refresh token available for {platform}")

        # This would typically make an HTTP request to the platform's token endpoint
        # For now, we'll raise an error indicating this needs to be implemented
        # in the specific platform integration
        raise NotImplementedError(
            f"Token refresh for {platform} must be implemented in the platform-specific integration"
        )

    async def revoke_token(
        self,
        db: AsyncSession,
        platform: PlatformName,
    ) -> None:
        """Revoke and delete an OAuth token.

        Args:
            db: Database session
            platform: Platform name

        Raises:
            TokenNotFoundError: If token doesn't exist
        """
        stmt = select(OAuthTokenORM).where(OAuthTokenORM.platform == platform)
        result = await db.execute(stmt)
        token_orm = result.scalar_one_or_none()

        if not token_orm:
            raise TokenNotFoundError(f"No token found for platform: {platform}")

        await db.delete(token_orm)
        await db.commit()
        logger.info("oauth_token_revoked", platform=platform)
