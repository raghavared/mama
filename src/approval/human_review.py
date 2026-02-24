"""Human-in-the-Loop review handler."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import httpx
import structlog

from src.config import get_settings
from src.models import ApprovalRecord, ApprovalGate, ContentJob, ContentJobStatus

logger = structlog.get_logger(__name__)


class HumanReviewHandler:
    """
    Manages human-in-the-loop approval for final content before publishing.

    Sends webhook notifications to human reviewers and processes their decisions.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def request_review(self, job: ContentJob, review_url: Optional[str] = None) -> None:
        """
        Notify human reviewers that content is ready for review.

        Sends a webhook POST to HUMAN_REVIEW_WEBHOOK_URL with job details.
        """
        webhook_url = review_url or self.settings.__dict__.get("human_review_webhook_url", "")

        self.logger.info(
            "Requesting human review",
            job_id=str(job.id),
            status=job.status.value,
        )

        if not webhook_url:
            self.logger.warning(
                "No human review webhook configured — skipping notification",
                job_id=str(job.id),
            )
            return

        payload = {
            "job_id": str(job.id),
            "topic": job.topic,
            "pipeline_type": job.pipeline_type.value if job.pipeline_type else None,
            "status": job.status.value,
            "media_assets": [
                {"type": a.type, "path": a.file_path, "source": a.source}
                for a in job.media_assets
            ],
            "script_preview": job.script.content[:200] if job.script else None,
            "approval_url": f"{self.settings.api_host}:{self.settings.api_port}/api/v1/jobs/{job.id}/approve",
            "requested_at": datetime.utcnow().isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                self.logger.info("Human review webhook sent", job_id=str(job.id), status=response.status_code)
        except Exception as exc:
            self.logger.error(
                "Failed to send human review webhook",
                job_id=str(job.id),
                error=str(exc),
            )

    def record_human_decision(
        self,
        job: ContentJob,
        decision: str,
        reviewer_id: str,
        feedback: Optional[str] = None,
    ) -> ApprovalRecord:
        """
        Record a human approval/rejection decision for a job.

        Called by the API endpoint when a human reviewer submits their decision.
        """
        record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=job.id,
            gate=ApprovalGate.HUMAN,
            subject_type="final_content",
            subject_id=uuid.uuid4(),
            decision=decision,
            feedback=feedback,
            reviewer=reviewer_id,
            reviewed_at=datetime.utcnow(),
        )

        job.add_approval(record)

        if decision == "approved":
            job.update_status(ContentJobStatus.PUBLISHING)
            self.logger.info("Human approved content", job_id=str(job.id), reviewer=reviewer_id)
        else:
            job.update_status(ContentJobStatus.REJECTED)
            self.logger.info(
                "Human rejected content",
                job_id=str(job.id),
                reviewer=reviewer_id,
                feedback=feedback,
            )

        return record
