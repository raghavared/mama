"""Add reinitiation_count and run_history to content_jobs.

Revision ID: 003
Revises: 002
Create Date: 2026-02-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects.postgresql import JSONB
    op.add_column("content_jobs", sa.Column("reinitiation_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("content_jobs", sa.Column("run_history", JSONB, nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("content_jobs", "run_history")
    op.drop_column("content_jobs", "reinitiation_count")
