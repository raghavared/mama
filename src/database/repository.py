"""ContentJob repository — async CRUD operations."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ContentJob, ContentJobStatus
from .models import ContentJobORM, ScriptORM, MediaAssetORM, ApprovalRecordORM, PublishedPostORM

logger = structlog.get_logger(__name__)


class ContentJobRepository:
    """Async repository for ContentJob persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def create_job(self, job: ContentJob) -> ContentJobORM:
        """Persist a new ContentJob to the database."""
        orm = ContentJobORM(
            id=job.id,
            topic=job.topic,
            topic_source=job.topic_source.value,
            pipeline_type=job.pipeline_type.value if job.pipeline_type else None,
            status=job.status.value,
            improvement_count=job.improvement_count,
            error_message=job.error_message,
            metadata_=job.metadata,
        )
        self.session.add(orm)
        await self.session.flush()
        self.logger.info("Job created", job_id=str(job.id))
        return orm

    async def get_job(self, job_id: uuid.UUID) -> Optional[ContentJob]:
        """Retrieve a ContentJob by ID."""
        result = await self.session.execute(
            select(ContentJobORM).where(ContentJobORM.id == job_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._orm_to_domain(orm)

    async def update_job(self, job: ContentJob) -> None:
        """Update an existing ContentJob in the database."""
        result = await self.session.execute(
            select(ContentJobORM).where(ContentJobORM.id == job.id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            await self.create_job(job)
            return

        orm.status = job.status.value
        orm.pipeline_type = job.pipeline_type.value if job.pipeline_type else None
        orm.error_message = job.error_message
        orm.improvement_count = job.improvement_count
        orm.metadata_ = job.metadata
        await self.session.flush()
        self.logger.info("Job updated", job_id=str(job.id), status=job.status.value)

    async def list_jobs(
        self,
        status: Optional[ContentJobStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContentJob]:
        """List jobs with optional status filter."""
        query = select(ContentJobORM).order_by(ContentJobORM.created_at.desc()).limit(limit).offset(offset)
        if status:
            query = query.where(ContentJobORM.status == status.value)
        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._orm_to_domain(orm) for orm in orms]

    def _orm_to_domain(self, orm: ContentJobORM) -> ContentJob:
        """Convert ORM model to domain Pydantic model."""
        from src.models import TopicSource, PipelineType
        return ContentJob(
            id=orm.id,
            topic=orm.topic,
            topic_source=TopicSource(orm.topic_source),
            pipeline_type=PipelineType(orm.pipeline_type) if orm.pipeline_type else None,
            status=ContentJobStatus(orm.status),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            error_message=orm.error_message,
            improvement_count=orm.improvement_count,
            metadata=orm.metadata_ or {},
        )
