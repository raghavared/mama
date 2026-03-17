"""Multi-Platform Publisher — orchestrates publishing to all platforms in parallel."""
from __future__ import annotations

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ContentJob, Platform, PublishedPost
from .instagram import InstagramPublisher
from .linkedin import LinkedInPublisher
from .facebook import FacebookPublisher
from .twitter import TwitterPublisher
from .youtube import YouTubePublisher

logger = structlog.get_logger(__name__)


class MultiPlatformPublisher:
    """Publishes content to multiple social platforms in parallel."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._publishers = {
            Platform.INSTAGRAM: InstagramPublisher(db),
            Platform.LINKEDIN: LinkedInPublisher(db),
            Platform.FACEBOOK: FacebookPublisher(db),
            Platform.X_TWITTER: TwitterPublisher(db),
            Platform.YOUTUBE: YouTubePublisher(db),
        }

    async def publish_all(
        self,
        job: ContentJob,
        asset_path: str,
        platforms: list[Platform],
    ) -> list[PublishedPost]:
        """
        Publish content to all specified platforms simultaneously.

        Returns list of PublishedPost records for each successful publication.
        """
        # Get the caption for this job
        caption = self._get_caption(job)

        # Build per-platform publish tasks
        tasks = {}
        for platform in platforms:
            publisher = self._publishers.get(platform)
            if publisher:
                platform_caption = publisher.format_caption(caption, platform)
                tasks[platform] = publisher.publish(job, asset_path, platform_caption)

        # Execute all in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        published_posts = []
        for platform, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(
                    "Platform publish failed",
                    platform=platform.value,
                    job_id=str(job.id),
                    error=str(result),
                )
            else:
                published_posts.append(result)
                job.published_posts.append(result)

        logger.info(
            "Multi-platform publish complete",
            job_id=str(job.id),
            published_count=len(published_posts),
            total_platforms=len(platforms),
        )
        return published_posts

    def _get_caption(self, job: ContentJob) -> str:
        """Extract caption from job script or metadata."""
        if job.script:
            return job.script.content

        # Try to get from metadata
        extended = job.metadata.get("cst_script_extended") or job.metadata.get("vst_script_extended") or {}
        return extended.get("full_caption") or job.topic
