"""Shared pytest fixtures."""
from __future__ import annotations

import os
import pytest

# Set test environment variables before any imports
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://mama:mama_password@localhost:5432/mama_db_test")
os.environ.setdefault("USE_LOCAL_STORAGE", "true")
os.environ.setdefault("LOCAL_STORAGE_PATH", "/tmp/mama_test_assets")
