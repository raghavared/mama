"""LangGraph workflow for the Video Post pipeline."""
from __future__ import annotations

from typing import Literal

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.base import AgentState
from src.agents.csa import CSAAgent
from src.agents.vst import VSTAgent
from src.config import get_settings
from src.media.script_separator import ScriptSeparatorModule
from src.media.video_generator import VideoGeneratorOrchestrator
from src.media.audio_generator import AudioGeneratorAgent
from src.media.av_merger import AVMergerAgent
from src.approval.video_approver import VideoApproverAgent
from src.approval.audio_approver import AudioApproverAgent
from src.approval.vam import VAMAgent

logger = structlog.get_logger(__name__)


def should_retry_video_script(state: AgentState) -> Literal["vst", "script_separator", "__end__"]:
    """After CSA review of video script, route appropriately."""
    if state.approval_decision and state.approval_decision.get("decision") == "approved":
        return "script_separator"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        return "__end__"
    return "vst"


def should_retry_video(state: AgentState) -> Literal["video_generation", "av_merge", "__end__"]:
    """After video approval, route to merge or retry."""
    if state.approval_decision and state.approval_decision.get("video_decision") == "approved":
        return "av_merge"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        return "__end__"
    return "video_generation"


def should_retry_audio(state: AgentState) -> Literal["audio_generation", "av_merge", "__end__"]:
    """After audio approval, route to merge or retry."""
    if state.approval_decision and state.approval_decision.get("audio_decision") == "approved":
        return "av_merge"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        return "__end__"
    return "audio_generation"


def should_finalize(state: AgentState) -> Literal["vst", "human_review", "__end__"]:
    """After VAM review, route to human review or retry."""
    if state.approval_decision and state.approval_decision.get("vam_decision") == "approved":
        return "human_review"

    settings = get_settings()
    if state.improvement_count >= settings.max_improvement_cycles:
        return "__end__"
    return "vst"


def build_video_pipeline() -> StateGraph:
    """Build the LangGraph state machine for the video post pipeline."""
    vst = VSTAgent()
    csa = CSAAgent()
    script_separator = ScriptSeparatorModule()
    video_gen = VideoGeneratorOrchestrator()
    audio_gen = AudioGeneratorAgent()
    video_approver = VideoApproverAgent()
    audio_approver = AudioApproverAgent()
    av_merger = AVMergerAgent()
    vam = VAMAgent()

    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("vst", vst.run)
    graph.add_node("csa", csa.run)
    graph.add_node("script_separator", script_separator.run)
    graph.add_node("video_generation", video_gen.run)
    graph.add_node("audio_generation", audio_gen.run)
    graph.add_node("video_approval", video_approver.run)
    graph.add_node("audio_approval", audio_approver.run)
    graph.add_node("av_merge", av_merger.run)
    graph.add_node("vam", vam.run)

    # Edges
    graph.add_edge(START, "vst")
    graph.add_edge("vst", "csa")
    graph.add_conditional_edges(
        "csa",
        should_retry_video_script,
        {"vst": "vst", "script_separator": "script_separator", "__end__": END},
    )
    graph.add_edge("script_separator", "video_generation")
    graph.add_edge("script_separator", "audio_generation")  # Parallel branch
    graph.add_edge("video_generation", "video_approval")
    graph.add_edge("audio_generation", "audio_approval")
    graph.add_conditional_edges(
        "video_approval",
        should_retry_video,
        {"video_generation": "video_generation", "av_merge": "av_merge", "__end__": END},
    )
    graph.add_conditional_edges(
        "audio_approval",
        should_retry_audio,
        {"audio_generation": "audio_generation", "av_merge": "av_merge", "__end__": END},
    )
    graph.add_edge("av_merge", "vam")
    graph.add_conditional_edges(
        "vam",
        should_finalize,
        {"vst": "vst", "human_review": END, "__end__": END},  # human_review triggers external HITL
    )

    return graph


class VideoPipelineGraph:
    """Compiled video pipeline for execution."""

    def __init__(self) -> None:
        self._graph = build_video_pipeline().compile()

    async def run(self, state: AgentState) -> AgentState:
        """Execute the full video post pipeline."""
        logger.info("Starting video post pipeline", job_id=str(state.job.id))
        result = await self._graph.ainvoke(state)
        return result
