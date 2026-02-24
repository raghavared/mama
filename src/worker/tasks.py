"""Celery tasks for async content generation pipeline."""
from __future__ import annotations

import asyncio
import uuid

import structlog

from .celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="src.worker.tasks.trigger_content_job",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def trigger_content_job(self, topic: str, topic_source: str = "manual", metadata: dict | None = None):
    """Trigger the full MAMA content generation pipeline for a topic."""
    from src.workflows.mama_workflow import MAMAWorkflow
    from src.models import TopicSource

    logger.info("Starting content job", topic=topic, source=topic_source, task_id=self.request.id)

    workflow = MAMAWorkflow()
    try:
        result = asyncio.run(
            workflow.trigger(
                topic=topic,
                topic_source=TopicSource(topic_source),
                metadata=metadata or {},
            )
        )
        logger.info(
            "Content job complete",
            job_id=str(result.job.id),
            status=result.job.status.value,
            pipeline=result.pipeline_type,
        )
        return {
            "job_id": str(result.job.id),
            "status": result.job.status.value,
            "pipeline_type": result.pipeline_type,
        }
    except Exception as exc:
        logger.error("Content job failed", topic=topic, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="src.worker.tasks.scan_trending_topics")
def scan_trending_topics():
    """Hourly task to scan trending topics and trigger content generation."""
    from src.triggers.trending import TrendingTopicDetector

    logger.info("Scanning trending topics")
    detector = TrendingTopicDetector()
    topics = asyncio.run(detector.get_trending_topics())

    triggered = []
    for topic in topics[:3]:  # Limit to top 3 trending topics per scan
        result = trigger_content_job.delay(topic, "trending")
        triggered.append({"topic": topic, "task_id": result.id})
        logger.info("Triggered content job for trending topic", topic=topic)

    return {"triggered": triggered}
