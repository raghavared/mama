"""Instagram Graph API publisher."""
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

logger = structlog.get_logger(__name__)

INSTAGRAM_GRAPH_URL = "https://graph.instagram.com/v21.0"


class InstagramPublisher(BasePublisher):
    """Publishes image and video posts to Instagram via Graph API."""

    platform = Platform.INSTAGRAM
    platform_name = "instagram"

    async def publish(self, job: ContentJob, asset_path: str, caption: str) -> PublishedPost:
        """Publish content to Instagram."""
        # Check if in development mode
        if self.settings.is_development:
            return self._stub_post(job, "instagram")

        # Get access token from database (with env var fallback)
        try:
            access_token = await self.get_access_token(fallback_env_var="instagram_access_token")
        except (TokenNotFoundError, TokenExpiredError) as e:
            self.logger.error("instagram_token_error", job_id=str(job.id), error=str(e))
            return self._stub_post(job, "instagram")

        formatted_caption = self.format_caption(caption, Platform.INSTAGRAM)
        hashtags = self.get_hashtags(job)
        if hashtags:
            formatted_caption += "\n\n" + " ".join(hashtags[:10])

        is_video = asset_path.endswith((".mp4", ".mov"))

        try:
            if is_video:
                post_id = await self._publish_reel(asset_path, formatted_caption, access_token)
            else:
                post_id = await self._publish_image(asset_path, formatted_caption, access_token)

            post_url = f"https://www.instagram.com/p/{post_id}/"
            self.logger.info("Published to Instagram", job_id=str(job.id), post_id=post_id)
            return PublishedPost(
                job_id=job.id,
                platform=Platform.INSTAGRAM,
                platform_post_id=post_id,
                post_url=post_url,
                posted_at=datetime.utcnow(),
            )
        except Exception as exc:
            self.logger.error("Instagram publish failed", job_id=str(job.id), error=str(exc))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
    async def _publish_image(self, image_url: str, caption: str, access_token: str) -> str:
        """Upload and publish an image post."""
        account_id = self.settings.instagram_account_id

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Create media container
            create_resp = await client.post(
                f"{INSTAGRAM_GRAPH_URL}/{account_id}/media",
                params={
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": access_token,
                },
            )
            create_resp.raise_for_status()
            container_id = create_resp.json()["id"]

            # Step 2: Publish the container
            publish_resp = await client.post(
                f"{INSTAGRAM_GRAPH_URL}/{account_id}/media_publish",
                params={"creation_id": container_id, "access_token": access_token},
            )
            publish_resp.raise_for_status()
            return publish_resp.json()["id"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
    async def _publish_reel(self, video_url: str, caption: str, access_token: str) -> str:
        """Upload and publish a Reel."""
        account_id = self.settings.instagram_account_id

        async with httpx.AsyncClient(timeout=120.0) as client:
            create_resp = await client.post(
                f"{INSTAGRAM_GRAPH_URL}/{account_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "share_to_feed": "true",
                    "access_token": access_token,
                },
            )
            create_resp.raise_for_status()
            container_id = create_resp.json()["id"]

            publish_resp = await client.post(
                f"{INSTAGRAM_GRAPH_URL}/{account_id}/media_publish",
                params={"creation_id": container_id, "access_token": access_token},
            )
            publish_resp.raise_for_status()
            return publish_resp.json()["id"]

    def _stub_post(self, job: ContentJob, platform: str) -> PublishedPost:
        stub_id = f"stub_{uuid.uuid4().hex[:8]}"
        return PublishedPost(
            job_id=job.id,
            platform=Platform.INSTAGRAM,
            platform_post_id=stub_id,
            post_url=f"https://www.instagram.com/p/{stub_id}/",
            posted_at=datetime.utcnow(),
        )
