"""OAuth API endpoints for social media platform authorization."""
from __future__ import annotations

import secrets
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.auth import get_current_user
from src.database import get_db
from src.oauth.exceptions import (
    OAuthError,
    PlatformConfigError,
    TokenEncryptionError,
    TokenNotFoundError,
)
from src.oauth.pkce import (
    generate_code_challenge,
    generate_code_verifier,
    get_code_challenge_method,
)
from src.oauth.platform_configs import PlatformName, get_platform_config
from src.oauth.token_manager import TokenManager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/oauth")

# In-memory state storage for CSRF protection (use Redis in production)
_oauth_states: dict[str, dict[str, Any]] = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────


class AuthorizeResponse(BaseModel):
    """Response containing the OAuth authorization URL."""

    auth_url: str
    state: str


class CallbackResponse(BaseModel):
    """Response after successful OAuth callback."""

    success: bool
    platform: str
    message: str


class PlatformStatus(BaseModel):
    """OAuth connection status for a single platform."""

    platform: str
    connected: bool
    expires_at: str | None = None


class OAuthStatusResponse(BaseModel):
    """OAuth connection status for all platforms."""

    platforms: list[PlatformStatus]


class DisconnectResponse(BaseModel):
    """Response after disconnecting a platform."""

    success: bool
    platform: str
    message: str


# ─── Helper Functions ────────────────────────────────────────────────────────


def _generate_state(platform: str, user_id: str) -> str:
    """Generate a CSRF protection state token.

    Args:
        platform: Platform name
        user_id: User ID initiating the OAuth flow

    Returns:
        Random state string
    """
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"platform": platform, "user_id": user_id}
    return state


def _verify_state(state: str) -> dict[str, Any] | None:
    """Verify and consume a state token.

    Args:
        state: State token to verify

    Returns:
        State data if valid, None otherwise
    """
    return _oauth_states.pop(state, None)


async def _exchange_code_for_token(
    platform: str, code: str, redirect_uri: str, code_verifier: str | None = None
) -> dict[str, Any]:
    """Exchange authorization code for access token.

    Args:
        platform: Platform name
        code: Authorization code from OAuth callback
        redirect_uri: Redirect URI used in the authorization request
        code_verifier: PKCE code verifier (required for Twitter)

    Returns:
        Token response from the platform

    Raises:
        HTTPException: If token exchange fails
    """
    try:
        config = get_platform_config(platform)  # type: ignore
    except PlatformConfigError as e:
        logger.error("platform_config_error", platform=platform, error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Build token request - Twitter requires Basic Auth, others use body params
    if platform == "twitter":
        # Twitter OAuth 2.0 requires Basic Auth and doesn't want client_id/secret in body
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            token_data["code_verifier"] = code_verifier

        # HTTP Basic Auth: base64(client_id:client_secret)
        import base64
        credentials = f"{config.client_id}:{config.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    else:
        # Other platforms use client_id/secret in request body
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
        if code_verifier:
            token_data["code_verifier"] = code_verifier
        headers = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                config.token_url,
                data=token_data,
                headers=headers if platform == "twitter" else None
            )
            response.raise_for_status()
            token_response = response.json()
            logger.info(
                "token_exchange_success",
                platform=platform,
                has_refresh_token=bool(token_response.get("refresh_token")),
            )
            return token_response
    except httpx.HTTPStatusError as e:
        logger.error(
            "token_exchange_failed",
            platform=platform,
            status_code=e.response.status_code,
            response=e.response.text,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to exchange code for token: {e.response.text}",
        ) from e
    except Exception as e:
        logger.error("token_exchange_error", platform=platform, error=str(e))
        raise HTTPException(
            status_code=502, detail=f"Token exchange error: {str(e)}"
        ) from e


def _check_admin_role(user: dict) -> None:
    """Check if user has admin role.

    Args:
        user: User dict from get_current_user dependency

    Raises:
        HTTPException: If user is not an admin
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403, detail="Only administrators can manage OAuth connections"
        )


def _create_oauth_callback_html(success: bool, platform: str, error: str | None = None) -> str:
    """Create HTML page for OAuth callback that notifies parent window and closes popup.

    Args:
        success: Whether OAuth flow succeeded
        platform: Platform name
        error: Error message if success is False

    Returns:
        HTML string
    """
    message_type = "oauth_success" if success else "oauth_error"
    message_data = f'{{"type": "{message_type}", "platform": "{platform}"'
    if error:
        # Escape quotes in error message
        error_escaped = error.replace('"', '\\"').replace("'", "\\'")
        message_data += f', "error": "{error_escaped}"'
    message_data += "}"

    status_text = "Successfully Connected!" if success else "Connection Failed"
    status_color = "#10b981" if success else "#ef4444"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OAuth Callback</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background: #f9fafb;
            }}
            .container {{
                text-align: center;
                padding: 2rem;
            }}
            .status {{
                font-size: 1.5rem;
                font-weight: 600;
                color: {status_color};
                margin-bottom: 1rem;
            }}
            .message {{
                color: #6b7280;
                margin-bottom: 1.5rem;
            }}
            .spinner {{
                border: 3px solid #f3f4f6;
                border-top: 3px solid {status_color};
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="status">{status_text}</div>
            <div class="message">
                {"Redirecting back to settings..." if success else error or "An error occurred"}
            </div>
            <div class="spinner"></div>
        </div>
        <script>
            // Send message to parent window (opener)
            if (window.opener) {{
                window.opener.postMessage({message_data}, window.location.origin);
            }}
            // Close popup after a short delay
            setTimeout(() => {{
                window.close();
            }}, 1500);
        </script>
    </body>
    </html>
    """


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/{platform}/authorize", response_model=AuthorizeResponse)
async def authorize(
    platform: PlatformName,
    user: dict = Depends(get_current_user),
) -> AuthorizeResponse:
    """Initiate OAuth authorization flow for a platform.

    This endpoint generates an OAuth authorization URL and returns it to the frontend.
    The user will be redirected to the platform's authorization page.

    Args:
        platform: Platform name (instagram, facebook, linkedin, twitter, youtube)
        user: Current authenticated user

    Returns:
        Authorization URL and state token

    Raises:
        HTTPException: If platform config is invalid or user is not authorized
    """
    _check_admin_role(user)

    try:
        config = get_platform_config(platform)
    except PlatformConfigError as e:
        logger.error("platform_config_error", platform=platform, error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Generate CSRF state token
    state = _generate_state(platform, user["id"])

    # Generate PKCE parameters if required (Twitter)
    code_challenge = None
    code_challenge_method = None
    if config.requires_pkce:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        code_challenge_method = get_code_challenge_method()

        # Store code_verifier in state for use in callback
        _oauth_states[state]["code_verifier"] = code_verifier

        logger.info(
            "pkce_generated",
            platform=platform,
            challenge_method=code_challenge_method,
        )

    # Generate authorization URL
    auth_url = config.get_authorization_url(
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )

    logger.info(
        "oauth_authorization_initiated",
        platform=platform,
        user_id=user["id"],
        uses_pkce=config.requires_pkce,
    )

    return AuthorizeResponse(auth_url=auth_url, state=state)


@router.get("/callback/{platform}", response_class=HTMLResponse)
async def callback(
    platform: PlatformName,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Handle OAuth callback and exchange code for tokens.

    This endpoint is called by the OAuth provider after user authorization.
    It exchanges the authorization code for access/refresh tokens and stores them.
    Returns an HTML page that notifies the parent window and closes the popup.

    Args:
        platform: Platform name
        code: Authorization code from the platform
        state: CSRF state token for verification
        db: Database session

    Returns:
        HTML page that notifies parent window and closes popup
    """
    # Verify state token (CSRF protection)
    state_data = _verify_state(state)
    if not state_data:
        logger.warning("oauth_callback_invalid_state", platform=platform, state=state)
        html = _create_oauth_callback_html(False, platform, "Invalid or expired state token")
        return HTMLResponse(content=html, status_code=400)

    if state_data["platform"] != platform:
        logger.warning(
            "oauth_callback_platform_mismatch",
            expected=state_data["platform"],
            actual=platform,
        )
        html = _create_oauth_callback_html(False, platform, "Platform mismatch")
        return HTMLResponse(content=html, status_code=400)

    # Get platform config for redirect URI
    try:
        config = get_platform_config(platform)
    except PlatformConfigError as e:
        logger.error("platform_config_error", platform=platform, error=str(e))
        html = _create_oauth_callback_html(False, platform, str(e))
        return HTMLResponse(content=html, status_code=400)

    # Get code_verifier from state if PKCE was used
    code_verifier = state_data.get("code_verifier")

    # Exchange code for token
    try:
        token_response = await _exchange_code_for_token(
            platform, code, config.redirect_uri, code_verifier
        )
    except HTTPException as e:
        logger.error("token_exchange_failed", platform=platform, error=str(e.detail))
        html = _create_oauth_callback_html(False, platform, str(e.detail))
        return HTMLResponse(content=html, status_code=e.status_code)

    # Store token in database
    token_manager = TokenManager()
    try:
        await token_manager.store_token(
            db=db,
            platform=platform,
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            expires_in=token_response.get("expires_in"),
            token_type=token_response.get("token_type", "Bearer"),
            extra_data={
                "scope": token_response.get("scope", " ".join(config.scopes)),
                "user_id": state_data["user_id"],
            },
        )
        logger.info(
            "oauth_callback_success",
            platform=platform,
            user_id=state_data["user_id"],
        )
    except TokenEncryptionError as e:
        logger.error("token_storage_failed", platform=platform, error=str(e))
        html = _create_oauth_callback_html(False, platform, "Failed to store token securely")
        return HTMLResponse(content=html, status_code=500)

    # Success! Return HTML that notifies parent and closes popup
    html = _create_oauth_callback_html(True, platform)
    return HTMLResponse(content=html, status_code=200)


@router.get("/status", response_model=list[dict[str, Any]])
async def get_oauth_status(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get OAuth connection status for all platforms.

    Returns the connection status (connected/disconnected) for each supported platform.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        Connection status for all platforms
    """
    _check_admin_role(user)

    platforms: list[PlatformName] = [
        "instagram",
        "facebook",
        "linkedin",
        "twitter",
        "youtube",
    ]
    token_manager = TokenManager()
    status_list: list[dict[str, Any]] = []

    for platform in platforms:
        try:
            is_valid = await token_manager.is_token_valid(db, platform)
            if is_valid:
                # Get token to check expiry
                try:
                    token_data = await token_manager.get_token(db, platform)
                    expires_at = token_data.get("expires_at")
                except (TokenNotFoundError, TokenEncryptionError):
                    expires_at = None

                status_list.append({
                    "platform": platform,
                    "status": "connected",
                    "connected_at": expires_at,
                })
            else:
                status_list.append({
                    "platform": platform,
                    "status": "disconnected",
                })
        except Exception as e:
            logger.error(
                "status_check_failed", platform=platform, error=str(e)
            )
            status_list.append({
                "platform": platform,
                "status": "disconnected",
            })

    logger.info("oauth_status_retrieved", user_id=user["id"])
    return status_list


@router.delete("/{platform}/disconnect", response_model=DisconnectResponse)
async def disconnect(
    platform: PlatformName,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectResponse:
    """Disconnect and delete OAuth tokens for a platform.

    Revokes the OAuth connection by deleting stored tokens.
    Note: This does not revoke the token on the platform's side - users should
    do that manually in their platform settings if needed.

    Args:
        platform: Platform name
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If token deletion fails or token not found
    """
    _check_admin_role(user)

    token_manager = TokenManager()
    try:
        await token_manager.revoke_token(db, platform)
        logger.info(
            "oauth_disconnected",
            platform=platform,
            user_id=user["id"],
        )
        return DisconnectResponse(
            success=True,
            platform=platform,
            message=f"Successfully disconnected from {platform}",
        )
    except TokenNotFoundError as e:
        logger.warning(
            "disconnect_token_not_found",
            platform=platform,
            user_id=user["id"],
        )
        raise HTTPException(
            status_code=404, detail=f"No connection found for {platform}"
        ) from e
    except OAuthError as e:
        logger.error(
            "disconnect_failed",
            platform=platform,
            user_id=user["id"],
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to disconnect: {str(e)}"
        ) from e
