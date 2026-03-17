# Twitter OAuth 2.0 PKCE Implementation

## Overview

Twitter OAuth 2.0 **requires** PKCE (Proof Key for Code Exchange) for all authorization flows. This document describes the PKCE implementation in the MAMA project.

## What is PKCE?

PKCE (pronounced "pixie") is a security extension to OAuth 2.0 that prevents authorization code interception attacks. It's defined in [RFC 7636](https://tools.ietf.org/html/rfc7636).

### How PKCE Works

1. **Generate code_verifier**: A cryptographically random string (43-128 characters)
2. **Generate code_challenge**: SHA256 hash of the code_verifier, base64url-encoded
3. **Authorization request**: Include `code_challenge` and `code_challenge_method=S256` in the OAuth URL
4. **Token exchange**: Send the original `code_verifier` when exchanging the authorization code for tokens
5. **Verification**: OAuth provider verifies that SHA256(code_verifier) matches the original code_challenge

This ensures that even if an attacker intercepts the authorization code, they cannot exchange it for tokens without the original code_verifier.

## Implementation Details

### 1. PKCE Utility Functions (`src/oauth/pkce.py`)

```python
def generate_code_verifier() -> str:
    """Generate a cryptographically random code verifier (43-128 characters)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def generate_code_challenge(code_verifier: str) -> str:
    """Generate code challenge from verifier using SHA256."""
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

def get_code_challenge_method() -> str:
    """Always returns 'S256' (SHA256)."""
    return 'S256'
```

### 2. Platform Configuration (`src/oauth/platform_configs.py`)

Twitter's configuration includes `requires_pkce=True`:

```python
"twitter": PlatformConfig(
    name="twitter",
    auth_url="https://twitter.com/i/oauth2/authorize",
    token_url="https://api.twitter.com/2/oauth2/token",
    scopes=["tweet.read", "tweet.write", "users.read"],
    client_id=settings.twitter_client_id,
    client_secret=settings.twitter_client_secret,
    redirect_uri=f"{base_redirect_uri}/twitter",
    requires_pkce=True,  # Twitter OAuth 2.0 requires PKCE
)
```

The `get_authorization_url()` method accepts optional PKCE parameters:

```python
def get_authorization_url(
    self,
    state: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> str:
    """Generate OAuth authorization URL with optional PKCE parameters."""
    # ... build base URL ...

    # Add PKCE parameters if provided
    if code_challenge and code_challenge_method:
        url += f"&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}"

    return url
```

### 3. Authorization Endpoint (`src/api/routers/oauth.py`)

The `/oauth/{platform}/authorize` endpoint generates PKCE parameters for Twitter:

```python
@router.post("/{platform}/authorize", response_model=AuthorizeResponse)
async def authorize(
    platform: PlatformName,
    user: dict = Depends(get_current_user),
) -> AuthorizeResponse:
    config = get_platform_config(platform)

    # Generate PKCE parameters if required (Twitter)
    code_challenge = None
    code_challenge_method = None
    if config.requires_pkce:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        code_challenge_method = get_code_challenge_method()

        # Store code_verifier in state for use in callback
        _oauth_states[state]["code_verifier"] = code_verifier

    # Generate authorization URL with PKCE
    auth_url = config.get_authorization_url(
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    return AuthorizeResponse(auth_url=auth_url, state=state)
```

**Key points:**
- PKCE is only generated for platforms where `requires_pkce=True`
- `code_verifier` is stored in the OAuth state for later retrieval in the callback
- Authorization URL includes `code_challenge` and `code_challenge_method=S256`

### 4. Callback Endpoint (`src/api/routers/oauth.py`)

The `/oauth/{platform}/callback` endpoint retrieves the `code_verifier` and uses it in token exchange:

```python
@router.get("/{platform}/callback", response_model=CallbackResponse)
async def callback(
    platform: PlatformName,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> CallbackResponse:
    # Verify state and retrieve stored data
    state_data = _verify_state(state)

    # Get code_verifier from state if PKCE was used
    code_verifier = state_data.get("code_verifier")

    # Exchange code for token (includes code_verifier)
    token_response = await _exchange_code_for_token(
        platform, code, config.redirect_uri, code_verifier
    )

    # Store token in database
    await token_manager.store_token(db, platform, ...)

    return CallbackResponse(success=True, ...)
```

### 5. Token Exchange Function

The `_exchange_code_for_token()` helper includes `code_verifier` in the token request:

```python
async def _exchange_code_for_token(
    platform: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> dict[str, Any]:
    config = get_platform_config(platform)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
    }

    # Add PKCE code_verifier if provided (required for Twitter)
    if code_verifier:
        token_data["code_verifier"] = code_verifier

    # POST to token endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(config.token_url, data=token_data)
        return response.json()
```

## Testing

### Automated Tests

Run the Twitter PKCE test suite:

```bash
python test_twitter_pkce.py
```

This verifies:
- ✅ PKCE code_verifier generation (43 characters)
- ✅ PKCE code_challenge generation (SHA256 hash)
- ✅ Twitter platform config has `requires_pkce=True`
- ✅ Authorization URLs include `code_challenge` and `code_challenge_method=S256`

### Manual Testing

1. **Start the backend:**
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Get a JWT token** (login as admin user)

3. **Call the authorize endpoint:**
   ```bash
   TOKEN="your-jwt-token"
   curl -X POST "http://localhost:8000/api/oauth/twitter/authorize" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json"
   ```

4. **Inspect the response:**
   ```json
   {
     "auth_url": "https://twitter.com/i/oauth2/authorize?client_id=...&code_challenge=abc123&code_challenge_method=S256...",
     "state": "..."
   }
   ```

5. **Verify the URL contains:**
   - `code_challenge=<43-character-string>`
   - `code_challenge_method=S256`

6. **Open the URL in a browser** and authorize

7. **Verify the callback succeeds** and tokens are stored

## OAuth State Management

The OAuth state dictionary stores PKCE parameters temporarily:

```python
_oauth_states[state] = {
    "platform": "twitter",
    "user_id": "user_uuid",
    "code_verifier": "P_-8udRSHU13vIxu6QJrSCOy3pUhrxg4wYEQUu7Fy-U",
}
```

- State is generated with `secrets.token_urlsafe(32)` for CSRF protection
- `code_verifier` is stored alongside platform and user_id
- State is consumed (deleted) after the callback to prevent reuse

**Production Note:** In production, replace the in-memory `_oauth_states` dict with Redis for persistence and scalability.

## Security Considerations

1. **PKCE is required for Twitter** - Without it, Twitter rejects authorization attempts
2. **SHA256 (S256) method** - More secure than the "plain" method
3. **State token for CSRF** - Protects against cross-site request forgery
4. **Code verifier entropy** - Uses cryptographically secure random bytes
5. **One-time use** - Both state and code_verifier are consumed after callback

## Troubleshooting

### "You weren't able to give access to the App"

**Cause:** PKCE parameters missing from authorization URL

**Solution:** Verify:
- Twitter platform config has `requires_pkce=True`
- Authorization URL includes `code_challenge` and `code_challenge_method=S256`
- Run `python test_twitter_pkce.py` to verify implementation

### "Invalid code_verifier"

**Cause:** code_verifier sent in token exchange doesn't match the original

**Solution:** Verify:
- `code_verifier` is stored in OAuth state during authorization
- Same `code_verifier` is retrieved and sent in token exchange
- State hasn't expired or been consumed by another request

### "State token invalid or expired"

**Cause:** OAuth state was consumed or never created

**Solution:** Verify:
- Authorization endpoint creates state before generating URL
- Callback endpoint retrieves state before it's consumed
- In production, use Redis with appropriate TTL (5-10 minutes)

## References

- [RFC 7636: Proof Key for Code Exchange](https://tools.ietf.org/html/rfc7636)
- [Twitter OAuth 2.0 Documentation](https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code)
- [OAuth 2.0 Security Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)

## Future Enhancements

1. **Add PKCE for all platforms** - While only Twitter requires it, PKCE is a best practice for all OAuth 2.0 flows
2. **Redis state storage** - Replace in-memory dict with Redis for production
3. **State expiration** - Add TTL to OAuth states (5-10 minutes)
4. **Metrics** - Track PKCE generation and validation success rates
