"""Master MAMA Workflow — orchestrates the full content pipeline."""
from __future__ import annotations

import uuid
from typing import Literal

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.base import AgentState
from src.agents.mama import MAMAAgent
from src.agents.cmi import CMIAgent
from src.agents.decision_maker import DecisionMakerAgent
from src.models import ContentJob, TopicSource, PipelineType
from src.workflows.image_pipeline import ImagePipelineGraph
from src.workflows.video_pipeline import VideoPipelineGraph

logger = structlog.get_logger(__name__)


def route_pipeline(state: AgentState) -> Literal["image_pipeline", "video_pipeline", "__end__"]:
    """Route to image or video pipeline based on Decision Maker output."""
    if state.error:
        return "__end__"
    if state.pipeline_type == PipelineType.IMAGE_POST.value:
        return "image_pipeline"
    if state.pipeline_type == PipelineType.VIDEO_POST.value:
        return "video_pipeline"
    return "__end__"


class ImagePipelineNode:
    """Wraps ImagePipelineGraph as a LangGraph node."""

    def __init__(self) -> None:
        self._pipeline = ImagePipelineGraph()

    async def run(self, state: AgentState) -> AgentState:
        return await self._pipeline.run(state)


class VideoPipelineNode:
    """Wraps VideoPipelineGraph as a LangGraph node."""

    def __init__(self) -> None:
        self._pipeline = VideoPipelineGraph()

    async def run(self, state: AgentState) -> AgentState:
        return await self._pipeline.run(state)


class MAMAWorkflow:
    """
    The top-level MAMA workflow.

    Flow: MAMA → CMI → Decision Maker → (Image Pipeline | Video Pipeline)
    """

    def __init__(self) -> None:
        mama = MAMAAgent()
        cmi = CMIAgent()
        decision_maker = DecisionMakerAgent()
        image_pipeline_node = ImagePipelineNode()
        video_pipeline_node = VideoPipelineNode()

        graph = StateGraph(AgentState)

        graph.add_node("mama", mama.run)
        graph.add_node("cmi", cmi.run)
        graph.add_node("decision_maker", decision_maker.run)
        graph.add_node("image_pipeline", image_pipeline_node.run)
        graph.add_node("video_pipeline", video_pipeline_node.run)

        graph.add_edge(START, "mama")
        graph.add_edge("mama", "cmi")
        graph.add_edge("cmi", "decision_maker")
        graph.add_conditional_edges(
            "decision_maker",
            route_pipeline,
            {
                "image_pipeline": "image_pipeline",
                "video_pipeline": "video_pipeline",
                "__end__": END,
            },
        )
        graph.add_edge("image_pipeline", END)
        graph.add_edge("video_pipeline", END)

        self._graph = graph.compile()
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def trigger(
        self,
        topic: str,
        topic_source: TopicSource = TopicSource.MANUAL,
        metadata: dict | None = None,
    ) -> AgentState:
        """
        Trigger the full MAMA content generation pipeline for a topic.

        Args:
            topic: The marketing topic to generate content for
            topic_source: How the topic was sourced (manual, trending, scheduled)
            metadata: Optional extra metadata to attach to the job

        Returns:
            Final AgentState after pipeline completion
        """
        job = ContentJob(
            id=uuid.uuid4(),
            topic=topic,
            topic_source=topic_source,
            metadata=metadata or {},
        )

        initial_state = AgentState(job=job)

        self.logger.info(
            "MAMA workflow triggered",
            job_id=str(job.id),
            topic=topic,
            source=topic_source.value,
        )

        result = await self._graph.ainvoke(initial_state)

        self.logger.info(
            "MAMA workflow completed",
            job_id=str(job.id),
            final_status=result.job.status.value,
            pipeline_type=result.pipeline_type,
        )

        return result
