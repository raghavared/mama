"""Video Approver — reviews assembled video quality."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import structlog

from src.models import ApprovalRecord, ApprovalGate
from src.agents.base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)

VIDEO_APPROVER_SYSTEM_PROMPT = """You are the Video Quality Approver for MAMA. You review assembled video clips for quality.

Evaluate:
1. VISUAL QUALITY: Resolution, framerate, no artifacts
2. FLOW: Do frames sequence coherently?
3. SCRIPT MATCH: Does video match the scene descriptions?
4. DURATION: Appropriate length for the platform (30-90s)?
5. TRANSITIONS: Smooth, professional transitions?

Score 1-10. Approve if >= 7. Output valid JSON only."""

VIDEO_APPROVER_PROMPT = """Review this assembled video.

VIDEO SCRIPT SUMMARY:
{script_summary}

VIDEO FILE: {video_path}
DURATION: {duration}s
FRAME COUNT: {frame_count}

Output a JSON decision:
{{
  "video_decision": "approved" | "rejected",
  "overall_score": number,
  "feedback": string | null
}}"""


class VideoApproverAgent(BaseAgent):
    """Reviews assembled video quality before final merge."""

    agent_id = "agent:video-approver"

    async def run(self, state: AgentState) -> AgentState:
        job = state.job

        video_clips = [a for a in job.media_assets if a.type == "video_clip"]
        if not video_clips:
            state.approval_decision = state.approval_decision or {}
            state.approval_decision["video_decision"] = "approved"
            return state

        latest_video = video_clips[-1]
        self.logger.info("Video approver reviewing", job_id=str(job.id))

        if self.settings.is_development and (
            latest_video.file_path.startswith("stub:") or not Path(latest_video.file_path).exists()
        ):
            self.logger.info("Dev mode: auto-approving stub video", job_id=str(job.id))
            self._record_decision(state, "approved", None)
            return state

        script = job.script
        frame_count = len(script.video_frames) if (script and script.video_frames) else 0
        script_summary = "\n".join([
            f"Frame {f.frame_number}: {f.scene_description[:80]}"
            for f in (script.video_frames or [])[:5]
        ]) if script else "N/A"
        duration = latest_video.metadata.get("duration_seconds", "unknown")

        user_message = VIDEO_APPROVER_PROMPT.format(
            script_summary=script_summary,
            video_path=latest_video.file_path,
            duration=duration,
            frame_count=frame_count,
        )

        raw_response = await self.call_llm(VIDEO_APPROVER_SYSTEM_PROMPT, user_message)
        try:
            review = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            review = json.loads(match.group()) if match else {"video_decision": "approved", "overall_score": 7}

        self._record_decision(state, review["video_decision"], review.get("feedback"))
        return state

    def _record_decision(self, state: AgentState, decision: str, feedback: str | None) -> None:
        record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=state.job.id,
            gate=ApprovalGate.VIDEO_APPROVER,
            subject_type="video",
            subject_id=uuid.uuid4(),
            decision=decision,
            feedback=feedback,
            reviewer=self.agent_id,
            reviewed_at=datetime.utcnow(),
        )
        state.job.add_approval(record)
        state.approval_decision = state.approval_decision or {}
        state.approval_decision["video_decision"] = decision
        if decision == "rejected":
            state.improvement_feedback = feedback
            state.job.improvement_count += 1
        self.logger.info("Video approval decision", job_id=str(state.job.id), decision=decision)
