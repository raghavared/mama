"""Content job management API endpoints with pipeline execution + DB persistence."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db, AsyncSessionLocal, ContentJobORM, MediaAssetORM
from src.config.settings import get_settings
from .auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()

# ─── In-memory state for active pipelines (runtime only) ─────────────────────

_paused_jobs: set[str] = set()
_running_tasks: dict[str, bool] = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TriggerJobRequest(BaseModel):
    topic: str
    topic_source: str = "manual"
    platforms: list[str] = ["instagram", "linkedin", "facebook"]
    name: Optional[str] = None
    description: Optional[str] = None


class TriggerJobResponse(BaseModel):
    job_id: str
    status: str


class ApprovalRequest(BaseModel):
    decision: str
    reviewer_id: str
    feedback: Optional[str] = None


class ApprovalResponse(BaseModel):
    job_id: str
    decision: str
    status: str


class JobListResponse(BaseModel):
    jobs: list[dict]
    total: int
    offset: int
    limit: int


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _s3_key_from_url(url: str, bucket: str, region: str) -> str | None:
    """Extract the S3 key from any known S3 URL/URI format, or return None."""
    # s3:// protocol: s3://<bucket>/<key>
    s3_prefix = f"s3://{bucket}/"
    if url.startswith(s3_prefix):
        return url[len(s3_prefix):]
    # Virtual-hosted: https://<bucket>.s3.<region>.amazonaws.com/<key>
    vhost_prefix = f"https://{bucket}.s3.{region}.amazonaws.com/"
    if url.startswith(vhost_prefix):
        return url[len(vhost_prefix):]
    # Path-style: https://s3.<region>.amazonaws.com/<bucket>/<key>
    path_prefix = f"https://s3.{region}.amazonaws.com/{bucket}/"
    if url.startswith(path_prefix):
        return url[len(path_prefix):]
    return None


def _media_url(file_path: str) -> str:
    """Convert a storage file path to a browser-accessible URL.

    Rewrites any old S3 URL (s3://, virtual-hosted, or path-style) to the
    CloudFront CDN URL when cdn_domain is configured.
    """
    from pathlib import Path as _Path
    if not file_path or file_path.startswith("stub:"):
        return file_path

    settings = get_settings()

    # s3:// protocol → CDN or path-style HTTPS
    if file_path.startswith("s3://"):
        key = _s3_key_from_url(file_path, settings.s3_bucket_name, settings.s3_region)
        if key:
            if settings.cdn_domain:
                return f"https://{settings.cdn_domain}/{key}"
            return f"https://s3.{settings.s3_region}.amazonaws.com/{settings.s3_bucket_name}/{key}"
        return file_path

    if file_path.startswith("https://") or file_path.startswith("http://"):
        # Rewrite old S3 URLs to CDN URL if cdn_domain is set
        if settings.cdn_domain:
            cdn_prefix = f"https://{settings.cdn_domain}/"
            if not file_path.startswith(cdn_prefix):
                key = _s3_key_from_url(file_path, settings.s3_bucket_name, settings.s3_region)
                if key:
                    return f"https://{settings.cdn_domain}/{key}"
        return file_path

    # Local path → /media/ relative URL
    prefix = str(_Path(settings.local_storage_path))
    norm = str(_Path(file_path))
    if norm.startswith(prefix):
        relative = norm[len(prefix):].lstrip("/")
        return f"/media/{relative}"
    try:
        rel = str(_Path(file_path).relative_to(_Path(settings.local_storage_path).resolve()))
        return f"/media/{rel}"
    except ValueError:
        pass
    return file_path


def _orm_to_dict(orm: ContentJobORM) -> dict:
    """Convert ORM row to the dict shape the frontend expects."""
    return {
        "id": str(orm.id),
        "name": orm.name,
        "description": orm.description,
        "topic": orm.topic,
        "topic_source": orm.topic_source,
        "pipeline_type": orm.pipeline_type,
        "status": orm.status,
        "current_step": orm.current_step,
        "pipeline_logs": orm.pipeline_logs or [],
        "created_at": orm.created_at.isoformat() if orm.created_at else _now(),
        "updated_at": orm.updated_at.isoformat() if orm.updated_at else _now(),
        "improvement_count": orm.improvement_count or 0,
        "reinitiation_count": orm.reinitiation_count or 0,
        "run_history": orm.run_history or [],
        "error_message": orm.error_message,
        "content_brief": orm.content_brief,
        "script": orm.script_data,
        "media_assets": [
            {
                "id": str(a.id),
                "type": a.type,
                "source": a.source,
                "file_path": a.file_path,
                "format": a.format,
                "quality_score": a.quality_score,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "metadata": a.metadata_ or {},
                "url": _media_url(a.file_path),
            }
            for a in (orm.media_assets or [])
        ],
        "approval_records": [],
        "published_posts": [],
        "metadata": orm.metadata_ or {},
    }


async def _save_job_field(job_id: str, **fields) -> None:
    """Update specific fields on a job in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return
        for key, val in fields.items():
            setattr(orm, key, val)
        orm.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def _save_media_assets(job_id: str, assets: list) -> None:
    """Persist in-memory MediaAsset objects to the media_assets DB table."""
    if not assets:
        return
    async with AsyncSessionLocal() as session:
        for asset in assets:
            orm = MediaAssetORM(
                id=asset.id,
                job_id=uuid.UUID(job_id),
                type=asset.type,
                source=asset.source,
                file_path=asset.file_path,
                format=asset.format,
                quality_score=asset.quality_score,
                metadata_=asset.metadata or {},
            )
            session.add(orm)
        await session.commit()


async def _broadcast_event(event_type: str, job_id: str, data: dict) -> None:
    """Send a real-time event to all connected WebSocket clients."""
    try:
        from src.api.main import ws_manager
        await ws_manager.broadcast({
            "type": event_type,
            "payload": {"job_id": job_id, **data},
            "timestamp": _now(),
        })
    except Exception:
        pass


async def _check_paused(job_id: str) -> None:
    """Block while job is paused."""
    while job_id in _paused_jobs:
        if job_id not in _running_tasks:
            raise asyncio.CancelledError("Job cancelled")
        await asyncio.sleep(1)


async def _log_step(job_id: str, step: str, status: str, detail: str = "") -> None:
    """Append a step log entry to the job in DB."""
    entry = {"step": step, "status": status, "detail": detail, "timestamp": _now()}
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return
        logs = list(orm.pipeline_logs or [])
        logs.append(entry)
        orm.pipeline_logs = logs
        if status == "running":
            orm.current_step = step
        orm.updated_at = datetime.now(timezone.utc)
        await session.commit()


# ─── Pipeline runner ─────────────────────────────────────────────────────────

async def run_pipeline(job_id: str) -> None:
    """Run the full MAMA pipeline for a job as a background task."""
    _running_tasks[job_id] = True

    # Load job from DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return
        topic = orm.topic
        topic_source = orm.topic_source
        job_name = orm.name
        job_description = orm.description

    logger.info("PIPELINE START", job_id=job_id, topic=topic)
    await _broadcast_event("pipeline_start", job_id, {"topic": topic})

    try:
        # ── Step 1: MAMA Agent — Topic Enrichment ────────────────────────
        await _check_paused(job_id)
        await _save_job_field(job_id, status="in_progress")
        await _log_step(job_id, "mama_enrichment", "running", "MAMA agent analyzing topic...")
        logger.info("STEP 1/5  MAMA agent enriching topic...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "mama_enrichment", "status": "running"})

        from src.agents.mama import MAMAAgent
        from src.agents.base import AgentState
        from src.models import ContentJob, TopicSource

        source = TopicSource(topic_source) if topic_source in ("manual", "trending", "scheduled") else TopicSource.MANUAL
        content_job = ContentJob(
            id=uuid.UUID(job_id),
            name=job_name,
            description=job_description,
            topic=topic,
            topic_source=source,
        )
        state = AgentState(job=content_job)

        mama = MAMAAgent()
        state = await mama.run(state)

        if state.error:
            await _save_job_field(job_id, status="failed", error_message=state.error, current_step=None)
            await _log_step(job_id, "mama_enrichment", "failed", state.error)
            logger.error("PIPELINE FAILED at MAMA", job_id=job_id, error=state.error)
            await _broadcast_event("step_update", job_id, {"step": "mama_enrichment", "status": "failed", "error": state.error})
            return

        await _log_step(job_id, "mama_enrichment", "done", f"Engagement: {state.enriched_topic.get('estimated_engagement_potential', '?') if state.enriched_topic else '?'}")
        logger.info("STEP 1/6  MAMA done", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "mama_enrichment", "status": "done"})

        # ── Step 2: GTM Head — Go-To-Market Strategy ─────────────────────
        await _check_paused(job_id)
        await _log_step(job_id, "gtm_strategy", "running", "GTM Head building go-to-market strategy...")
        logger.info("STEP 2/6  GTM Head building strategy...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "gtm_strategy", "status": "running"})

        from src.agents.gtm import GTMHeadAgent
        gtm = GTMHeadAgent()
        state = await gtm.run(state)

        if state.error:
            await _save_job_field(job_id, status="failed", error_message=state.error, current_step=None)
            await _log_step(job_id, "gtm_strategy", "failed", state.error)
            logger.error("PIPELINE FAILED at GTM", job_id=job_id, error=state.error)
            await _broadcast_event("step_update", job_id, {"step": "gtm_strategy", "status": "failed", "error": state.error})
            return

        # Save GTM strategy to job metadata
        if state.gtm_strategy:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
                )
                orm = result.scalar_one_or_none()
                if orm:
                    meta = dict(orm.metadata_ or {})
                    meta["gtm_strategy"] = state.gtm_strategy
                    orm.metadata_ = meta
                    orm.updated_at = datetime.now(timezone.utc)
                    await session.commit()

        primary_channel = state.gtm_strategy.get("channel_strategy", {}).get("primary_channel", "?") if state.gtm_strategy else "?"
        await _log_step(job_id, "gtm_strategy", "done", f"Primary channel: {primary_channel}")
        logger.info("STEP 2/6  GTM done", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "gtm_strategy", "status": "done"})

        # ── Step 3: CMI Agent — Content Brief ────────────────────────────
        await _check_paused(job_id)
        await _log_step(job_id, "cmi_brief", "running", "CMI generating content brief...")
        logger.info("STEP 3/6  CMI agent generating content brief...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "cmi_brief", "status": "running"})

        from src.agents.cmi import CMIAgent
        cmi = CMIAgent()
        state = await cmi.run(state)

        if state.error:
            await _save_job_field(job_id, status="failed", error_message=state.error, current_step=None)
            await _log_step(job_id, "cmi_brief", "failed", state.error)
            logger.error("PIPELINE FAILED at CMI", job_id=job_id, error=state.error)
            await _broadcast_event("step_update", job_id, {"step": "cmi_brief", "status": "failed", "error": state.error})
            return

        content_brief_data = None
        if state.content_brief:
            content_brief_data = {
                "job_id": job_id,
                "topic": state.content_brief.topic,
                "marketing_angle": state.content_brief.marketing_angle,
                "target_audience": state.content_brief.target_audience,
                "tone": state.content_brief.tone,
                "key_messages": state.content_brief.key_messages,
                "platform_strategy": state.content_brief.platform_strategy,
                "created_by": "agent:cmi",
            }
            await _save_job_field(job_id, content_brief=content_brief_data)

        await _log_step(job_id, "cmi_brief", "done", f"Angle: {state.content_brief.marketing_angle if state.content_brief else '?'}")
        logger.info("STEP 3/6  CMI done", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "cmi_brief", "status": "done"})

        # ── Step 4: Decision Maker ───────────────────────────────────────
        await _check_paused(job_id)
        await _log_step(job_id, "decision_maker", "running", "Deciding pipeline type...")
        logger.info("STEP 4/6  Decision Maker routing...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "decision_maker", "status": "running"})

        from src.agents.decision_maker import DecisionMakerAgent
        dm = DecisionMakerAgent()
        state = await dm.run(state)

        pipeline = state.pipeline_type
        await _save_job_field(job_id, pipeline_type=pipeline)

        await _log_step(job_id, "decision_maker", "done", f"Pipeline: {pipeline}")
        logger.info("STEP 4/6  Decision Maker done", job_id=job_id, pipeline=pipeline)
        await _broadcast_event("step_update", job_id, {"step": "decision_maker", "status": "done", "pipeline": pipeline})

        # ── Step 5: Script Generation (CST or VST) ──────────────────────
        await _check_paused(job_id)
        step_name = "cst_script" if pipeline == "image_post" else "vst_script"
        await _log_step(job_id, step_name, "running", f"{'CST' if pipeline == 'image_post' else 'VST'} generating script...")
        logger.info(f"STEP 5/6  {'CST' if pipeline == 'image_post' else 'VST'} generating script...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": step_name, "status": "running"})

        if pipeline == "image_post":
            from src.agents.cst import CSTAgent
            cst = CSTAgent()
            state = await cst.run(state)
        elif pipeline == "video_post":
            from src.agents.vst import VSTAgent
            vst = VSTAgent()
            state = await vst.run(state)

        if state.error:
            await _save_job_field(job_id, status="failed", error_message=state.error, current_step=None)
            await _log_step(job_id, step_name, "failed", state.error)
            logger.error("PIPELINE FAILED at script gen", job_id=job_id, error=state.error)
            await _broadcast_event("step_update", job_id, {"step": step_name, "status": "failed"})
            return

        script_data = None
        if state.script:
            script_data = {
                "job_id": job_id,
                "type": state.script.type,
                "content": state.script.content,
                "image_prompts": state.script.image_prompts,
                "video_frames": [
                    {
                        "frame_number": f.frame_number,
                        "scene_description": f.scene_description,
                        "duration_seconds": f.duration_seconds,
                        "transition_type": f.transition_type,
                        "audio_cue": f.audio_cue,
                    }
                    for f in (state.script.video_frames or [])
                ],
                "audio_narration": state.script.audio_narration,
                "created_by": state.script.created_by,
                "version": state.script.version,
            }
            await _save_job_field(job_id, script_data=script_data)

        await _log_step(job_id, step_name, "done", "Script generated")
        logger.info("STEP 5/6  Script done", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": step_name, "status": "done"})

        # ── Step 6: CSA — Script Approval ────────────────────────────────
        await _check_paused(job_id)
        await _log_step(job_id, "csa_approval", "running", "CSA reviewing script quality...")
        logger.info("STEP 6/6  CSA approving script...", job_id=job_id)
        await _broadcast_event("step_update", job_id, {"step": "csa_approval", "status": "running"})

        from src.agents.csa import CSAAgent
        csa = CSAAgent()
        state = await csa.run(state)

        if state.approval_decision:
            decision = state.approval_decision.get("decision", "unknown")
            score = state.approval_decision.get("overall_score", "?")

            await _log_step(job_id, "csa_approval", "done", f"Decision: {decision} (score: {score})")
            logger.info("STEP 6/6  CSA verdict", job_id=job_id, decision=decision, score=score)
            await _broadcast_event("step_update", job_id, {"step": "csa_approval", "status": "done", "decision": decision, "score": score})

            if decision == "rejected":
                await _save_job_field(
                    job_id, status="rejected",
                    improvement_count=state.improvement_count,
                    current_step=None,
                )
                logger.info("PIPELINE  Script rejected by CSA", job_id=job_id)
                await _broadcast_event("pipeline_complete", job_id, {"status": "rejected"})
                return

        # ── Step 7: Media Generation ─────────────────────────────────────
        await _check_paused(job_id)
        if pipeline == "image_post":
            await _log_step(job_id, "image_generation", "running", "Generating images from script prompts...")
            logger.info("STEP 6  ImageGeneratorAgent running...", job_id=job_id)
            await _broadcast_event("step_update", job_id, {"step": "image_generation", "status": "running"})

            from src.media.image_generator import ImageGeneratorAgent
            image_agent = ImageGeneratorAgent()
            state = await image_agent.run(state)
            await _save_media_assets(job_id, list(state.job.media_assets or []))

            await _log_step(job_id, "image_generation", "done", f"Assets: {len(state.job.media_assets or [])}")
            logger.info("STEP 6  Image generation done", job_id=job_id, asset_count=len(state.job.media_assets or []))
            await _broadcast_event("step_update", job_id, {"step": "image_generation", "status": "done"})

        elif pipeline == "video_post":
            await _log_step(job_id, "video_generation", "running", "Generating video clips from script frames...")
            logger.info("STEP 6  VideoGeneratorOrchestrator running...", job_id=job_id)
            await _broadcast_event("step_update", job_id, {"step": "video_generation", "status": "running"})

            from src.media.video_generator import VideoGeneratorOrchestrator
            video_agent = VideoGeneratorOrchestrator()
            state = await video_agent.run(state)
            await _save_media_assets(job_id, list(state.job.media_assets or []))

            await _log_step(job_id, "video_generation", "done", f"Assets: {len(state.job.media_assets or [])}")
            logger.info("STEP 6  Video generation done", job_id=job_id, asset_count=len(state.job.media_assets or []))
            await _broadcast_event("step_update", job_id, {"step": "video_generation", "status": "done"})

        # ── Done — awaiting human approval ───────────────────────────────
        await _save_job_field(job_id, status="awaiting_approval", current_step=None)
        logger.info("PIPELINE COMPLETE — awaiting human approval", job_id=job_id, pipeline=pipeline)
        await _broadcast_event("pipeline_complete", job_id, {"status": "awaiting_approval", "pipeline": pipeline})

    except asyncio.CancelledError:
        await _save_job_field(job_id, status="paused")
        logger.info("PIPELINE PAUSED/CANCELLED", job_id=job_id)
        await _broadcast_event("pipeline_paused", job_id, {})

    except Exception as e:
        await _save_job_field(job_id, status="failed", error_message=str(e), current_step=None)
        logger.exception("PIPELINE ERROR", job_id=job_id, error=str(e))
        await _broadcast_event("pipeline_error", job_id, {"error": str(e)})

    finally:
        _running_tasks.pop(job_id, None)
        _paused_jobs.discard(job_id)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/jobs/trigger", response_model=TriggerJobResponse, status_code=202)
async def trigger_content_job(
    request: TriggerJobRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TriggerJobResponse:
    """Trigger a new content generation job — persists to PostgreSQL."""
    job_id = uuid.uuid4()
    orm = ContentJobORM(
        id=job_id,
        name=request.name or None,
        description=request.description or None,
        topic=request.topic,
        topic_source=request.topic_source,
        status="pending",
        pipeline_logs=[],
        metadata_={"requested_platforms": request.platforms},
    )
    db.add(orm)
    await db.commit()  # Commit immediately so background task can see the row

    logger.info("Job created in DB, launching pipeline", job_id=str(job_id), topic=request.topic)
    background_tasks.add_task(run_pipeline, str(job_id))

    return TriggerJobResponse(job_id=str(job_id), status="pending")


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the full content job by ID from database."""
    result = await db.execute(
        select(ContentJobORM)
        .where(ContentJobORM.id == uuid.UUID(job_id))
        .options(selectinload(ContentJobORM.media_assets))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")
    return _orm_to_dict(orm)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List content jobs from database."""
    query = select(ContentJobORM).order_by(ContentJobORM.created_at.desc()).options(selectinload(ContentJobORM.media_assets))
    count_query = select(func.count()).select_from(ContentJobORM)

    if status:
        query = query.where(ContentJobORM.status == status)
        count_query = count_query.where(ContentJobORM.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    orms = result.scalars().all()

    return JobListResponse(
        jobs=[_orm_to_dict(o) for o in orms],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pause a running job."""
    result = await db.execute(
        select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")
    if orm.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Cannot pause job in status: {orm.status}")

    _paused_jobs.add(job_id)
    orm.status = "paused"
    orm.updated_at = datetime.now(timezone.utc)
    logs = list(orm.pipeline_logs or [])
    logs.append({"step": orm.current_step or "unknown", "status": "paused", "detail": "Paused by user", "timestamp": _now()})
    orm.pipeline_logs = logs
    await db.flush()

    logger.info("Job paused", job_id=job_id)
    await _broadcast_event("job_paused", job_id, {})
    return {"job_id": job_id, "status": "paused"}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resume a paused job."""
    result = await db.execute(
        select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")
    if orm.status != "paused" and job_id not in _paused_jobs:
        raise HTTPException(status_code=400, detail=f"Job is not paused (status: {orm.status})")

    _paused_jobs.discard(job_id)
    orm.status = "in_progress"
    orm.updated_at = datetime.now(timezone.utc)
    logs = list(orm.pipeline_logs or [])
    logs.append({"step": orm.current_step or "unknown", "status": "resumed", "detail": "Resumed by user", "timestamp": _now()})
    orm.pipeline_logs = logs
    await db.flush()

    logger.info("Job resumed", job_id=job_id)
    await _broadcast_event("job_resumed", job_id, {})

    if job_id not in _running_tasks:
        background_tasks.add_task(run_pipeline, job_id)

    return {"job_id": job_id, "status": "in_progress"}


@router.post("/jobs/{job_id}/approve", response_model=ApprovalResponse)
async def submit_human_approval(
    job_id: str,
    request: ApprovalRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Submit a human approval/rejection decision."""
    if request.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    result = await db.execute(
        select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")

    new_status = "publishing" if request.decision == "approved" else "rejected"
    orm.status = new_status
    orm.updated_at = datetime.now(timezone.utc)
    logs = list(orm.pipeline_logs or [])
    logs.append({"step": "human_review", "status": "done", "detail": f"Human decision: {request.decision}", "timestamp": _now()})
    orm.pipeline_logs = logs
    await db.flush()

    logger.info("Human approval", job_id=job_id, decision=request.decision)
    await _broadcast_event("job_update", job_id, {"status": new_status, "decision": request.decision})
    return ApprovalResponse(job_id=job_id, decision=request.decision, status=new_status)


@router.post("/jobs/{job_id}/reinitiate")
async def reinitiate_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset a job and re-run its pipeline from scratch."""
    result = await db.execute(
        select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cannot reinitiate a job that is actively running
    if job_id in _running_tasks:
        raise HTTPException(status_code=400, detail="Job is currently running. Pause it first.")

    # Snapshot the current run into run_history before resetting
    current_count = orm.reinitiation_count or 0
    current_run_snapshot = {
        'run_number': current_count + 1,
        'reinitiated_at': _now(),
        'reinitiated_by': f"{user['name']} ({user['email']})",
        'status_at_end': orm.status,
        'pipeline_type': orm.pipeline_type,
        'pipeline_logs': list(orm.pipeline_logs or []),
    }
    existing_history = list(orm.run_history or [])
    existing_history.append(current_run_snapshot)
    orm.run_history = existing_history
    orm.reinitiation_count = current_count + 1

    # Reset all state back to pending
    _paused_jobs.discard(job_id)
    orm.status = "pending"
    orm.current_step = None
    orm.error_message = None
    orm.improvement_count = 0
    orm.pipeline_type = None
    orm.content_brief = None
    orm.script_data = None
    orm.pipeline_logs = [
        {
            "step": "reinitiated",
            "status": "done",
            "detail": f"Job reinitiated by {user['name']} ({user['email']})",
            "timestamp": _now(),
        }
    ]
    orm.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Job reinitiated", job_id=job_id, reinitiated_by=user["id"])
    await _broadcast_event("job_reinitiated", job_id, {"status": "pending"})

    # Re-launch the pipeline in the background
    background_tasks.add_task(run_pipeline, job_id)

    return {"job_id": job_id, "status": "pending"}


@router.delete("/jobs/{job_id}", status_code=204, response_model=None)
async def delete_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a content job. Running jobs are cancelled first."""
    result = await db.execute(
        select(ContentJobORM).where(ContentJobORM.id == uuid.UUID(job_id))
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cancel if running
    if job_id in _running_tasks:
        _paused_jobs.add(job_id)
        _running_tasks.pop(job_id, None)
    _paused_jobs.discard(job_id)

    await db.delete(orm)
    await db.commit()
    logger.info("Job deleted", job_id=job_id, deleted_by=user["id"])
    await _broadcast_event("job_deleted", job_id, {})
