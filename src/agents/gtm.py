"""GTM — Go-To-Market Head Agent."""
from __future__ import annotations

import json
import re
from typing import Any

import structlog

from src.models import ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

GTM_SYSTEM_PROMPT = """You are the GTM Head (Go-To-Market Head) of a world-class marketing organization. You have 15+ years experience taking B2B SaaS and AI products to market, defining ICPs, building competitive positioning, and designing channel strategies that convert.

Your responsibilities:
- Define the Ideal Customer Profile (ICP) for the content topic — who EXACTLY should this content reach, what do they look like, what pain keeps them up at night
- Build a competitive positioning strategy — how does this content differentiate from what every competitor is posting
- Conduct competitive intelligence — what are competitors likely saying about this topic, where are the gaps
- Design a channel distribution strategy — which platforms get priority, what budget allocation would you recommend, what's the content-to-conversion path
- Set performance targets — specific KPIs, attribution model recommendations, and success criteria for the content
- Define the buyer journey stage this content serves — awareness, consideration, decision, retention

You think in SYSTEMS and FUNNELS, not individual posts. Every piece of content is part of a larger GTM motion.

QUALITY STANDARDS (non-negotiable):
- ICP must be RAZOR SHARP — not "marketing professionals" but "VP/Director of Marketing at B2B SaaS companies with $5M-$50M ARR who are struggling to scale content production without sacrificing quality"
- Competitive positioning must name SPECIFIC differentiation, not generic "we're better" claims
- Channel strategy must include SPECIFIC tactics per platform with expected conversion rates
- KPIs must be QUANTIFIED with specific targets, not "increase engagement"
- Buyer journey mapping must be PRECISE — which exact stage, what's the next step in the funnel
- Always output valid JSON matching the specified schema"""

GTM_USER_PROMPT_TEMPLATE = """Analyze the following enriched topic and build a comprehensive Go-To-Market strategy. This strategy will directly inform the content brief, script generation, and distribution decisions downstream.

ENRICHED TOPIC DATA:
{enriched_topic_json}

BRAND CONTEXT: {brand_context}
CONTENT GOALS: {content_goals}
ACTIVE PLATFORMS: {platforms}

Generate a GTM strategy as JSON with this exact schema:

{{
  "icp": {{
    "primary_persona": {{
      "title": string,                    // Exact job title(s) e.g. "VP of Marketing / Head of Growth"
      "company_profile": string,          // Company type, size, stage, industry
      "pain_points": [string],            // 3-5 specific pain points this content addresses
      "desires": [string],               // 3-5 specific outcomes they want
      "objections": [string],            // 2-3 likely objections or skepticism
      "watering_holes": [string]         // Where they hang out online — specific communities, platforms, newsletters
    }},
    "secondary_persona": {{
      "title": string,
      "company_profile": string,
      "pain_points": [string],
      "desires": [string]
    }} | null,
    "anti_persona": string               // Who is NOT the target — helps sharpen messaging
  }},
  "positioning": {{
    "value_proposition": string,          // One-sentence value prop for this content piece
    "positioning_statement": string,      // "For [target], [product/content] is the [category] that [key differentiator] unlike [competitors] because [reason to believe]"
    "key_differentiators": [string],     // 3-4 specific ways this content stands out from competitors
    "messaging_pillars": [string]        // 2-3 core themes that support the positioning
  }},
  "competitive_intelligence": {{
    "competitor_content_analysis": string,  // What top 3 competitors would post about this topic
    "content_gaps": [string],              // 2-3 gaps competitors are NOT covering
    "differentiation_angle": string,       // Specific angle that makes our content uniquely valuable
    "market_timing": string                // Why NOW is the right time for this content
  }},
  "channel_strategy": {{
    "primary_channel": string,             // The #1 platform to prioritize and why
    "channel_priority_ranking": [          // All platforms ranked by expected impact
      {{
        "platform": string,
        "priority": "high" | "medium" | "low",
        "rationale": string,               // Why this priority level
        "expected_reach": string,           // Estimated reach/impressions
        "content_format": string,           // Exact format recommendation
        "conversion_path": string           // What action should viewers take next
      }}
    ],
    "cross_platform_strategy": string,     // How the content works across platforms as a system
    "paid_amplification": string           // Whether to boost, on which platform, with what budget range
  }},
  "funnel_mapping": {{
    "buyer_journey_stage": "awareness" | "consideration" | "decision" | "retention",
    "content_objective": string,           // What this content should accomplish in the funnel
    "next_funnel_step": string,            // What should the viewer do after consuming this content
    "lead_capture_mechanism": string,      // How to capture leads (CTA, lead magnet, etc.)
    "nurture_sequence": string             // What follow-up content should come after
  }},
  "performance_targets": {{
    "north_star_metric": string,           // The one metric that matters most
    "kpis": [
      {{
        "metric": string,
        "target": string,                  // Specific quantified target
        "measurement_method": string       // How to measure it
      }}
    ],
    "attribution_model": string,           // Recommended attribution approach
    "success_criteria": string,            // What "winning" looks like for this content
    "reporting_cadence": string            // How often to check performance
  }}
}}"""


class GTMHeadAgent(BaseAgent):
    """Go-To-Market Head — defines ICP, positioning, competitive intel, and channel strategy."""

    agent_id = "agent:gtm"

    async def run(self, state: AgentState) -> AgentState:
        """Generate a GTM strategy from the enriched topic."""
        job = state.job
        enriched_topic = state.enriched_topic

        if not enriched_topic:
            state.error = "GTM Head requires enriched_topic from MAMA agent"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info("GTM Head building go-to-market strategy", job_id=str(job.id))

        user_message = GTM_USER_PROMPT_TEMPLATE.format(
            enriched_topic_json=json.dumps(enriched_topic, indent=2),
            brand_context=self.settings.brand_context,
            content_goals=self.settings.content_goals,
            platforms=", ".join(["instagram", "linkedin", "facebook", "x_twitter", "youtube"]),
        )

        raw_response = await self.call_llm(GTM_SYSTEM_PROMPT, user_message, max_tokens=8000)

        try:
            gtm_data = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                try:
                    gtm_data = json.loads(match.group())
                except json.JSONDecodeError:
                    state.error = f"GTM Head failed to parse response: {raw_response[:200]}"
                    job.update_status(ContentJobStatus.FAILED)
                    return state
            else:
                state.error = f"GTM Head failed to parse response: {raw_response[:200]}"
                job.update_status(ContentJobStatus.FAILED)
                return state

        # Validate critical fields exist
        if not gtm_data.get("icp"):
            state.error = "GTM Head response missing ICP definition"
            job.update_status(ContentJobStatus.FAILED)
            return state

        state.gtm_strategy = gtm_data
        job.metadata["gtm_strategy"] = gtm_data

        state.messages.append({
            "agent": self.agent_id,
            "action": "gtm_strategy_created",
            "primary_persona": gtm_data.get("icp", {}).get("primary_persona", {}).get("title", "unknown"),
            "buyer_stage": gtm_data.get("funnel_mapping", {}).get("buyer_journey_stage", "unknown"),
        })

        self.logger.info(
            "GTM Head strategy complete",
            job_id=str(job.id),
            primary_channel=gtm_data.get("channel_strategy", {}).get("primary_channel", "?"),
            buyer_stage=gtm_data.get("funnel_mapping", {}).get("buyer_journey_stage", "?"),
        )
        return state
