"""LinkedIn API v2 publisher."""
from __future__ import annotations

import uuid
from datetime import datetime

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models import ContentJob, Platform, PublishedPost
from .base_publisher import BasePublisher

LINKEDIN_API_URL = "https://api.linkedin.com/v2"


class LinkedInPublisher(BasePublisher):
    platform = Platform.LINKEDIN

    async def publish(self, job: ContentJob, asset_path: str, caption: str) -> PublishedPost:
        if not self.settings.linkedin_access_token or self.settings.is_development:
            stub_id = f"stub_{uuid.uuid4().hex[:8]}"
            return PublishedPost(job_id=job.id, platform=Platform.LINKEDIN,
                                 platform_post_id=stub_id,
                                 post_url=f"https://www.linkedin.com/feed/update/{stub_id}/",
                                 posted_at=datetime.utcnow())

        formatted_caption = self.format_caption(caption, Platform.LINKEDIN)
        is_video = asset_path.endswith((".mp4", ".mov"))

        try:
            post_id = await self._create_post(formatted_caption, asset_path, is_video)
            self.logger.info("Published to LinkedIn", job_id=str(job.id), post_id=post_id)
            return PublishedPost(job_id=job.id, platform=Platform.LINKEDIN,
                                 platform_post_id=post_id,
                                 post_url=f"https://www.linkedin.com/feed/update/{post_id}/",
                                 posted_at=datetime.utcnow())
        except Exception as exc:
            self.logger.error("LinkedIn publish failed", job_id=str(job.id), error=str(exc))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30))
    async def _create_post(self, caption: str, asset_url: str, is_video: bool) -> str:
        token = self.settings.linkedin_access_token
        org_id = self.settings.linkedin_org_id
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "X-Restli-Protocol-Version": "2.0.0"}

        media_category = "VIDEO" if is_video else "IMAGE"
        payload = {
            "author": f"urn:li:organization:{org_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": media_category,
                    "media": [{"status": "READY", "originalUrl": asset_url}],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{LINKEDIN_API_URL}/ugcPosts", headers=headers, json=payload)
            response.raise_for_status()
            return response.headers.get("x-restli-id", response.json().get("id", "unknown"))
