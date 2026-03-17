# Twitter OAuth Fix - PKCE Implementation

## Problem

Twitter OAuth was failing with the error: **"You weren't able to give access to the App"**

### Root Cause

Two critical issues were identified:

1. **Missing PKCE Support**: Twitter OAuth 2.0 **REQUIRES** PKCE (Proof Key for Code Exchange) for the authorization_code flow, but our implementation was missing it.
2. **Incorrect Redirect URI**: The system was using `http://0.0.0.0:8000` instead of `http://localhost:8000`, which Twitter doesn't accept.

## Solution

### 1. Implemented PKCE Support

Created a new PKCE utilities module (`src/oauth/pkce.py`) that:
- Generates a cryptographically secure `code_verifier` (43 characters)
- Generates a `code_challenge` using SHA256 hash of the verifier
- Uses S256 as the challenge method

### 2. Updated Platform Configuration

Modified `src/oauth/platform_configs.py`:
- Added `requires_pkce` flag to `PlatformConfig` (set to `True` for Twitter)
- Updated `get_authorization_url()` to accept PKCE parameters
- Fixed redirect URI to use `localhost` instead of `0.0.0.0`

### 3. Updated OAuth Router

Modified `src/api/routers/oauth.py`:
- Generate PKCE parameters when Twitter OAuth is initiated
- Store `code_verifier` in OAuth state for callback
- Pass `code_verifier` to token exchange endpoint

## What You Need to Do

### Update Twitter Developer Portal

You need to update your redirect URI in the Twitter Developer Portal to match **EXACTLY**:

```
http://localhost:8000/api/oauth/callback/twitter
```

**Steps:**

1. Go to: https://developer.twitter.com/en/portal/projects-and-apps
2. Select your app
3. Click on "User authentication settings" (or "Edit" if already configured)
4. Under **Callback URI / Redirect URL**, ADD this URL:
   ```
   http://localhost:8000/api/oauth/callback/twitter
   ```
5. **IMPORTANT**: Copy-paste it EXACTLY as shown above (case-sensitive, no trailing slash)
6. Click "Save"

### Test the OAuth Flow

1. **Restart your backend** (if it's running):
   ```bash
   # Kill the existing backend
   lsof -ti:8000 | xargs kill -9

   # Start it again (from MAMA project root)
   # (however you normally start it - uvicorn, python, etc.)
   ```

2. **Clear browser cookies** for localhost (to start fresh)

3. **Try the Twitter OAuth flow** from your dashboard:
   - Go to Settings → Social Connections
   - Click "Connect" on Twitter
   - You should be redirected to Twitter's authorization page
   - Click "Authorize app"
   - You should be redirected back successfully

## Technical Details

### OAuth URL Structure

The generated OAuth URL now includes PKCE parameters:

```
https://twitter.com/i/oauth2/authorize?
  client_id=<YOUR_CLIENT_ID>&
  redirect_uri=http://localhost:8000/api/oauth/callback/twitter&
  scope=tweet.read tweet.write users.read&
  response_type=code&
  state=<RANDOM_STATE>&
  code_challenge=<BASE64_CHALLENGE>&
  code_challenge_method=S256
```

### PKCE Flow

1. **Authorization Request**:
   - Generate random `code_verifier` (43 chars)
   - Compute `code_challenge = BASE64URL(SHA256(code_verifier))`
   - Send `code_challenge` and `code_challenge_method=S256` to Twitter
   - Store `code_verifier` in server state

2. **Token Exchange**:
   - Receive authorization `code` from Twitter callback
   - Retrieve stored `code_verifier` from state
   - Send `code` + `code_verifier` to Twitter token endpoint
   - Twitter verifies: `SHA256(code_verifier) == code_challenge`
   - Twitter returns access token

### Why PKCE?

PKCE prevents authorization code interception attacks by ensuring that the same client that initiated the OAuth flow is the one exchanging the code for a token. Even if an attacker intercepts the authorization code, they cannot use it without the `code_verifier`.

## Files Changed

1. **New file**: `src/oauth/pkce.py` - PKCE utility functions
2. **Modified**: `src/oauth/platform_configs.py` - Added PKCE support and fixed redirect URI
3. **Modified**: `src/api/routers/oauth.py` - Generate and use PKCE parameters
4. **Test script**: `test_twitter_oauth.py` - Verify PKCE implementation

## Verification

Run the test script to verify the OAuth URL:

```bash
python3 test_twitter_oauth.py
```

You should see:
```
✅ PKCE IS IMPLEMENTED
   code_challenge: <BASE64_STRING>
   code_challenge_method: S256

✅ Redirect URI: http://localhost:8000/api/oauth/callback/twitter
```

## Next Steps

1. Update Twitter Developer Portal redirect URI (see above)
2. Restart backend
3. Test OAuth flow
4. If you still get errors, check:
   - Browser console for the exact OAuth URL being opened
   - Backend logs for any PKCE-related errors
   - Twitter Developer Portal for any configuration issues

## References

- Twitter OAuth 2.0 Documentation: https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
- PKCE RFC 7636: https://tools.ietf.org/html/rfc7636
