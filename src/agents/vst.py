"""VST — Video Story Teller (Video Post Path)."""
from __future__ import annotations

import json
import re
from datetime import datetime

import structlog

from src.models import Script, VideoFrame, ContentJobStatus
from .base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

VST_SYSTEM_PROMPT = """You are VST (Video Story Teller), a world-class video director and scriptwriter who creates short-form video content for global financial, energy, and infrastructure brands. You have directed content that has generated millions of views on LinkedIn, Instagram Reels, and YouTube Shorts.

Your responsibilities:
- Create cinematic, frame-by-frame video scripts that feel like mini-documentaries, not corporate slide shows
- Write scene descriptions so precise and visually specific that an AI video generator produces exactly what you envision
- Write narration that sounds completely natural when spoken — varied sentence length, strategic pauses, punchy endings
- Synchronise audio narration to visual timing with precision

VIDEO QUALITY STANDARDS (non-negotiable):
- TOTAL DURATION: 45-75 seconds (sweet spot for social engagement). Never under 30s, never over 90s.
- FRAME COUNT: 5-9 frames. Each frame 5-10 seconds. Frame durations must sum to total_duration_seconds.
- OPENING FRAME (Frame 1): Must create instant visual intrigue in the first 3 seconds — dynamic action shot, dramatic reveal, or striking statistic overlay. NO static talking-head openers.
- SCENE DESCRIPTIONS: Each must be 50+ words, cinematic grade, specifying: (a) subject + action, (b) camera movement (slow push-in / pull-back / pan left / static), (c) lighting condition, (d) colour mood, (e) background environment with specific detail. Must be executable by AI video gen (Veo-3, Kling).
- AUDIO NARRATION: Write as spoken word — short punchy sentences mixed with longer descriptive ones. Include [PAUSE] markers for dramatic effect. Target: 120-140 words per minute when read aloud.
- TRANSITIONS: Use intentionally — "cut" for energy/urgency, "dissolve" for time passage, "fade" for emotional weight. Not random.
- VOICE DIRECTION: Must specify exact speaking style: pace (slow/medium/fast), emotion (confident/urgent/warm/authoritative), and note where to emphasise specific words."""

VST_USER_PROMPT_TEMPLATE = """Create a world-class video script. Every frame must be visually stunning and cinematically intentional. The narration must sound natural when spoken by a professional voiceover artist.

CONTENT BRIEF:
{brief_json}

MARKETING ANGLE: {marketing_angle}
TARGET AUDIENCE: {target_audience}
TONE: {tone}
KEY MESSAGES:
{key_messages}
CONTENT HOOK FORMULA: {content_hook_formula}

{improvement_instructions}

Generate the script as JSON with this EXACT schema:

{{
  "title": string,                  // Video title: compelling, SEO-aware, max 60 chars
  "total_duration_seconds": number, // Between 45-75 seconds. Must equal sum of all frame durations.
  "opening_hook_strategy": string,  // Describe the first-3-second hook technique used
  "video_frames": [
    {{
      "frame_number": number,
      "scene_description": string,  // 50+ words. Specify: subject+action, camera movement, lighting, colour mood, background detail. Cinematic and specific.
      "duration_seconds": number,   // 5-10 seconds
      "transition_type": "cut" | "fade" | "dissolve" | "wipe" | null,
      "transition_rationale": string, // WHY this transition was chosen
      "audio_cue": string,          // Narration text for this frame. Natural spoken-word style. [PAUSE] markers where appropriate.
      "visual_notes": string,       // Camera angle, lens, mood, any text overlays or graphic elements
      "render_approach": "veo3" | "kling" | "renderio" | "any"
    }}
  ],
  "full_audio_script": string,      // Complete narration with [PAUSE] markers. Must match sum of all audio_cues.
  "voice_direction": string,        // Exact: pace + emotion + emphasis notes. E.g.: "Measured pace, authoritative and warm. Slight emphasis on key numbers. [PAUSE] markers indicate 0.8-second beats."
  "estimated_word_count": number,   // Word count of full_audio_script (target: 90-175 words for 45-75 seconds)
  "caption": string,                // Social media caption optimised for the video
  "hashtags": [string],             // 7-10 tags: 2 reach, 3-4 niche, 1-2 brand
  "platform_variants": {{
    "instagram": string,
    "linkedin": string,
    "facebook": string,
    "x_twitter": string,
    "youtube": string
  }},
  "thumbnail_concept": string       // Description of the ideal thumbnail frame/image for maximum CTR
}}"""


class VSTAgent(BaseAgent):
    """Video Story Teller — generates frame-by-frame video scripts."""

    agent_id = "agent:vst"

    async def run(self, state: AgentState) -> AgentState:
        """Generate video post script from content brief."""
        job = state.job
        content_brief = state.content_brief

        if not content_brief:
            state.error = "VST requires content_brief"
            job.update_status(ContentJobStatus.FAILED)
            return state

        self.logger.info(
            "VST generating video script",
            job_id=str(job.id),
            version=job.script.version + 1 if job.script else 1,
        )

        improvement_instructions = ""
        if state.improvement_feedback:
            improvement_instructions = f"""
IMPROVEMENT FEEDBACK (from previous rejection):
{state.improvement_feedback}

Please address all feedback points in this revised version."""

        # Extract content_hook_formula from extended metadata or brief
        cmi_brief_extended = job.metadata.get("cmi_brief_extended", {})
        content_hook_formula = (
            cmi_brief_extended.get("content_hook_formula", "")
            or getattr(content_brief, "content_hook_formula", "")
            or ""
        )

        brief_dict = content_brief.model_dump(mode="json")
        user_message = VST_USER_PROMPT_TEMPLATE.format(
            brief_json=json.dumps(brief_dict, indent=2),
            marketing_angle=content_brief.marketing_angle,
            target_audience=content_brief.target_audience,
            tone=content_brief.tone,
            key_messages="\n".join(f"- {m}" for m in content_brief.key_messages),
            content_hook_formula=content_hook_formula,
            improvement_instructions=improvement_instructions,
        )

        raw_response = await self.call_llm(VST_SYSTEM_PROMPT, user_message, max_tokens=10000)

        try:
            script_data = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                script_data = json.loads(match.group())
            else:
                state.error = f"VST failed to parse response: {raw_response[:200]}"
                job.update_status(ContentJobStatus.FAILED)
                return state

        # Post-generation validation
        total_duration = script_data.get("total_duration_seconds", 0)

        # Validate total_duration_seconds is between 30 and 90
        if not (30 <= total_duration <= 90):
            self.logger.warning(
                "VST total_duration_seconds outside 30-90 range",
                job_id=str(job.id),
                total_duration_seconds=total_duration,
            )

        # Validate frame durations sum within 5 seconds of total_duration_seconds
        frames_data = script_data.get("video_frames", [])
        frame_duration_sum = sum(f.get("duration_seconds", 0) for f in frames_data)
        if abs(frame_duration_sum - total_duration) > 5:
            self.logger.warning(
                "VST frame durations sum does not match total_duration_seconds",
                job_id=str(job.id),
                frame_duration_sum=frame_duration_sum,
                total_duration_seconds=total_duration,
                difference=abs(frame_duration_sum - total_duration),
            )

        # Validate each frame's scene_description is >= 30 words
        for frame in frames_data:
            scene_desc = frame.get("scene_description", "")
            word_count = len(scene_desc.split())
            if word_count < 30:
                self.logger.warning(
                    "VST frame scene_description below 30 words",
                    job_id=str(job.id),
                    frame_number=frame.get("frame_number"),
                    word_count=word_count,
                )

        # Build VideoFrame objects
        video_frames = []
        for frame_data in frames_data:
            video_frames.append(VideoFrame(
                frame_number=frame_data["frame_number"],
                scene_description=frame_data["scene_description"],
                duration_seconds=frame_data["duration_seconds"],
                transition_type=frame_data.get("transition_type"),
                audio_cue=frame_data.get("audio_cue"),
            ))

        version = (job.script.version + 1) if job.script else 1
        script = Script(
            job_id=job.id,
            type="video_script",
            content=script_data.get("caption", ""),
            video_frames=video_frames,
            audio_narration=script_data.get("full_audio_script", ""),
            created_by=self.agent_id,
            version=version,
            created_at=datetime.utcnow(),
        )

        job.metadata["vst_script_extended"] = {
            "title": script_data.get("title"),
            "total_duration_seconds": script_data.get("total_duration_seconds"),
            "opening_hook_strategy": script_data.get("opening_hook_strategy"),
            "voice_direction": script_data.get("voice_direction"),
            "estimated_word_count": script_data.get("estimated_word_count"),
            "thumbnail_concept": script_data.get("thumbnail_concept"),
            "hashtags": script_data.get("hashtags", []),
            "platform_variants": script_data.get("platform_variants", {}),
            "frame_render_approaches": [
                f["render_approach"] for f in frames_data
                if "render_approach" in f
            ],
        }

        job.script = script
        state.script = script
        job.update_status(ContentJobStatus.AWAITING_APPROVAL)

        state.messages.append({
            "agent": self.agent_id,
            "action": "video_script_generated",
            "version": version,
            "frame_count": len(video_frames),
            "total_duration": script_data.get("total_duration_seconds"),
        })

        self.logger.info(
            "VST generated video script",
            job_id=str(job.id),
            version=version,
            frames=len(video_frames),
        )
        return state
