"""Dashboard statistics and analytics endpoints — backed by PostgreSQL."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, ContentJobORM
from .auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()


class DashboardStatsResponse(BaseModel):
    total_jobs: int = 0
    active_jobs: int = 0
    published_today: int = 0
    approval_pending: int = 0
    total_impressions: int = 0
    total_engagement: int = 0
    cost_today: float = 0.0
    jobs_by_status: dict[str, int] = {}
    jobs_by_platform: dict[str, int] = {}
    recent_activity: list[dict] = []


class AgentActivityResponse(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    action: str
    job_id: str
    timestamp: str
    details: dict = {}
    status: str = "info"


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsResponse:
    """Get aggregated dashboard statistics from the database."""
    # Total jobs
    total_result = await db.execute(select(func.count()).select_from(ContentJobORM))
    total_jobs = total_result.scalar() or 0

    # Jobs by status
    status_result = await db.execute(
        select(ContentJobORM.status, func.count())
        .group_by(ContentJobORM.status)
    )
    jobs_by_status = {row[0]: row[1] for row in status_result.all()}

    active_statuses = {"pending", "in_progress", "paused"}
    active_jobs = sum(jobs_by_status.get(s, 0) for s in active_statuses)
    approval_pending = jobs_by_status.get("awaiting_approval", 0)

    return DashboardStatsResponse(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        published_today=jobs_by_status.get("published", 0),
        approval_pending=approval_pending,
        total_impressions=0,
        total_engagement=0,
        cost_today=0.0,
        jobs_by_status=jobs_by_status,
        jobs_by_platform={},
        recent_activity=[],
    )


@router.get("/agents/activity", response_model=list[AgentActivityResponse])
async def get_agent_activity(
    limit: int = 50,
    user: dict = Depends(get_current_user),
) -> list[AgentActivityResponse]:
    """Get recent agent activity logs."""
    return []
