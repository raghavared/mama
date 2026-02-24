"""Facebook Graph API publisher."""
from __future__ import annotations

import uuid
from datetime import datetime

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import ContentJob, Platform, PublishedPost
from .base_publisher import BasePublisher

FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v21.0"


class FacebookPublisher(BasePublisher):
    platform = Platform.FACEBOOK

    async def publish(self, job: ContentJob, asset_path: str, caption: str) -> PublishedPost:
        if not self.settings.facebook_access_token or self.settings.is_development:
            stub_id = f"stub_{uuid.uuid4().hex[:8]}"
            return PublishedPost(job_id=job.id, platform=Platform.FACEBOOK,
                                 platform_post_id=stub_id,
                                 post_url=f"https://www.facebook.com/{stub_id}",
                                 posted_at=datetime.utcnow())

        formatted_caption = self.format_caption(caption, Platform.FACEBOOK)
        is_video = asset_path.endswith((".mp4", ".mov"))

        try:
            post_id = await self._post_to_page(formatted_caption, asset_path, is_video)
            self.logger.info("Published to Facebook", job_id=str(job.id), post_id=post_id)
            return PublishedPost(job_id=job.id, platform=Platform.FACEBOOK,
                                 platform_post_id=post_id,
                                 post_url=f"https://www.facebook.com/{post_id}",
                                 posted_at=datetime.utcnow())
        except Exception as exc:
            self.logger.error("Facebook publish failed", job_id=str(job.id), error=str(exc))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
    async def _post_to_page(self, caption: str, asset_url: str, is_video: bool) -> str:
        page_id = self.settings.facebook_page_id
        token = self.settings.facebook_access_token

        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_video:
                response = await client.post(
                    f"{FACEBOOK_GRAPH_URL}/{page_id}/videos",
                    params={"file_url": asset_url, "description": caption, "access_token": token},
                )
            else:
                response = await client.post(
                    f"{FACEBOOK_GRAPH_URL}/{page_id}/photos",
                    params={"url": asset_url, "caption": caption, "access_token": token},
                )
            response.raise_for_status()
            return response.json().get("id", "unknown")
