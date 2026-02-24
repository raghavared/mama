"""Celery application for async task processing."""
from __future__ import annotations

from celery import Celery

from src.config import get_settings

settings = get_settings()

celery_app = Celery(
    "mama",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker (media gen is heavy)
    task_routes={
        "src.worker.tasks.trigger_content_job": {"queue": "default"},
        "src.worker.tasks.generate_video": {"queue": "media_generation"},
        "src.worker.tasks.generate_image": {"queue": "media_generation"},
        "src.worker.tasks.generate_audio": {"queue": "media_generation"},
        "src.worker.tasks.publish_content": {"queue": "publishing"},
    },
    beat_schedule={
        "trending-topics-scan": {
            "task": "src.worker.tasks.scan_trending_topics",
            "schedule": 3600.0,  # Every hour
        },
    },
)
