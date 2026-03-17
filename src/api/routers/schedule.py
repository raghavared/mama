"""Scheduling management API endpoints — backed by PostgreSQL."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, ScheduledJobORM
from .auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/schedule")


class ScheduledJobRequest(BaseModel):
    topic: str
    cron_expression: str = "0 9 * * 1-5"
    platforms: list[str] = ["instagram", "linkedin"]
    enabled: bool = True


class ScheduledJobResponse(BaseModel):
    id: str
    topic: str
    cron_expression: str
    platforms: list[str]
    enabled: bool
    next_run: str
    last_run: str | None = None


@router.get("", response_model=list[ScheduledJobResponse])
async def list_scheduled_jobs(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledJobResponse]:
    """List all scheduled content jobs."""
    result = await db.execute(select(ScheduledJobORM).order_by(ScheduledJobORM.created_at.desc()))
    return [_to_response(j) for j in result.scalars().all()]


@router.post("", response_model=ScheduledJobResponse, status_code=201)
async def create_scheduled_job(
    request: ScheduledJobRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScheduledJobResponse:
    """Create a new scheduled content job."""
    job = ScheduledJobORM(
        id=uuid.uuid4(),
        topic=request.topic,
        cron_expression=request.cron_expression,
        platforms=request.platforms,
        enabled=request.enabled,
        next_run=datetime.now(timezone.utc),
        created_by=uuid.UUID(user["id"]),
    )
    db.add(job)
    await db.flush()
    logger.info("Scheduled job created", job_id=str(job.id), topic=request.topic)
    return _to_response(job)


@router.delete("/{job_id}", status_code=204, response_model=None)
async def delete_scheduled_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a scheduled job."""
    result = await db.execute(select(ScheduledJobORM).where(ScheduledJobORM.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    await db.delete(job)
    await db.flush()
    logger.info("Scheduled job deleted", job_id=job_id)


def _to_response(job: ScheduledJobORM) -> ScheduledJobResponse:
    return ScheduledJobResponse(
        id=str(job.id),
        topic=job.topic,
        cron_expression=job.cron_expression,
        platforms=job.platforms or [],
        enabled=job.enabled,
        next_run=job.next_run.isoformat() if job.next_run else datetime.now(timezone.utc).isoformat(),
        last_run=job.last_run.isoformat() if job.last_run else None,
    )
