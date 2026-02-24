"""Add name and description columns to content_jobs.

Revision ID: 002
Revises: 001
Create Date: 2026-02-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_jobs", sa.Column("name", sa.String(200), nullable=True))
    op.add_column("content_jobs", sa.Column("description", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("content_jobs", "description")
    op.drop_column("content_jobs", "name")
