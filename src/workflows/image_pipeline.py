"""LangGraph workflow for the Image Post pipeline."""
from __future__ import annotations

from typing import Literal

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.base import AgentState
from src.agents.csa import CSAAgent
from src.agents.cst import CSTAgent
from src.config import get_settings
from src.media.image_generator import ImageGeneratorAgent
from src.approval.image_approver import ImageApproverAgent

logger = structlog.get_logger(__name__)


def should_retry_script(state: AgentState) -> Literal["cst", "image_generation", "__end__"]:
    """After CSA review, route to improvement or proceed."""
    if state.approval_decision and state.approval_decision.get("decision") == "approved":
        return "image_generation"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        logger.warning(
            "Max script improvements reached",
            job_id=str(state.job.id),
            count=state.improvement_count,
        )
        return "__end__"

    return "cst"


def should_retry_image(state: AgentState) -> Literal["cst", "__end__", "publish"]:
    """After image approval, route to publish or improvement."""
    if state.approval_decision and state.approval_decision.get("image_decision") == "approved":
        return "publish"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        return "__end__"

    return "cst"


def build_image_pipeline() -> StateGraph:
    """Build the LangGraph state machine for the image post pipeline."""
    cst = CSTAgent()
    csa = CSAAgent()
    image_gen = ImageGeneratorAgent()
    image_approver = ImageApproverAgent()

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("cst", cst.run)
    graph.add_node("csa", csa.run)
    graph.add_node("image_generation", image_gen.run)
    graph.add_node("image_approval", image_approver.run)

    # Edges: start → CST → CSA → (approved: image gen | rejected: CST again)
    graph.add_edge(START, "cst")
    graph.add_edge("cst", "csa")
    graph.add_conditional_edges(
        "csa",
        should_retry_script,
        {
            "cst": "cst",
            "image_generation": "image_generation",
            "__end__": END,
        },
    )
    graph.add_edge("image_generation", "image_approval")
    graph.add_conditional_edges(
        "image_approval",
        should_retry_image,
        {
            "cst": "cst",
            "publish": END,  # Publishing handled by caller
            "__end__": END,
        },
    )

    return graph


class ImagePipelineGraph:
    """Compiled image pipeline for execution."""

    def __init__(self) -> None:
        self._graph = build_image_pipeline().compile()

    async def run(self, state: AgentState) -> AgentState:
        """Execute the full image post pipeline."""
        logger.info("Starting image post pipeline", job_id=str(state.job.id))
        result = await self._graph.ainvoke(state)
        return result
