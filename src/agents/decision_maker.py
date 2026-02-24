"""Decision Maker — Routes content to Image Post or Video Post pipeline."""
from __future__ import annotations

import json
import re

import structlog

from src.models import PipelineType, ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

# Keywords that signal an explicit user intent to create images
_IMAGE_KEYWORDS = {
    "image", "images", "photo", "photos", "picture", "pictures",
    "infographic", "infographics", "static", "illustration", "graphic",
    "poster", "thumbnail", "banner", "image post", "image only",
}

# Keywords that signal an explicit user intent to create video
_VIDEO_KEYWORDS = {
    "video", "videos", "reel", "reels", "clip", "clips", "animation",
    "animated", "motion", "film", "cinematic", "short film", "story",
    "video post", "video only",
}


def _detect_explicit_intent(text: str) -> str | None:
    """
    Scan a description/name for explicit image or video intent.
    Returns 'image_post', 'video_post', or None if no clear signal.
    """
    lower = text.lower()
    words = set(re.findall(r"[a-z_]+", lower))
    # Also check multi-word phrases
    has_image = bool(words & _IMAGE_KEYWORDS) or any(p in lower for p in ("image post", "image only", "static image"))
    has_video = bool(words & _VIDEO_KEYWORDS) or any(p in lower for p in ("video post", "video only", "short video"))

    if has_image and not has_video:
        return "image_post"
    if has_video and not has_image:
        return "video_post"
    # Both or neither — let LLM decide
    return None


DECISION_MAKER_SYSTEM_PROMPT = """You are the Decision Maker module in the MAMA marketing content system.

Your sole responsibility is to decide whether a content brief should be produced as:
- An IMAGE POST (static image + caption)
- A VIDEO POST (short-form video with narration)

Decision criteria:
- IMAGE POST: Informational content, statistics, quotes, tips, infographics, announcements, product showcases
- VIDEO POST: Storytelling content, tutorials, demonstrations, emotional narratives, trending social formats, entertainment

Consider:
- The user's explicit intent from the job description (HIGHEST priority — if they say "image" or "video", follow it)
- The marketing angle and tone from the content brief
- The suggested platforms (YouTube and TikTok strongly suggest video)
- The complexity and depth of the message
- The engagement potential for each format

Output ONLY valid JSON with this schema:
{
  "pipeline_type": "image_post" | "video_post",
  "confidence": "high" | "medium" | "low",
  "rationale": string
}"""

DECISION_MAKER_USER_TEMPLATE = """Decide the optimal content format for the following content brief.

{job_context}CONTENT BRIEF:
{brief_json}

ENRICHED TOPIC DATA:
{topic_json}

Return your decision as JSON."""


class DecisionMakerAgent(BaseAgent):
    """Routes content brief to the appropriate pipeline (image or video)."""

    agent_id = "module:decision-maker"

    async def run(self, state: AgentState) -> AgentState:
        """Decide pipeline type based on content brief."""
        job = state.job
        content_brief = state.content_brief

        if not content_brief:
            state.error = "Decision Maker requires content_brief from CMI"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info("Decision Maker routing content", job_id=str(job.id))

        # ── 1. Check for explicit user intent in description / name ──────
        explicit_type: str | None = None
        intent_source: str = ""

        for field_name, field_value in [("description", job.description), ("name", job.name)]:
            if field_value:
                detected = _detect_explicit_intent(field_value)
                if detected:
                    explicit_type = detected
                    intent_source = field_name
                    break

        if explicit_type:
            decision = {
                "pipeline_type": explicit_type,
                "confidence": "high",
                "rationale": f"Explicit user intent detected in job {intent_source}: '{job.description or job.name}'",
            }
            self.logger.info(
                "Decision Maker: explicit intent override",
                job_id=str(job.id),
                pipeline_type=explicit_type,
                source=intent_source,
            )
        else:
            # ── 2. No explicit intent — let the LLM decide ───────────────
            brief_dict = content_brief.model_dump(mode="json")
            topic_dict = state.enriched_topic or {}

            # Include description as context if present
            job_context = ""
            if job.description:
                job_context = f"JOB DESCRIPTION (from user):\n{job.description}\n\n"
            elif job.name:
                job_context = f"JOB NAME (from user):\n{job.name}\n\n"

            user_message = DECISION_MAKER_USER_TEMPLATE.format(
                job_context=job_context,
                brief_json=json.dumps(brief_dict, indent=2),
                topic_json=json.dumps(topic_dict, indent=2),
            )

            raw_response = await self.call_llm(DECISION_MAKER_SYSTEM_PROMPT, user_message)

            try:
                decision = json.loads(raw_response)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if match:
                    decision = json.loads(match.group())
                else:
                    # Default to image_post on parse failure
                    decision = {"pipeline_type": "image_post", "confidence": "low", "rationale": "parse_error"}

        pipeline_type = PipelineType(decision["pipeline_type"])
        job.pipeline_type = pipeline_type
        state.pipeline_type = pipeline_type.value
        job.metadata["pipeline_decision"] = decision

        state.messages.append({
            "agent": self.agent_id,
            "action": "pipeline_decided",
            "pipeline_type": pipeline_type.value,
            "confidence": decision.get("confidence"),
            "rationale": decision.get("rationale"),
        })

        self.logger.info(
            "Decision Maker routed to pipeline",
            job_id=str(job.id),
            pipeline_type=pipeline_type.value,
            confidence=decision.get("confidence"),
        )
        return state
