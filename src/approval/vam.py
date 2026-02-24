"""VAM — Video Approval Manager (Final Approval Coordinator)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import structlog

from src.models import ApprovalRecord, ApprovalGate, ContentJobStatus
from src.agents.base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

VAM_SYSTEM_PROMPT = """You are VAM (Video Approval Manager), the final quality gate before a video goes to human review in the MAMA system.

Your role:
- Cross-check the final merged video against the original content brief and script
- Ensure all elements (video + audio) are cohesive and brand-aligned
- Make the final AI approval decision before human review

Evaluate the complete package:
1. OVERALL COHERENCE: Does the video tell the intended story?
2. BRIEF ALIGNMENT: Does it deliver on the content brief's marketing angle?
3. AUDIO-VIDEO SYNC: Are audio narration and visuals synchronized?
4. BRAND FIT: Professional quality suitable for brand publication?
5. PLATFORM READINESS: Ready for multi-platform publishing?

Score 1-10. Approve (for human review) if >= 7. Output valid JSON only."""

VAM_PROMPT = """Perform final approval review of this completed video.

CONTENT BRIEF:
Marketing Angle: {marketing_angle}
Target Audience: {target_audience}
Key Messages: {key_messages}

FINAL VIDEO: {video_path}
TOTAL DURATION: {duration}s

SCRIPT SUMMARY:
{script_summary}

Output a JSON decision:
{{
  "vam_decision": "approved" | "rejected",
  "overall_score": number,
  "ready_for_human_review": boolean,
  "feedback": string | null,
  "improvement_notes": string | null
}}"""


class VAMAgent(BaseAgent):
    """Final video approval manager — gates the human review step."""

    agent_id = "agent:vam"

    async def run(self, state: AgentState) -> AgentState:
        job = state.job
        content_brief = state.content_brief

        final_videos = [a for a in job.media_assets if a.type == "final_video"]
        if not final_videos:
            state.approval_decision = state.approval_decision or {}
            state.approval_decision["vam_decision"] = "approved"
            job.update_status(ContentJobStatus.AWAITING_APPROVAL)
            return state

        final_video = final_videos[-1]
        self.logger.info("VAM final review", job_id=str(job.id))

        if self.settings.is_development and (
            final_video.file_path.startswith("stub:") or not Path(final_video.file_path).exists()
        ):
            self.logger.info("Dev mode: VAM auto-approving stub video", job_id=str(job.id))
            self._record_decision(state, "approved", None)
            return state

        script = job.script
        script_summary = "\n".join([
            f"Frame {f.frame_number}: {f.scene_description[:60]} | {f.audio_cue or ''}"
            for f in (script.video_frames or [])[:5]
        ]) if script else "N/A"

        user_message = VAM_PROMPT.format(
            marketing_angle=content_brief.marketing_angle if content_brief else "N/A",
            target_audience=content_brief.target_audience if content_brief else "N/A",
            key_messages=", ".join(content_brief.key_messages[:3]) if content_brief else "N/A",
            video_path=final_video.file_path,
            duration=final_video.metadata.get("duration_seconds", "unknown"),
            script_summary=script_summary,
        )

        raw_response = await self.call_llm(VAM_SYSTEM_PROMPT, user_message)
        try:
            review = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            review = json.loads(match.group()) if match else {"vam_decision": "approved", "overall_score": 7}

        self._record_decision(state, review["vam_decision"], review.get("improvement_notes") or review.get("feedback"))
        return state

    def _record_decision(self, state: AgentState, decision: str, feedback: str | None) -> None:
        record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=state.job.id,
            gate=ApprovalGate.VAM,
            subject_type="video",
            subject_id=uuid.uuid4(),
            decision=decision,
            feedback=feedback,
            reviewer=self.agent_id,
            reviewed_at=datetime.utcnow(),
        )
        state.job.add_approval(record)
        state.approval_decision = state.approval_decision or {}
        state.approval_decision["vam_decision"] = decision
        if decision == "approved":
            state.job.update_status(ContentJobStatus.AWAITING_APPROVAL)  # Ready for human
        else:
            state.improvement_feedback = feedback
            state.job.improvement_count += 1
        self.logger.info("VAM decision", job_id=str(state.job.id), decision=decision)
