"""CST — Content Story Teller (Image Post Path)."""
from __future__ import annotations

import json
import re
from datetime import datetime

import structlog

from src.models import Script, ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

CST_SYSTEM_PROMPT = """You are CST (Content Story Teller), a world-class senior copywriter and creative director who has crafted viral campaigns for global financial institutions, energy companies, and infrastructure brands. You understand how to make complex B2B topics instantly compelling for a social media audience.

Your responsibilities:
- Transform content briefs into emotionally resonant, platform-native scripts that stop the scroll
- Craft hooks that outperform industry benchmarks (top 5% engagement rate)
- Write image prompts that produce magazine-cover quality photography indistinguishable from a $10,000 photo shoot

COPY QUALITY STANDARDS (non-negotiable):
- HOOK: Must create an open loop, use a pattern interrupt, or make a bold claim in the FIRST 7 words. Test: would you stop scrolling? If not, rewrite.
- NARRATIVE: Use a 3-act micro-structure: (1) Tension/Problem, (2) Insight/Shift, (3) Resolution/Aspiration. No flat informational lists.
- CTA: Must be specific + benefit-led. NOT "Contact us." YES "Download our 2-page fund summary — see the exact infrastructure plays generating 14% returns."
- CAPTION LENGTH: Instagram ≤ 2200 chars (aim 150-300 for maximum reach), LinkedIn 1300-1900 chars (longer performs better for thought leadership), Facebook 40-80 words for image posts
- HASHTAGS: 5-10 total, mix of: 2 broad reach (>1M posts), 3 niche authority (10k-200k posts), 1-2 brand-specific

IMAGE PROMPT QUALITY RULES (critical — follow exactly):
- Every image prompt MUST produce a photorealistic, high-end result that looks like it was shot by a professional photographer for a tier-1 finance or energy industry publication
- MANDATORY in every prompt: "photorealistic, shot on Sony A7R V with 85mm f/1.4 lens, f/1.8 aperture, ISO 100, professional three-point studio lighting with Profoto B10 strobes, 8K resolution, ultra-sharp focus, fine micro-detail in textures, award-winning commercial photography"
- Human subjects: "real person, natural skin texture, subtle smile, authentic confident expression, NOT AI-generated look, NOT stock photo model look"
- Lighting must be specified precisely: choose from "cinematic Rembrandt lighting with 45° key light", "soft diffused natural window light from camera left", "golden hour backlight with warm 3200K fill", or "dramatic split lighting for high-contrast authority feel"
- Composition: always specify "rule of thirds composition, subject at left/right third, blurred background bokeh (f/1.8), strong foreground-background separation"
- Colour grade: "professional Lightroom colour grade — [choose: warm amber tones and rich blacks for premium feel / cool steel-blue tones for tech/finance gravitas / neutral natural tones for authenticity]"
- Setting must be SPECIFIC: NOT "office" but "modern open-plan trading floor with Bloomberg terminals, city skyline visible through floor-to-ceiling glass, late afternoon natural light"
- Anti-patterns — NEVER write: "an image of", "a picture showing", "create an image", generic "businessman", generic "handshake", generic "graph on screen"
- Minimum 100 words per image prompt
- Generate exactly 3 image prompts per script, each showing a DIFFERENT scene/angle/moment that together tell the full visual story"""

CST_USER_PROMPT_TEMPLATE = """Create a world-class image post script. This content must outperform competitor posts. Every word is deliberate. Every image prompt is production-ready.

CONTENT BRIEF:
{brief_json}

MARKETING ANGLE: {marketing_angle}
TARGET AUDIENCE: {target_audience}
TONE: {tone}
KEY MESSAGES:
{key_messages}
CONTENT HOOK FORMULA: {content_hook_formula}
PSYCHOLOGICAL HOOKS: {psychological_hooks}

{improvement_instructions}

Generate the script as JSON with this EXACT schema:

{{
  "hook": string,           // Opens with pattern interrupt or bold claim. Max 10 words. Test: stops the scroll.
  "hook_type": string,      // Label the technique: "contrarian claim", "open loop question", "bold statistic", "social proof", "loss aversion"
  "narrative": string,      // 3-act micro-structure: Tension → Insight → Aspiration. No lists. Conversational paragraphs.
  "call_to_action": string, // Specific + benefit-led. Not generic. States exact action AND exact value gained.
  "full_caption": string,   // Complete post combining hook + narrative + CTA. Platform: Instagram (150-300 chars for reach)
  "image_prompts": [string], // EXACTLY 3 prompts. Each 100+ words. Each a different scene. All photorealistic. All follow IMAGE PROMPT QUALITY RULES.
  "image_style_notes": string, // Unified visual style guide: brand colour palette, mood board reference, consistency notes across all 3 images
  "hashtags": [string],     // 7-10 tags: 2 reach (>1M), 3-4 niche authority (10k-200k), 1-2 brand
  "platform_variants": {{
    "instagram": string,    // ≤300 words, hook-first, line-breaks for readability, emojis if tone suits
    "linkedin": string,     // 1300-1900 chars, thought-leadership tone, no emojis, ends with question to drive comments
    "facebook": string      // 40-80 words for image post, community-oriented framing, clear sharing trigger
  }},
  "engagement_prediction": string,  // Why this specific hook+angle will outperform: 1-2 sentences
  "ab_test_suggestion": string      // One alternative hook to A/B test against the primary
}}"""


class CSTAgent(BaseAgent):
    """Content Story Teller — generates image post scripts and image prompts."""

    agent_id = "agent:cst"

    async def run(self, state: AgentState) -> AgentState:
        """Generate image post script from content brief."""
        job = state.job
        content_brief = state.content_brief

        if not content_brief:
            state.error = "CST requires content_brief"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info(
            "CST generating image script",
            job_id=str(job.id),
            version=job.script.version + 1 if job.script else 1,
        )

        improvement_instructions = ""
        if state.improvement_feedback:
            improvement_instructions = f"""
IMPROVEMENT FEEDBACK (from previous rejection):
{state.improvement_feedback}

Please address all feedback points in this revised version."""

        # Extract content_hook_formula and psychological_hooks from extended metadata or brief
        cmi_brief_extended = job.metadata.get("cmi_brief_extended", {})
        content_hook_formula = (
            cmi_brief_extended.get("content_hook_formula", "")
            or getattr(content_brief, "content_hook_formula", "")
            or ""
        )
        psychological_hooks = (
            cmi_brief_extended.get("psychological_hooks", "")
            or getattr(content_brief, "psychological_hooks", "")
            or ""
        )

        brief_dict = content_brief.model_dump(mode="json")
        user_message = CST_USER_PROMPT_TEMPLATE.format(
            brief_json=json.dumps(brief_dict, indent=2),
            marketing_angle=content_brief.marketing_angle,
            target_audience=content_brief.target_audience,
            tone=content_brief.tone,
            key_messages="\n".join(f"- {m}" for m in content_brief.key_messages),
            content_hook_formula=content_hook_formula,
            psychological_hooks=psychological_hooks,
            improvement_instructions=improvement_instructions,
        )

        raw_response = await self.call_llm(CST_SYSTEM_PROMPT, user_message, max_tokens=8000)

        try:
            script_data = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                script_data = json.loads(match.group())
            else:
                state.error = f"CST failed to parse response: {raw_response[:200]}"
                job.update_status(ContentJobStatus.FAILED)
                return state

        # Post-generation validation: exactly 3 image prompts, each >= 80 words
        image_prompts = script_data.get("image_prompts", [])
        if len(image_prompts) != 3:
            self.logger.warning(
                "CST image_prompts count is not 3",
                job_id=str(job.id),
                count=len(image_prompts),
            )
        for i, prompt in enumerate(image_prompts):
            word_count = len(prompt.split())
            if word_count < 80:
                self.logger.warning(
                    "CST image prompt below 80 words",
                    job_id=str(job.id),
                    prompt_index=i,
                    word_count=word_count,
                )

        version = (job.script.version + 1) if job.script else 1
        script = Script(
            job_id=job.id,
            type="image_script",
            content=script_data["full_caption"],
            image_prompts=script_data.get("image_prompts", []),
            created_by=self.agent_id,
            version=version,
            created_at=datetime.utcnow(),
        )

        # Store extended data in metadata
        job.metadata["cst_script_extended"] = {
            "hook": script_data.get("hook"),
            "hook_type": script_data.get("hook_type"),
            "narrative": script_data.get("narrative"),
            "call_to_action": script_data.get("call_to_action"),
            "image_style_notes": script_data.get("image_style_notes"),
            "hashtags": script_data.get("hashtags", []),
            "platform_variants": script_data.get("platform_variants", {}),
            "engagement_prediction": script_data.get("engagement_prediction"),
            "ab_test_suggestion": script_data.get("ab_test_suggestion"),
        }

        job.script = script
        state.script = script
        job.update_status(ContentJobStatus.AWAITING_APPROVAL)

        state.messages.append({
            "agent": self.agent_id,
            "action": "script_generated",
            "version": version,
            "image_prompts_count": len(script.image_prompts or []),
        })

        self.logger.info("CST generated script", job_id=str(job.id), version=version)
        return state
