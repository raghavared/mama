"""X/Twitter API v2 publisher."""
from __future__ import annotations

import uuid
from datetime import datetime

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import ContentJob, Platform, PublishedPost
from src.oauth.exceptions import TokenNotFoundError, TokenExpiredError
from .base_publisher import BasePublisher

TWITTER_API_URL = "https://api.twitter.com/2"


class TwitterPublisher(BasePublisher):
    platform = Platform.X_TWITTER
    platform_name = "twitter"

    async def publish(self, job: ContentJob, asset_path: str, caption: str) -> PublishedPost:
        # Check if in development mode
        if self.settings.is_development:
            stub_id = f"stub_{uuid.uuid4().hex[:8]}"
            return PublishedPost(job_id=job.id, platform=Platform.X_TWITTER,
                                 platform_post_id=stub_id,
                                 post_url=f"https://x.com/i/web/status/{stub_id}",
                                 posted_at=datetime.utcnow())

        # Get access token from database (with env var fallback)
        try:
            token_data = await self.token_manager.get_token(self.db, self.platform_name)
            # Check if token is valid
            is_valid = await self.token_manager.is_token_valid(self.db, self.platform_name)
            if not is_valid:
                self.logger.warning("token_expired", platform=self.platform_name)
                raise TokenExpiredError(f"Token expired for {self.platform_name}")

            access_token = token_data["access_token"]
            # Twitter OAuth 1.0a requires additional secrets stored in extra_data
            extra_data = token_data.get("extra_data", {})

        except (TokenNotFoundError, TokenExpiredError) as e:
            # Fallback to environment variables
            self.logger.info("twitter_using_fallback_tokens", job_id=str(job.id), error=str(e))
            if not self.settings.twitter_bearer_token:
                self.logger.error("twitter_token_error", job_id=str(job.id), error=str(e))
                stub_id = f"stub_{uuid.uuid4().hex[:8]}"
                return PublishedPost(job_id=job.id, platform=Platform.X_TWITTER,
                                     platform_post_id=stub_id,
                                     post_url=f"https://x.com/i/web/status/{stub_id}",
                                     posted_at=datetime.utcnow())
            # Use fallback from env vars
            access_token = self.settings.twitter_access_token
            extra_data = {
                "api_key": self.settings.twitter_api_key,
                "api_secret": self.settings.twitter_api_secret,
                "access_token_secret": self.settings.twitter_access_token_secret,
            }

        formatted_caption = self.format_caption(caption, Platform.X_TWITTER)

        try:
            tweet_id = await self._post_tweet(formatted_caption, access_token, extra_data)
            self.logger.info("Published to X/Twitter", job_id=str(job.id), tweet_id=tweet_id)
            return PublishedPost(job_id=job.id, platform=Platform.X_TWITTER,
                                 platform_post_id=tweet_id,
                                 post_url=f"https://x.com/i/web/status/{tweet_id}",
                                 posted_at=datetime.utcnow())
        except Exception as exc:
            self.logger.error("Twitter publish failed", job_id=str(job.id), error=str(exc))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
    async def _post_tweet(self, text: str, access_token: str, extra_data: dict) -> str:
        import hmac, hashlib, time, base64, os, urllib.parse

        # Extract OAuth 1.0a credentials
        api_key = extra_data.get("api_key", self.settings.twitter_api_key)
        api_secret = extra_data.get("api_secret", self.settings.twitter_api_secret)
        access_token_secret = extra_data.get("access_token_secret", self.settings.twitter_access_token_secret)

        oauth_params = {
            "oauth_consumer_key": api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": access_token,
            "oauth_version": "1.0",
        }

        payload = {"text": text}

        # Build OAuth signature
        base_params = {**oauth_params}
        sorted_params = "&".join([f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}"
                                  for k, v in sorted(base_params.items())])
        base_string = f"POST&{urllib.parse.quote(f'{TWITTER_API_URL}/tweets')}&{urllib.parse.quote(sorted_params)}"
        signing_key = f"{urllib.parse.quote(api_secret)}&{urllib.parse.quote(access_token_secret)}"
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()
        oauth_params["oauth_signature"] = signature

        auth_header = "OAuth " + ", ".join([f'{k}="{urllib.parse.quote(v)}"' for k, v in oauth_params.items()])

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TWITTER_API_URL}/tweets",
                headers={"Authorization": auth_header, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("data", {}).get("id", "unknown")
