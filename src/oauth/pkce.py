"""PKCE (Proof Key for Code Exchange) utilities for OAuth 2.0.

Twitter and other platforms require PKCE for enhanced security in OAuth flows.
PKCE prevents authorization code interception attacks.
"""
from __future__ import annotations

import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    """Generate a cryptographically random code verifier.

    The code verifier is a high-entropy cryptographic random string using the
    unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
    with a minimum length of 43 characters and a maximum length of 128 characters.

    Returns:
        URL-safe random string (43-128 characters)
    """
    # Generate 32 random bytes -> base64url encode -> 43 characters
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def generate_code_challenge(code_verifier: str) -> str:
    """Generate a code challenge from the code verifier.

    The code challenge is created by:
    1. Hashing the code_verifier with SHA256
    2. Base64url encoding the hash

    Args:
        code_verifier: The code verifier string

    Returns:
        Base64url-encoded SHA256 hash of the code verifier
    """
    # SHA256 hash the code verifier
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    # Base64url encode (no padding)
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


def get_code_challenge_method() -> str:
    """Get the code challenge method used.

    Returns:
        Always returns 'S256' (SHA256)
    """
    return 'S256'
