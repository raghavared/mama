#!/usr/bin/env python3
"""Test script to debug Twitter OAuth URL generation."""
import sys
from urllib.parse import parse_qs, urlparse

# Add src to path
sys.path.insert(0, '/Users/raghavareddy/Downloads/projects/AI/MAMA')

from src.oauth.platform_configs import get_platform_config
from src.oauth.pkce import (
    generate_code_challenge,
    generate_code_verifier,
    get_code_challenge_method,
)

def main():
    """Generate and analyze Twitter OAuth URL."""
    print("=" * 80)
    print("Twitter OAuth URL Analysis")
    print("=" * 80)

    # Get Twitter config
    try:
        config = get_platform_config("twitter")
    except Exception as e:
        print(f"ERROR: Failed to get Twitter config: {e}")
        return

    print("\n1. PLATFORM CONFIGURATION:")
    print(f"   Client ID: {config.client_id[:20]}..." if config.client_id else "   Client ID: NOT SET")
    print(f"   Auth URL: {config.auth_url}")
    print(f"   Token URL: {config.token_url}")
    print(f"   Scopes: {config.scopes}")
    print(f"   Redirect URI: {config.redirect_uri}")

    # Generate PKCE parameters if required
    code_verifier = None
    code_challenge = None
    code_challenge_method = None

    if config.requires_pkce:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        code_challenge_method = get_code_challenge_method()
        print(f"\n   PKCE Enabled: Yes")
        print(f"   Code Verifier: {code_verifier[:20]}... (length: {len(code_verifier)})")
        print(f"   Code Challenge: {code_challenge[:20]}... (length: {len(code_challenge)})")
        print(f"   Challenge Method: {code_challenge_method}")
    else:
        print(f"\n   PKCE Enabled: No")

    # Generate authorization URL with test state
    test_state = "test_state_12345"
    auth_url = config.get_authorization_url(
        state=test_state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    print("\n2. GENERATED AUTHORIZATION URL:")
    print(f"   {auth_url}")

    # Parse the URL
    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    print("\n3. URL PARAMETERS (decoded):")
    for key, value in params.items():
        print(f"   {key}: {value[0]}")

    print("\n4. PKCE CHECK:")
    has_code_challenge = 'code_challenge' in params
    has_code_challenge_method = 'code_challenge_method' in params

    if has_code_challenge and has_code_challenge_method:
        print("   ✅ PKCE IS IMPLEMENTED")
        print(f"      code_challenge: {params['code_challenge'][0][:20]}...")
        print(f"      code_challenge_method: {params['code_challenge_method'][0]}")
    else:
        print("   ❌ PKCE IS MISSING!")
        print("      Twitter OAuth 2.0 REQUIRES PKCE for authorization_code flow")
        print("      Missing parameters:")
        if not has_code_challenge:
            print("        - code_challenge")
        if not has_code_challenge_method:
            print("        - code_challenge_method")

    print("\n5. REDIRECT URI TO ADD IN TWITTER DEVELOPER PORTAL:")
    print("   " + "=" * 76)
    print(f"   {config.redirect_uri}")
    print("   " + "=" * 76)
    print("\n   Steps:")
    print("   1. Go to: https://developer.twitter.com/en/portal/projects-and-apps")
    print("   2. Select your app")
    print("   3. Go to: User authentication settings")
    print("   4. Edit 'Redirect URLs'")
    print("   5. Add EXACTLY this URL (copy-paste it):")
    print(f"      {config.redirect_uri}")
    print("   6. Save")

    print("\n6. TWITTER OAUTH 2.0 REQUIREMENTS:")
    print("   ✅ Must use OAuth 2.0 (not OAuth 1.0a)")
    print("   ✅ Must use authorization_code grant type")
    print("   ❌ MUST include PKCE (code_challenge + code_challenge_method)")
    print("   ✅ Redirect URI must be EXACT match (no wildcards)")
    print("   ✅ Scopes must be space-separated")
    print("   ✅ Must include state parameter for CSRF protection")

    print("\n7. ISSUE DIAGNOSIS:")
    if not has_code_challenge or not has_code_challenge_method:
        print("   🔴 CRITICAL: Twitter OAuth is MISSING PKCE support!")
        print("   ")
        print("   Twitter REQUIRES PKCE for OAuth 2.0 authorization_code flow.")
        print("   Without PKCE, Twitter will reject the authorization request.")
        print("   ")
        print("   This is likely why the user is seeing:")
        print("   'You weren't able to give access to the App'")
    else:
        print("   ✅ PKCE is implemented correctly")
        print("   Check if redirect URI in Twitter Portal matches exactly:")
        print(f"      {config.redirect_uri}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
