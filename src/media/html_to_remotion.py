"""Converts video script frames to Remotion MarketingVideo composition props via LLM."""
from __future__ import annotations

import json
import re

import structlog

from src.agents.base import AgentState, BaseAgent
from src.config import get_settings

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a video content designer. Given a list of video scenes,
extract the key content elements and format them as JSON props for a marketing video composition.
Always return valid JSON only. No markdown, no explanation."""


class HTMLToRemotionGenerator(BaseAgent):
    """Generates Remotion MarketingVideo props from a video Script using an LLM."""

    agent_id = "module:html-to-remotion"

    async def run(self, state: AgentState) -> AgentState:
        """Not used as a pipeline node directly."""
        return state

    async def generate_props(self, script) -> dict:
        """Generate Remotion MarketingVideo props from a Script object.

        Args:
            script: A Script instance with video_frames or audio_narration.

        Returns:
            A dict of props matching the MarketingVideo composition schema.
        """
        settings = get_settings()

        frames_text = ""
        if script and hasattr(script, "video_frames") and script.video_frames:
            frames_text = "\n".join(
                f"Scene {f.frame_number}: {f.scene_description}"
                for f in script.video_frames[:5]
            )
        elif script and hasattr(script, "audio_narration") and script.audio_narration:
            frames_text = script.audio_narration
        else:
            frames_text = "Marketing content"

        user_message = f"""Extract video props from these scenes:
{frames_text}

Return JSON with these exact fields (all strings, all optional):
{{
  "title": "<main headline, max 8 words>",
  "subtitle": "<supporting text, max 12 words>",
  "bodyText": "<key message, max 20 words>",
  "ctaText": "<call to action, max 5 words>",
  "brandColor": "<hex color matching content mood, e.g. #6366f1>",
  "accentColor": "<complementary hex color, e.g. #f59e0b>",
  "backgroundType": "gradient",
  "hashtags": ["<tag1>", "<tag2>", "<tag3>"]
}}"""

        try:
            response = await self.call_llm(SYSTEM_PROMPT, user_message, max_tokens=512)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            logger.warning(
                "No JSON object found in LLM response for Remotion props",
                response_preview=response[:200],
            )
        except Exception as e:
            logger.warning("Failed to generate Remotion props via LLM", error=str(e))

        # Fallback defaults
        return {
            "title": settings.brand_name,
            "subtitle": settings.brand_description[:50],
            "ctaText": "Learn More",
            "brandColor": "#6366f1",
            "accentColor": "#f59e0b",
            "backgroundType": "gradient",
        }
