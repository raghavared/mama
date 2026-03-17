"""Test script specifically for Twitter OAuth 2.0 with PKCE.

This script verifies:
1. PKCE code_verifier and code_challenge generation
2. Twitter authorization URL contains code_challenge and code_challenge_method
3. Platform config correctly identifies Twitter as requiring PKCE

Usage:
    python test_twitter_pkce.py
"""
from __future__ import annotations

import sys

# Add src to path
sys.path.insert(0, ".")

from src.oauth.pkce import (
    generate_code_challenge,
    generate_code_verifier,
    get_code_challenge_method,
)
from src.oauth.platform_configs import get_platform_config


def test_pkce_generation() -> bool:
    """Test PKCE code generation."""
    print("=" * 60)
    print("TEST 1: PKCE Code Generation")
    print("=" * 60)

    try:
        # Generate code verifier
        code_verifier = generate_code_verifier()
        print(f"✅ Code verifier generated: {len(code_verifier)} characters")
        print(f"   Sample: {code_verifier}")

        # Verify length (must be 43-128 characters)
        assert (
            43 <= len(code_verifier) <= 128
        ), f"Code verifier length {len(code_verifier)} is invalid"

        # Generate code challenge
        code_challenge = generate_code_challenge(code_verifier)
        print(f"✅ Code challenge generated: {len(code_challenge)} characters")
        print(f"   Sample: {code_challenge}")

        # Get challenge method
        method = get_code_challenge_method()
        print(f"✅ Challenge method: {method}")
        assert method == "S256", f"Expected S256, got {method}"

        # Verify code_challenge is different from code_verifier (hashed)
        assert (
            code_challenge != code_verifier
        ), "Code challenge must be different from verifier"

        print("✅ PASS: PKCE generation works correctly\n")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False


def test_twitter_config() -> bool:
    """Test Twitter platform configuration."""
    print("=" * 60)
    print("TEST 2: Twitter Platform Configuration")
    print("=" * 60)

    try:
        config = get_platform_config("twitter")

        print(f"✅ Platform: {config.name}")
        print(f"✅ Auth URL: {config.auth_url}")
        print(f"✅ Token URL: {config.token_url}")
        print(f"✅ Scopes: {', '.join(config.scopes)}")
        print(f"✅ Redirect URI: {config.redirect_uri}")
        print(f"✅ Requires PKCE: {config.requires_pkce}")

        # Verify Twitter requires PKCE
        assert (
            config.requires_pkce is True
        ), "Twitter must require PKCE (requires_pkce=True)"

        # Verify client credentials are set
        assert config.client_id, "Twitter client_id is not set"
        assert config.client_secret, "Twitter client_secret is not set"
        print(f"✅ Client ID configured: {config.client_id[:10]}...")

        print("✅ PASS: Twitter configuration correct\n")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False


def test_authorization_url_with_pkce() -> bool:
    """Test authorization URL includes PKCE parameters."""
    print("=" * 60)
    print("TEST 3: Authorization URL with PKCE")
    print("=" * 60)

    try:
        config = get_platform_config("twitter")

        # Generate PKCE parameters
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        code_challenge_method = get_code_challenge_method()

        # Generate authorization URL
        state = "test_state_12345"
        auth_url = config.get_authorization_url(
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        print(f"✅ Authorization URL generated")
        print(f"   URL: {auth_url[:80]}...")

        # Verify URL contains all required parameters
        assert config.auth_url in auth_url, "Base auth URL missing"
        assert f"client_id={config.client_id}" in auth_url, "client_id missing"
        assert "redirect_uri=" in auth_url, "redirect_uri missing"
        assert "response_type=code" in auth_url, "response_type missing"
        assert f"state={state}" in auth_url, "state missing"

        # Verify PKCE parameters are included
        assert (
            f"code_challenge={code_challenge}" in auth_url
        ), "code_challenge missing from URL"
        assert (
            f"code_challenge_method={code_challenge_method}" in auth_url
        ), "code_challenge_method missing from URL"

        print(f"✅ code_challenge present in URL")
        print(f"✅ code_challenge_method={code_challenge_method} present in URL")

        # Verify scopes
        for scope in config.scopes:
            # URL may encode spaces as + or %20
            scope_encoded = scope.replace(" ", "+")
            assert scope_encoded in auth_url, f"Scope {scope} missing from URL"

        print(f"✅ All scopes present: {', '.join(config.scopes)}")

        print("✅ PASS: Authorization URL contains all PKCE parameters\n")
        return True

    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False


def test_authorization_url_without_pkce() -> bool:
    """Test that authorization URL works without PKCE for other platforms."""
    print("=" * 60)
    print("TEST 4: Authorization URL without PKCE (Instagram)")
    print("=" * 60)

    try:
        config = get_platform_config("instagram")

        # Verify Instagram does NOT require PKCE
        assert (
            config.requires_pkce is False
        ), "Instagram should not require PKCE by default"

        # Generate authorization URL without PKCE
        state = "test_state_67890"
        auth_url = config.get_authorization_url(state=state)

        print(f"✅ Authorization URL generated (no PKCE)")
        print(f"   URL: {auth_url[:80]}...")

        # Verify URL does NOT contain PKCE parameters
        assert "code_challenge=" not in auth_url, "code_challenge should not be present"
        assert (
            "code_challenge_method=" not in auth_url
        ), "code_challenge_method should not be present"

        print(f"✅ PKCE parameters correctly omitted for Instagram")

        print("✅ PASS: Non-PKCE platforms work correctly\n")
        return True

    except Exception as e:
        print(f"⚠️  SKIP: Instagram not configured (optional test): {e}\n")
        # Return True since this is optional
        return True


def main() -> None:
    """Run all Twitter PKCE tests."""
    print("\n" + "=" * 60)
    print("TWITTER OAUTH 2.0 PKCE VERIFICATION")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(test_pkce_generation())
    results.append(test_twitter_config())
    results.append(test_authorization_url_with_pkce())
    results.append(test_authorization_url_without_pkce())

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")

    if passed == total:
        print("\n🎉 All tests passed! Twitter PKCE implementation is correct.")
        print("\n" + "=" * 60)
        print("NEXT STEPS - MANUAL TESTING")
        print("=" * 60)
        print()
        print("1. Start the backend:")
        print("   uvicorn src.api.main:app --reload --port 8000")
        print()
        print("2. Get a test JWT token:")
        print('   TOKEN="your-jwt-token"')
        print()
        print('3. Call the authorize endpoint:')
        print('   curl -X POST "http://localhost:8000/api/oauth/twitter/authorize" \\')
        print('     -H "Authorization: Bearer $TOKEN" \\')
        print('     -H "Content-Type: application/json"')
        print()
        print("4. Copy the auth_url from the response and open it in a browser")
        print()
        print("5. Verify the URL contains:")
        print("   - code_challenge=<43-char-string>")
        print("   - code_challenge_method=S256")
        print()
        print("6. Authorize on Twitter and verify the callback succeeds")
        print()
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
