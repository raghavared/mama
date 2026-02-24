"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-02-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # content_jobs
    op.create_table(
        "content_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("topic_source", sa.String(50), nullable=False),
        sa.Column("pipeline_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("improvement_count", sa.Integer, server_default="0"),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_index("ix_content_jobs_status", "content_jobs", ["status"])
    op.create_index("ix_content_jobs_created_at", "content_jobs", ["created_at"])

    # scripts
    op.create_table(
        "scripts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("content_jobs.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("image_prompts", JSONB, server_default="[]"),
        sa.Column("video_frames", JSONB, server_default="[]"),
        sa.Column("audio_narration", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_index("ix_scripts_job_id", "scripts", ["job_id"])

    # media_assets
    op.create_table(
        "media_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("content_jobs.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_index("ix_media_assets_job_id", "media_assets", ["job_id"])

    # approval_records
    op.create_table(
        "approval_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("content_jobs.id"), nullable=False),
        sa.Column("gate", sa.String(50), nullable=False),
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("reviewer", sa.String(200), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_records_job_id", "approval_records", ["job_id"])

    # published_posts
    op.create_table(
        "published_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("content_jobs.id"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("platform_post_id", sa.String(200), nullable=False),
        sa.Column("post_url", sa.String(500), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("analytics", JSONB, server_default="{}"),
    )
    op.create_index("ix_published_posts_job_id", "published_posts", ["job_id"])


def downgrade() -> None:
    op.drop_table("published_posts")
    op.drop_table("approval_records")
    op.drop_table("media_assets")
    op.drop_table("scripts")
    op.drop_table("content_jobs")
