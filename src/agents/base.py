"""Base agent class and shared workflow state for all MAMA agents."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import structlog
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models import ContentJob, ContentBrief, Script, ApprovalRecord
from src.utils.llm_client import MultiLLMClient, LLMResponse

logger = structlog.get_logger(__name__)


class AgentState(BaseModel):
    """Shared state that flows through the LangGraph workflow."""

    # Core job data
    job: ContentJob
    messages: list[dict[str, Any]] = Field(default_factory=list)

    # Stage outputs
    enriched_topic: Optional[dict[str, Any]] = None
    gtm_strategy: Optional[dict[str, Any]] = None
    content_brief: Optional[ContentBrief] = None
    script: Optional[Script] = None
    approval_decision: Optional[dict[str, Any]] = None

    # Routing
    pipeline_type: Optional[str] = None  # "image_post" | "video_post"
    next_action: Optional[str] = None

    # Loop control
    improvement_feedback: Optional[str] = None
    improvement_count: int = 0
    max_improvements: int = 5

    # Error tracking
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class BaseAgent(ABC):
    """
    Base class for all MAMA coordinator agents.

    Each agent:
    - Has a unique agent_id (e.g. "agent:cmi")
    - Calls Claude via the Anthropic SDK
    - Exposes a .run(state) -> state interface for LangGraph node wrapping
    """

    agent_id: str = "agent:base"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._llm_client: Optional[MultiLLMClient] = None
        self._last_llm_response: Optional[LLMResponse] = None
        self.logger = structlog.get_logger(self.__class__.__name__)

    @property
    def llm_client(self) -> MultiLLMClient:
        if self._llm_client is None:
            self._llm_client = MultiLLMClient(self.settings)
        return self._llm_client

    @property
    def llm_response(self) -> Optional[LLMResponse]:
        """The full LLMResponse from the most recent call_llm() invocation."""
        return self._last_llm_response

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Execute the agent's task and return updated state."""
        ...

    async def call_llm(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        """Call LLM with automatic fallback and return the text response."""
        self.logger.info("Calling LLM", agent_id=self.agent_id)
        response = await self.llm_client.call(system_prompt, user_message, max_tokens)
        self._last_llm_response = response
        self.logger.info(
            "LLM call complete",
            agent_id=self.agent_id,
            provider=response.provider_used,
            model=response.model_used,
            latency_ms=round(response.latency_ms),
        )
        return response.text

    def log_state_transition(self, from_status: str, to_status: str, job_id: uuid.UUID) -> None:
        self.logger.info(
            "State transition",
            agent_id=self.agent_id,
            job_id=str(job_id),
            from_status=from_status,
            to_status=to_status,
        )
