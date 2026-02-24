"""YouTube Data API v3 publisher."""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog

from src.models import ContentJob, Platform, PublishedPost
from .base_publisher import BasePublisher


class YouTubePublisher(BasePublisher):
    platform = Platform.YOUTUBE

    async def publish(self, job: ContentJob, asset_path: str, caption: str) -> PublishedPost:
        if not self.settings.youtube_api_key or self.settings.is_development:
            stub_id = f"stub_{uuid.uuid4().hex[:8]}"
            return PublishedPost(job_id=job.id, platform=Platform.YOUTUBE,
                                 platform_post_id=stub_id,
                                 post_url=f"https://www.youtube.com/watch?v={stub_id}",
                                 posted_at=datetime.utcnow())

        if not asset_path.endswith((".mp4", ".mov")):
            self.logger.info("YouTube only supports video posts — skipping", job_id=str(job.id))
            stub_id = f"skip_{uuid.uuid4().hex[:8]}"
            return PublishedPost(job_id=job.id, platform=Platform.YOUTUBE,
                                 platform_post_id=stub_id, post_url="", posted_at=datetime.utcnow())

        try:
            video_id = await self._upload_video(job, asset_path, caption)
            self.logger.info("Published to YouTube", job_id=str(job.id), video_id=video_id)
            return PublishedPost(job_id=job.id, platform=Platform.YOUTUBE,
                                 platform_post_id=video_id,
                                 post_url=f"https://www.youtube.com/watch?v={video_id}",
                                 posted_at=datetime.utcnow())
        except Exception as exc:
            self.logger.error("YouTube upload failed", job_id=str(job.id), error=str(exc))
            raise

    async def _upload_video(self, job: ContentJob, video_path: str, description: str) -> str:
        """Upload video to YouTube using google-api-python-client."""
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials

        creds = Credentials(token=self.settings.youtube_api_key)
        youtube = build("youtube", "v3", credentials=creds)

        extended = job.metadata.get("vst_script_extended", {})
        title = extended.get("title") or f"{job.topic[:50]} | {job.metadata.get('brand_name', 'Content')}"
        tags = self.get_hashtags(job)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:15],
                "categoryId": "22",  # People & Blogs
            },
            "status": {"privacyStatus": "public"},
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        return response.get("id", "unknown")
