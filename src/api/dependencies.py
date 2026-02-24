"""FastAPI dependency injection providers."""
from __future__ import annotations

from functools import lru_cache

from src.workflows.mama_workflow import MAMAWorkflow


@lru_cache(maxsize=1)
def get_workflow() -> MAMAWorkflow:
    """Singleton MAMA workflow instance."""
    return MAMAWorkflow()
