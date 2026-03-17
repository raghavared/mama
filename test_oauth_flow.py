"""Test script for OAuth 2.0 flows across all supported platforms.

This script tests:
1. Authorization URL generation
2. Token storage and encryption
3. Token retrieval and decryption
4. Token validation
5. Error scenarios

Run this script after setting up OAuth credentials in your .env file.

Usage:
    python test_oauth_flow.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select

# Add src to path
sys.path.insert(0, ".")

from src.config.settings import get_settings
from src.database import AsyncSessionLocal, OAuthTokenORM
from src.oauth import TokenManager, get_platform_config
from src.oauth.exceptions import (
    OAuthError,
    PlatformConfigError,
    TokenEncryptionError,
    TokenNotFoundError,
)
from src.oauth.platform_configs import PlatformName

logger = structlog.get_logger(__name__)

# Test platforms
PLATFORMS: list[PlatformName] = ["instagram", "facebook", "linkedin", "twitter", "youtube"]


class OAuthTester:
    """Test runner for OAuth flows."""

    def __init__(self) -> None:
        """Initialize the tester."""
        self.token_manager = TokenManager()
        self.results: dict[str, dict[str, Any]] = {}
        self.passed = 0
        self.failed = 0

    def log_test(self, test_name: str, passed: bool, message: str = "") -> None:
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if message:
            print(f"    └─ {message}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1

    async def test_platform_config(self, platform: PlatformName) -> bool:
        """Test platform configuration retrieval.

        Args:
            platform: Platform name to test

        Returns:
            True if test passed
        """
        test_name = f"Config: {platform.upper()}"
        try:
            config = get_platform_config(platform)

            # Check all required fields are present
            assert config.name == platform
            assert config.auth_url.startswith("https://")
            assert config.token_url.startswith("https://")
            assert len(config.scopes) > 0
            assert config.client_id
            assert config.client_secret
            assert config.redirect_uri

            self.log_test(test_name, True, f"Client ID: {config.client_id[:10]}...")
            return True

        except PlatformConfigError as e:
            self.log_test(test_name, False, f"Missing credentials: {e}")
            return False
        except AssertionError as e:
            self.log_test(test_name, False, f"Invalid configuration: {e}")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"Unexpected error: {e}")
            return False

    def test_authorization_url(self, platform: PlatformName) -> bool:
        """Test authorization URL generation.

        Args:
            platform: Platform name to test

        Returns:
            True if test passed
        """
        test_name = f"Auth URL: {platform.upper()}"
        try:
            config = get_platform_config(platform)
            state = "test_state_123"
            auth_url = config.get_authorization_url(state)

            # Validate URL structure
            assert auth_url.startswith(config.auth_url)
            assert f"client_id={config.client_id}" in auth_url
            assert f"redirect_uri={config.redirect_uri}" in auth_url
            assert "response_type=code" in auth_url
            assert f"state={state}" in auth_url

            # Check scopes are included
            for scope in config.scopes:
                # URL may encode spaces as + or %20
                assert scope.replace(" ", "+") in auth_url or scope.replace(" ", "%20") in auth_url

            self.log_test(test_name, True, f"URL: {auth_url[:60]}...")
            return True

        except PlatformConfigError as e:
            self.log_test(test_name, False, f"Config error: {e}")
            return False
        except AssertionError as e:
            self.log_test(test_name, False, f"Invalid URL format: {e}")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"Unexpected error: {e}")
            return False

    async def test_token_encryption(self) -> bool:
        """Test token encryption and decryption.

        Returns:
            True if test passed
        """
        test_name = "Token Encryption"
        try:
            # Test data
            token_data = {
                "access_token": "test_access_token_12345",
                "refresh_token": "test_refresh_token_67890",
                "token_type": "Bearer",
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "extra_data": {"user_id": "123", "username": "testuser"},
            }

            # Encrypt
            encrypted = self.token_manager._encrypt_token(token_data)
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0
            assert encrypted != str(token_data)  # Must be encrypted, not plaintext

            # Decrypt
            decrypted = self.token_manager._decrypt_token(encrypted)
            assert decrypted == token_data

            self.log_test(test_name, True, "Encryption/decryption successful")
            return True

        except TokenEncryptionError as e:
            self.log_test(test_name, False, f"Encryption error: {e}")
            return False
        except AssertionError as e:
            self.log_test(test_name, False, f"Validation failed: {e}")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"Unexpected error: {e}")
            return False

    async def test_token_storage(self, platform: PlatformName) -> bool:
        """Test token storage and retrieval.

        Args:
            platform: Platform name to test

        Returns:
            True if test passed
        """
        test_name = f"Token Storage: {platform.upper()}"
        try:
            async with AsyncSessionLocal() as db:
                # Store test token
                test_access_token = f"test_access_{platform}_12345"
                test_refresh_token = f"test_refresh_{platform}_67890"
                expires_in = 3600  # 1 hour

                await self.token_manager.store_token(
                    db=db,
                    platform=platform,
                    access_token=test_access_token,
                    refresh_token=test_refresh_token,
                    expires_in=expires_in,
                    extra_data={"test": True, "platform": platform},
                )

                # Retrieve token
                token_data = await self.token_manager.get_token(db, platform)

                # Validate
                assert token_data["access_token"] == test_access_token
                assert token_data["refresh_token"] == test_refresh_token
                assert token_data["token_type"] == "Bearer"
                assert token_data["extra_data"]["test"] is True

                # Check expiration
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                assert expires_at > datetime.utcnow()

                self.log_test(test_name, True, "Store/retrieve successful")
                return True

        except Exception as e:
            self.log_test(test_name, False, f"Storage error: {e}")
            return False

    async def test_token_validation(self, platform: PlatformName) -> bool:
        """Test token validation.

        Args:
            platform: Platform name to test

        Returns:
            True if test passed
        """
        test_name = f"Token Validation: {platform.upper()}"
        try:
            async with AsyncSessionLocal() as db:
                # Check if token is valid (from previous test)
                is_valid = await self.token_manager.is_token_valid(db, platform)
                assert is_valid is True

                self.log_test(test_name, True, "Token is valid")
                return True

        except Exception as e:
            self.log_test(test_name, False, f"Validation error: {e}")
            return False

    async def test_token_revocation(self, platform: PlatformName) -> bool:
        """Test token revocation.

        Args:
            platform: Platform name to test

        Returns:
            True if test passed
        """
        test_name = f"Token Revocation: {platform.upper()}"
        try:
            async with AsyncSessionLocal() as db:
                # Revoke token
                await self.token_manager.revoke_token(db, platform)

                # Verify it's gone
                try:
                    await self.token_manager.get_token(db, platform)
                    # Should not reach here
                    self.log_test(test_name, False, "Token still exists after revocation")
                    return False
                except TokenNotFoundError:
                    # Expected
                    pass

                self.log_test(test_name, True, "Token revoked successfully")
                return True

        except TokenNotFoundError:
            self.log_test(test_name, False, "Token not found (may not have been stored)")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"Revocation error: {e}")
            return False

    async def test_error_scenarios(self) -> None:
        """Test error handling scenarios."""
        print("\n" + "=" * 60)
        print("ERROR SCENARIO TESTS")
        print("=" * 60 + "\n")

        # Test 1: Invalid platform
        test_name = "Error: Invalid Platform"
        try:
            get_platform_config("invalid_platform")  # type: ignore
            self.log_test(test_name, False, "Should have raised PlatformConfigError")
        except PlatformConfigError:
            self.log_test(test_name, True, "Correctly raised PlatformConfigError")
        except Exception as e:
            self.log_test(test_name, False, f"Wrong exception type: {e}")

        # Test 2: Token not found
        test_name = "Error: Token Not Found"
        try:
            async with AsyncSessionLocal() as db:
                await self.token_manager.get_token(db, "instagram")
            self.log_test(test_name, False, "Should have raised TokenNotFoundError")
        except TokenNotFoundError:
            self.log_test(test_name, True, "Correctly raised TokenNotFoundError")
        except Exception as e:
            self.log_test(test_name, False, f"Wrong exception type: {e}")

        # Test 3: Invalid encrypted token
        test_name = "Error: Invalid Encrypted Token"
        try:
            self.token_manager._decrypt_token("invalid_encrypted_data")
            self.log_test(test_name, False, "Should have raised TokenEncryptionError")
        except TokenEncryptionError:
            self.log_test(test_name, True, "Correctly raised TokenEncryptionError")
        except Exception as e:
            self.log_test(test_name, False, f"Wrong exception type: {e}")

    async def run_all_tests(self) -> None:
        """Run all OAuth tests."""
        print("\n" + "=" * 60)
        print("MAMA OAUTH FLOW TESTING")
        print("=" * 60 + "\n")

        settings = get_settings()
        print(f"Environment: {settings.environment}")
        print(f"API Host: {settings.api_host}:{settings.api_port}")
        print(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
        print("\n")

        # Test 1: Platform Configuration
        print("=" * 60)
        print("PLATFORM CONFIGURATION TESTS")
        print("=" * 60 + "\n")

        configured_platforms: list[PlatformName] = []
        for platform in PLATFORMS:
            if await self.test_platform_config(platform):
                configured_platforms.append(platform)

        if not configured_platforms:
            print("\n❌ No platforms configured. Please set OAuth credentials in .env")
            print("   See docs/oauth-setup.md for instructions.")
            return

        # Test 2: Authorization URL Generation
        print("\n" + "=" * 60)
        print("AUTHORIZATION URL GENERATION TESTS")
        print("=" * 60 + "\n")

        for platform in configured_platforms:
            self.test_authorization_url(platform)

        # Test 3: Token Encryption
        print("\n" + "=" * 60)
        print("TOKEN ENCRYPTION TESTS")
        print("=" * 60 + "\n")

        await self.test_token_encryption()

        # Test 4: Token Storage (for configured platforms only)
        print("\n" + "=" * 60)
        print("TOKEN STORAGE TESTS")
        print("=" * 60 + "\n")

        for platform in configured_platforms:
            await self.test_token_storage(platform)

        # Test 5: Token Validation
        print("\n" + "=" * 60)
        print("TOKEN VALIDATION TESTS")
        print("=" * 60 + "\n")

        for platform in configured_platforms:
            await self.test_token_validation(platform)

        # Test 6: Token Revocation
        print("\n" + "=" * 60)
        print("TOKEN REVOCATION TESTS")
        print("=" * 60 + "\n")

        for platform in configured_platforms:
            await self.test_token_revocation(platform)

        # Test 7: Error Scenarios
        await self.test_error_scenarios()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60 + "\n")

        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.failed == 0:
            print("\n🎉 All tests passed! OAuth integration is working correctly.")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed. Please review the errors above.")

        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60 + "\n")

        print("1. Manual Testing:")
        print("   - Start the backend: uvicorn src.api.main:app --reload")
        print("   - Start the dashboard: cd dashboard && npm run dev")
        print("   - Go to Settings → Social Connections")
        print("   - Click 'Connect' for each platform")
        print("   - Complete OAuth flow in browser")
        print()
        print("2. Test Publishing:")
        print("   - Create a content job in the dashboard")
        print("   - Verify publishers can retrieve OAuth tokens")
        print("   - Confirm posts are published successfully")
        print()
        print("3. Monitor Logs:")
        print("   - Check backend logs for OAuth-related errors")
        print("   - Verify token refresh works before expiration")
        print()
        print("4. Production Checklist:")
        print("   - Update redirect URIs to production domain (HTTPS)")
        print("   - Submit apps for platform review")
        print("   - Test on production environment")
        print("   - Set up monitoring for token expiration")
        print()


async def main() -> None:
    """Main test runner."""
    try:
        tester = OAuthTester()
        await tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
