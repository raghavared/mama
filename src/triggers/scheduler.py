"""Content scheduler — manages automatic content generation cron jobs."""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class ContentScheduler:
    """
    Manages scheduled content generation using APScheduler.

    Supports:
    - Hourly trending topic scans
    - Custom scheduled content topics
    - Platform-specific scheduling
    """

    def __init__(self) -> None:
        self._scheduler = None
        self.logger = structlog.get_logger(self.__class__.__name__)

    def start(self) -> None:
        """Start the scheduler with default jobs."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._scan_and_trigger,
                "interval",
                hours=1,
                id="trending_scan",
                replace_existing=True,
            )
            self._scheduler.start()
            self.logger.info("Content scheduler started")
        except ImportError:
            self.logger.warning("APScheduler not installed — using Celery beat for scheduling")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()
            self.logger.info("Content scheduler stopped")

    def add_scheduled_job(
        self,
        topic: str,
        cron_expression: str,
        platforms: Optional[list[str]] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Add a custom scheduled content job."""
        if not self._scheduler:
            raise RuntimeError("Scheduler not started")

        from apscheduler.triggers.cron import CronTrigger

        _job_id = job_id or f"scheduled_{topic[:20].replace(' ', '_')}"

        self._scheduler.add_job(
            self._trigger_topic,
            CronTrigger.from_crontab(cron_expression),
            args=[topic, platforms or ["instagram", "linkedin"]],
            id=_job_id,
            replace_existing=True,
        )
        self.logger.info("Scheduled job added", job_id=_job_id, topic=topic, cron=cron_expression)
        return _job_id

    async def _scan_and_trigger(self) -> None:
        """Fetch trending topics and trigger content generation."""
        from src.triggers.trending import TrendingTopicDetector
        from src.worker.tasks import trigger_content_job

        detector = TrendingTopicDetector()
        topics = await detector.get_trending_topics()

        for topic in topics[:3]:
            trigger_content_job.delay(topic, "trending")
            self.logger.info("Auto-triggered topic", topic=topic)

    async def _trigger_topic(self, topic: str, platforms: list[str]) -> None:
        from src.worker.tasks import trigger_content_job
        trigger_content_job.delay(topic, "scheduled", {"platforms": platforms})
        self.logger.info("Scheduled topic triggered", topic=topic)
