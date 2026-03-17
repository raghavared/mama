"""Add social_oauth_tokens table for OAuth token storage.

Revision ID: 004
Revises: 003
Create Date: 2026-02-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.dialects.postgresql import UUID

    op.create_table(
        "oauth_tokens",
        sa.Column("id", UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("platform", sa.String(50), nullable=False, unique=True),
        sa.Column("encrypted_token", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_oauth_tokens_platform", "oauth_tokens", ["platform"])


def downgrade() -> None:
    op.drop_index("ix_oauth_tokens_platform", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
