"""MAMA — Master Marketing Agent (Entry Point & Orchestrator)."""
from __future__ import annotations

import json

import structlog

from src.models import ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

MAMA_SYSTEM_PROMPT = """You are MAMA (Marketing Agent Multi-Agent Architecture), the master orchestrator of an AI-powered marketing content system.

Your responsibilities:
- Analyze incoming content triggers (trending topics, manual requests, scheduled jobs)
- Assess topic suitability for marketing content
- Enrich the topic with context (industry relevance, target audience, timing)
- Dispatch the enriched topic to the Content Marketing Ideator (CMI) for ideation
- Track workflow progress and escalate errors to human operators

You do NOT generate content ideas, scripts, or media assets. Your role is coordination and topic assessment only.

Guidelines:
- Always output valid JSON matching the specified schema
- Topics are assessed in the context of the brand's industry — ALWAYS respect the BRAND CONTEXT provided. Topics that are standard and legitimate within the brand's sector (finance, investment, energy, power, infrastructure, etc.) are ALWAYS suitable.
- Only set `suitable: false` for content that is explicitly illegal, promotes violence, contains explicit adult material, or is completely unrelated to any conceivable business purpose. Industry-specific topics such as financial returns, investment performance, energy pricing, power generation, regulatory updates, or sector market trends are NEVER unsuitable for brands operating in those sectors.
- Keep `enriched_context` concise (3-5 sentences max)
- Target audience should be specific (e.g., "B2B SaaS founders aged 30-45" not just "businesses")"""

MAMA_USER_PROMPT_TEMPLATE = """Analyze the following marketing content trigger and prepare it for the content ideation pipeline.

TRIGGER SOURCE: {trigger_source}
RAW TOPIC: {raw_topic}
BRAND CONTEXT: {brand_context}
ACTIVE PLATFORMS: {platforms}
CONTENT GOALS: {content_goals}

Today's date: {current_date}

Assess the topic and output a JSON object with this exact schema:

{{
  "suitable": boolean,
  "unsuitable_reason": string | null,
  "enriched_topic": string,
  "enriched_context": string,
  "target_audience": {{
    "primary": string,
    "secondary": string | null,
    "pain_points": [string],
    "desires": [string]
  }},
  "recommended_tone": "educational" | "inspirational" | "humorous" | "urgent" | "conversational" | "authoritative",
  "timing_relevance": "evergreen" | "trending_now" | "seasonal",
  "suggested_platforms": [string],
  "marketing_angle": string,
  "estimated_engagement_potential": "low" | "medium" | "high",
  "competitive_context": string,                      // What competitors are likely posting about this topic
  "content_differentiation_opportunity": string,      // Specific angle that would stand out
  "audience_emotional_state": string,                 // What the audience is feeling about this topic right now
  "trending_angles": [string]                         // 2-3 trending angles on this topic across social media
}}"""


class MAMAAgent(BaseAgent):
    """Entry point agent — enriches topics and routes to CMI."""

    agent_id = "agent:mama"

    async def run(self, state: AgentState) -> AgentState:
        """Analyze the trigger topic and enrich it for downstream processing."""
        job = state.job
        self.logger.info("MAMA analyzing topic", job_id=str(job.id), topic=job.topic)
        job.update_status(ContentJobStatus.IN_PROGRESS)

        from datetime import date

        user_message = MAMA_USER_PROMPT_TEMPLATE.format(
            trigger_source=job.topic_source.value,
            raw_topic=job.topic,
            brand_context=self.settings.brand_context,
            platforms=", ".join(["instagram", "linkedin", "facebook", "x_twitter", "youtube"]),
            content_goals=self.settings.content_goals,
            current_date=date.today().isoformat(),
        )

        raw_response = await self.call_llm(MAMA_SYSTEM_PROMPT, user_message)

        # Parse JSON response
        try:
            enriched = json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            import re
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                enriched = json.loads(match.group())
            else:
                state.error = f"MAMA failed to parse LLM response: {raw_response[:200]}"
                job.update_status(ContentJobStatus.FAILED)
                return state

        if not enriched.get("suitable", True):
            self.logger.warning(
                "Topic unsuitable for marketing",
                job_id=str(job.id),
                reason=enriched.get("unsuitable_reason"),
            )
            state.error = f"Topic unsuitable: {enriched.get('unsuitable_reason')}"
            job.update_status(ContentJobStatus.FAILED)
            return state

        state.enriched_topic = enriched
        state.messages.append({
            "agent": self.agent_id,
            "action": "topic_enriched",
            "output": enriched,
        })

        self.logger.info(
            "MAMA enriched topic",
            job_id=str(job.id),
            engagement_potential=enriched.get("estimated_engagement_potential"),
        )
        return state
