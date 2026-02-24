"""Base publisher abstract class."""
from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from src.config import get_settings
from src.models import ContentJob, Platform, PublishedPost


class BasePublisher(ABC):
    """Abstract base for all social platform publishers."""

    platform: Platform

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    async def publish(
        self,
        job: ContentJob,
        asset_path: str,
        caption: str,
    ) -> PublishedPost:
        """Publish content to the platform and return a PublishedPost record."""
        ...

    def format_caption(self, caption: str, platform: Platform) -> str:
        """Platform-specific caption formatting."""
        if platform == Platform.X_TWITTER:
            # Twitter: 280 char limit
            if len(caption) > 270:
                return caption[:267] + "..."
        elif platform == Platform.INSTAGRAM:
            # Instagram: 2200 char limit
            if len(caption) > 2200:
                return caption[:2197] + "..."
        elif platform == Platform.LINKEDIN:
            # LinkedIn: 3000 char limit
            if len(caption) > 3000:
                return caption[:2997] + "..."
        return caption

    def get_hashtags(self, job: ContentJob) -> list[str]:
        """Extract hashtags from job metadata."""
        extended = job.metadata.get("cst_script_extended") or job.metadata.get("vst_script_extended") or {}
        return extended.get("hashtags", [])
