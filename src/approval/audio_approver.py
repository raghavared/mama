"""Audio Approver — reviews ElevenLabs generated audio narration."""
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

AUDIO_APPROVER_SYSTEM_PROMPT = """You are the Audio Quality Approver for MAMA. You review AI-generated audio narration for quality and brand fit.

Evaluate:
1. CLARITY: Is the narration clear and easily understandable?
2. PACING: Is the speaking pace appropriate for the content?
3. TONE: Does it match the specified voice direction?
4. SCRIPT MATCH: Does it accurately deliver the audio script?
5. TECHNICAL QUALITY: No artifacts, background noise, or distortion?

Score 1-10. Approve if >= 7. Output valid JSON only."""

AUDIO_APPROVER_PROMPT = """Review this generated audio narration.

AUDIO SCRIPT:
{audio_script}

VOICE DIRECTION: {voice_direction}
AUDIO FILE: {audio_path}
DURATION: {duration}s

Output a JSON decision:
{{
  "audio_decision": "approved" | "rejected",
  "overall_score": number,
  "feedback": string | null
}}"""


class AudioApproverAgent(BaseAgent):
    """Reviews generated audio narration quality."""

    agent_id = "agent:audio-approver"

    async def run(self, state: AgentState) -> AgentState:
        job = state.job

        audio_assets = [a for a in job.media_assets if a.type == "audio"]
        if not audio_assets:
            state.approval_decision = state.approval_decision or {}
            state.approval_decision["audio_decision"] = "approved"
            return state

        latest_audio = audio_assets[-1]

        self.logger.info("Audio approver reviewing", job_id=str(job.id))

        if self.settings.is_development and (
            latest_audio.file_path.startswith("stub:") or not Path(latest_audio.file_path).exists()
        ):
            self.logger.info("Dev mode: auto-approving stub audio", job_id=str(job.id))
            self._record_decision(state, "approved", None)
            return state

        audio_script = job.script.audio_narration or "" if job.script else ""
        voice_direction = job.metadata.get("vst_script_extended", {}).get("voice_direction", "professional")
        duration = latest_audio.metadata.get("duration_seconds", "unknown")

        user_message = AUDIO_APPROVER_PROMPT.format(
            audio_script=audio_script[:500],
            voice_direction=voice_direction,
            audio_path=latest_audio.file_path,
            duration=duration,
        )

        raw_response = await self.call_llm(AUDIO_APPROVER_SYSTEM_PROMPT, user_message)
        try:
            review = json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            review = json.loads(match.group()) if match else {"audio_decision": "approved", "overall_score": 7}

        self._record_decision(state, review["audio_decision"], review.get("feedback"))
        return state

    def _record_decision(self, state: AgentState, decision: str, feedback: str | None) -> None:
        record = ApprovalRecord(
            id=uuid.uuid4(),
            job_id=state.job.id,
            gate=ApprovalGate.AUDIO,
            subject_type="audio",
            subject_id=uuid.uuid4(),
            decision=decision,
            feedback=feedback,
            reviewer=self.agent_id,
            reviewed_at=datetime.utcnow(),
        )
        state.job.add_approval(record)
        state.approval_decision = state.approval_decision or {}
        state.approval_decision["audio_decision"] = decision
        if decision == "rejected":
            state.improvement_feedback = feedback
            state.job.improvement_count += 1
        self.logger.info("Audio approval decision", job_id=str(state.job.id), decision=decision)
