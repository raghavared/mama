"""CMI — Content Marketing Ideator Agent."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

import structlog

from src.models import ContentBrief, ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

CMI_SYSTEM_PROMPT = """You are CMI (Content Marketing Ideator), a world-class marketing strategist with 20+ years experience building campaigns for Fortune 500 brands in finance, energy, infrastructure, and technology sectors.

Your responsibilities:
- Transform enriched topic analysis into a razor-sharp content marketing brief that wins attention in a noisy feed
- Develop a differentiated, non-generic marketing angle that competitors would NOT produce
- Define hyper-specific platform strategy — not generic advice, but exact content tactics for each network
- Identify 2-3 deep psychological triggers (FOMO, authority, social proof, reciprocity, loss aversion, aspiration) that will drive measurable engagement
- Craft key messages that are quotable, memorable, and share-worthy

You output ONLY the content brief. You do NOT write scripts, generate images, or decide on content type.

QUALITY STANDARDS (non-negotiable):
- Marketing angle must be SPECIFIC and DIFFERENTIATED — "Our fund delivers 12% returns" is generic. "How our infrastructure fund turned India's power deficit into investor alpha" is differentiated.
- Every key message must pass the "So what?" test — if an audience member could reasonably say "so what?", rewrite it
- Platform strategy must specify EXACT content tactics (carousel vs single image, text length, posting hook format, CTA type) per platform — not generic "post engaging content"
- Psychological hooks must name the specific trigger and explain HOW the content will activate it
- Call-to-action must be specific and low-friction (not "contact us" — "Download the 2-page fund summary")
- Hashtag strategy must mix reach tags (>500k posts), niche tags (10k-100k posts), and brand tags
- Always output valid JSON matching the specified schema"""

CMI_USER_PROMPT_TEMPLATE = """Create a world-class content marketing brief for the following enriched topic analysis. Your brief will be used directly by a senior copywriter and creative director to produce content that must outperform category benchmarks.

ENRICHED TOPIC DATA:
{enriched_topic_json}

GTM STRATEGY (from GTM Head — use this to sharpen your ICP targeting, positioning, and channel tactics):
{gtm_strategy_json}

BRAND CONTEXT: {brand_context}
CONTENT GOALS: {content_goals}

Generate a detailed content brief as JSON with this exact schema:

{{
  "marketing_angle": string,          // Specific, differentiated angle — NOT generic. Min 2 sentences.
  "angle_rationale": string,          // Why THIS angle beats competitors. 1-2 sentences.
  "target_audience": string,          // Hyper-specific: role, seniority, pain state, desire state
  "tone": "educational" | "inspirational" | "humorous" | "urgent" | "conversational" | "authoritative",
  "tone_justification": string,       // Why this tone wins with this audience on these platforms
  "key_messages": [string],           // Exactly 3-5 messages. Each must be quotable and pass "So what?" test
  "platform_strategy": {{
    "instagram": string,              // EXACT tactics: reel vs carousel vs single, caption style, hook format
    "linkedin": string,               // EXACT tactics: article vs post, length, professional hook style
    "facebook": string,               // EXACT tactics: video vs image, community angle, sharing trigger
    "x_twitter": string,              // EXACT tactics: thread vs single tweet, hook tweet, character strategy
    "youtube": string                 // EXACT tactics: short vs long-form, thumbnail concept, title formula
  }},
  "psychological_hooks": [            // Exactly 2-3 hooks
    {{
      "trigger": string,              // Name the trigger: "FOMO", "Authority", "Social Proof", "Loss Aversion", "Aspiration", "Curiosity Gap"
      "activation_method": string     // Exactly HOW the content will activate this trigger
    }}
  ],
  "content_angle_rationale": string,  // Full strategic rationale, 2-3 sentences
  "hashtag_strategy": {{
    "reach_tags": [string],           // 3-4 high-volume tags (>500k posts)
    "niche_tags": [string],           // 3-4 niche tags (10k-100k posts)
    "brand_tags": [string]            // 1-2 brand/campaign specific tags
  }},
  "call_to_action": string,           // Specific, low-friction CTA with exact action and value proposition
  "content_hook_formula": string,     // The opening hook structure to use (e.g., "Contrarian statement + data proof")
  "competitor_differentiation": string  // What makes this angle unique vs what competitors would post
}}"""


class CMIAgent(BaseAgent):
    """Content Marketing Ideator — generates marketing strategy and content brief."""

    agent_id = "agent:cmi"

    async def run(self, state: AgentState) -> AgentState:
        """Generate a content brief from the enriched topic."""
        job = state.job
        enriched_topic = state.enriched_topic

        if not enriched_topic:
            state.error = "CMI requires enriched_topic from MAMA agent"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info("CMI generating content brief", job_id=str(job.id))

        gtm_strategy = state.gtm_strategy or {}
        user_message = CMI_USER_PROMPT_TEMPLATE.format(
            enriched_topic_json=json.dumps(enriched_topic, indent=2),
            gtm_strategy_json=json.dumps(gtm_strategy, indent=2) if gtm_strategy else "Not available",
            brand_context=self.settings.brand_context,
            content_goals=self.settings.content_goals,
        )

        raw_response = await self.call_llm(CMI_SYSTEM_PROMPT, user_message, max_tokens=8000)

        try:
            brief_data = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                brief_data = json.loads(match.group())
            else:
                state.error = f"CMI failed to parse response: {raw_response[:200]}"
                job.update_status(ContentJobStatus.FAILED)
                return state

        content_brief = ContentBrief(
            job_id=job.id,
            topic=enriched_topic.get("enriched_topic", job.topic),
            marketing_angle=brief_data["marketing_angle"],
            target_audience=brief_data["target_audience"],
            tone=brief_data["tone"],
            key_messages=brief_data["key_messages"],
            platform_strategy=brief_data["platform_strategy"],
            created_by=self.agent_id,
            created_at=datetime.utcnow(),
        )

        # Store full enriched CMI output in job metadata
        job.metadata["cmi_brief_extended"] = {
            "angle_rationale": brief_data.get("angle_rationale", ""),
            "tone_justification": brief_data.get("tone_justification", ""),
            "psychological_hooks": brief_data.get("psychological_hooks", []),
            "content_angle_rationale": brief_data.get("content_angle_rationale", ""),
            "hashtag_strategy": brief_data.get("hashtag_strategy", {}),
            "call_to_action": brief_data.get("call_to_action", ""),
            "content_hook_formula": brief_data.get("content_hook_formula", ""),
            "competitor_differentiation": brief_data.get("competitor_differentiation", ""),
        }

        job.content_brief = content_brief
        state.content_brief = content_brief

        state.messages.append({
            "agent": self.agent_id,
            "action": "content_brief_created",
            "marketing_angle": content_brief.marketing_angle,
        })

        self.logger.info(
            "CMI created content brief",
            job_id=str(job.id),
            marketing_angle=content_brief.marketing_angle[:80],
        )
        return state
