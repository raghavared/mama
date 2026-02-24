"""Unit tests for agent implementations."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentState
from src.agents.mama import MAMAAgent
from src.agents.cmi import CMIAgent
from src.agents.decision_maker import DecisionMakerAgent
from src.agents.cst import CSTAgent
from src.agents.csa import CSAAgent
from src.models import ContentJob, ContentBrief, Script, TopicSource, ContentJobStatus, PipelineType


def make_job(topic: str = "Test topic") -> ContentJob:
    return ContentJob(topic=topic, topic_source=TopicSource.MANUAL)


def make_state(topic: str = "Test topic") -> AgentState:
    return AgentState(job=make_job(topic))


@pytest.fixture
def mama_response():
    return json.dumps({
        "suitable": True,
        "unsuitable_reason": None,
        "enriched_topic": "AI in Modern Marketing",
        "enriched_context": "AI is transforming marketing automation.",
        "target_audience": {
            "primary": "B2B SaaS founders aged 30-45",
            "secondary": None,
            "pain_points": ["manual campaigns", "low ROI"],
            "desires": ["automation", "growth"],
        },
        "recommended_tone": "authoritative",
        "timing_relevance": "trending_now",
        "suggested_platforms": ["instagram", "linkedin"],
        "marketing_angle": "AI-driven marketing automation",
        "estimated_engagement_potential": "high",
    })


@pytest.fixture
def cmi_response():
    return json.dumps({
        "marketing_angle": "How AI saves 10 hours per week on marketing",
        "target_audience": "B2B SaaS founders",
        "tone": "authoritative",
        "key_messages": ["Save time", "Increase ROI", "Easy to start"],
        "platform_strategy": {
            "instagram": "Visual hooks",
            "linkedin": "Data-driven",
            "facebook": "Story format",
            "x_twitter": "Short punchy",
            "youtube": "Tutorial format",
        },
        "psychological_hooks": ["FOMO", "Authority"],
        "content_angle_rationale": "Time-saving resonates with busy founders",
        "hashtag_suggestions": ["#AIMarketing", "#MarketingAutomation"],
        "call_to_action": "Start your free trial today",
    })


@pytest.fixture
def decision_maker_response():
    return json.dumps({
        "pipeline_type": "image_post",
        "confidence": "high",
        "rationale": "Statistical content is better suited for images",
    })


@pytest.fixture
def cst_response():
    return json.dumps({
        "hook": "Did you know AI can 10x your marketing ROI?",
        "narrative": "Marketing teams waste hours on manual tasks...",
        "call_to_action": "Start free trial at mama.io",
        "full_caption": "Did you know AI can 10x your marketing ROI?\n\nMarketing teams waste hours...",
        "image_prompts": ["Futuristic AI robot in marketing office, professional"],
        "image_style_notes": "Clean, modern, blues and whites",
        "hashtags": ["#AIMarketing"],
        "platform_variants": {
            "instagram": "Short version for Instagram",
            "linkedin": "Long professional version",
            "facebook": "Medium engaging version",
        },
    })


@pytest.fixture
def csa_approved_response():
    return json.dumps({
        "decision": "approved",
        "overall_score": 8,
        "criteria_scores": {
            "brand_alignment": 8,
            "audience_fit": 8,
            "hook_strength": 9,
            "message_clarity": 8,
            "call_to_action": 7,
            "platform_suitability": 8,
        },
        "strengths": ["Strong hook", "Clear CTA"],
        "rejection_reasons": None,
        "improvement_feedback": None,
        "approval_notes": "Good quality script, ready for image generation",
    })


@pytest.mark.asyncio
async def test_mama_agent_enriches_topic(mama_response):
    state = make_state("AI in marketing")
    agent = MAMAAgent()

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=mama_response)):
        result = await agent.run(state)

    assert result.enriched_topic is not None
    assert result.enriched_topic["suitable"] is True
    assert result.job.status == ContentJobStatus.IN_PROGRESS
    assert len(result.messages) == 1


@pytest.mark.asyncio
async def test_mama_agent_rejects_unsuitable_topic():
    state = make_state("Controversial political topic")
    agent = MAMAAgent()

    unsuitable_response = json.dumps({
        "suitable": False,
        "unsuitable_reason": "Topic is too controversial for brand content",
        "enriched_topic": "",
        "enriched_context": "",
        "target_audience": {},
        "recommended_tone": "educational",
        "timing_relevance": "evergreen",
        "suggested_platforms": [],
        "marketing_angle": "",
        "estimated_engagement_potential": "low",
    })

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=unsuitable_response)):
        result = await agent.run(state)

    assert result.error is not None
    assert "unsuitable" in result.error.lower()
    assert result.job.status == ContentJobStatus.FAILED


@pytest.mark.asyncio
async def test_cmi_agent_creates_brief(mama_response, cmi_response):
    state = make_state("AI marketing")
    state.enriched_topic = json.loads(mama_response)
    agent = CMIAgent()

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=cmi_response)):
        result = await agent.run(state)

    assert result.content_brief is not None
    assert result.content_brief.marketing_angle == "How AI saves 10 hours per week on marketing"
    assert len(result.content_brief.key_messages) == 3


@pytest.mark.asyncio
async def test_decision_maker_routes_to_image_pipeline(cmi_response, decision_maker_response):
    state = make_state("AI marketing")
    state.content_brief = ContentBrief(
        job_id=state.job.id,
        topic="AI marketing",
        marketing_angle="AI saves time",
        target_audience="founders",
        tone="authoritative",
        key_messages=["Save time"],
        platform_strategy={},
    )
    state.enriched_topic = {}
    agent = DecisionMakerAgent()

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=decision_maker_response)):
        result = await agent.run(state)

    assert result.pipeline_type == "image_post"
    assert result.job.pipeline_type == PipelineType.IMAGE_POST


@pytest.mark.asyncio
async def test_cst_agent_generates_script(cst_response):
    state = make_state("AI marketing")
    state.content_brief = ContentBrief(
        job_id=state.job.id,
        topic="AI marketing",
        marketing_angle="AI saves time",
        target_audience="founders",
        tone="authoritative",
        key_messages=["Save time", "10x ROI"],
        platform_strategy={"instagram": "Visual", "linkedin": "Data"},
    )
    agent = CSTAgent()

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=cst_response)):
        result = await agent.run(state)

    assert result.script is not None
    assert result.script.type == "image_script"
    assert result.script.version == 1
    assert len(result.script.image_prompts) == 1
    assert result.job.status == ContentJobStatus.AWAITING_APPROVAL


@pytest.mark.asyncio
async def test_csa_agent_approves_script(csa_approved_response):
    state = make_state("AI marketing")
    state.content_brief = ContentBrief(
        job_id=state.job.id,
        topic="AI marketing",
        marketing_angle="AI saves time",
        target_audience="founders",
        tone="authoritative",
        key_messages=["Save time"],
        platform_strategy={},
    )
    state.script = Script(
        job_id=state.job.id,
        type="image_script",
        content="Did you know AI can 10x your ROI?\n...",
        image_prompts=["AI marketing office"],
        created_by="agent:cst",
        version=1,
    )
    agent = CSAAgent()

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=csa_approved_response)):
        result = await agent.run(state)

    assert result.approval_decision["decision"] == "approved"
    assert result.job.status == ContentJobStatus.APPROVED
    assert len(result.job.approval_records) == 1
    assert result.improvement_feedback is None


@pytest.mark.asyncio
async def test_csa_agent_rejects_script():
    state = make_state("AI marketing")
    state.content_brief = ContentBrief(
        job_id=state.job.id,
        topic="AI marketing",
        marketing_angle="AI saves time",
        target_audience="founders",
        tone="authoritative",
        key_messages=["Save time"],
        platform_strategy={},
    )
    state.script = Script(
        job_id=state.job.id,
        type="image_script",
        content="AI is good.",
        image_prompts=[],
        created_by="agent:cst",
        version=1,
    )
    agent = CSAAgent()

    rejected_response = json.dumps({
        "decision": "rejected",
        "overall_score": 4,
        "criteria_scores": {"brand_alignment": 4, "audience_fit": 4, "hook_strength": 3,
                            "message_clarity": 5, "call_to_action": 3, "platform_suitability": 4},
        "strengths": [],
        "rejection_reasons": ["No compelling hook", "Missing CTA", "Too short"],
        "improvement_feedback": "Add a strong hook in the first line. Include a clear call-to-action.",
        "approval_notes": None,
    })

    with patch.object(agent, "call_llm", new=AsyncMock(return_value=rejected_response)):
        result = await agent.run(state)

    assert result.approval_decision["decision"] == "rejected"
    assert result.job.status == ContentJobStatus.REJECTED
    assert result.improvement_feedback is not None
    assert result.job.improvement_count == 1
