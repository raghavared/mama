"""Script Separator — splits video scripts into video and audio tracks."""
from __future__ import annotations

import structlog

from src.agents.base import AgentState, BaseAgent

logger = structlog.get_logger(__name__)


class ScriptSeparatorModule(BaseAgent):
    """Separates an approved video script into video frames and audio narration."""

    agent_id = "module:script-separator"

    async def run(self, state: AgentState) -> AgentState:
        """Parse the video script into separate video and audio components."""
        job = state.job
        script = state.script or job.script

        if not script or script.type != "video_script":
            self.logger.warning("Script separator expects video_script", job_id=str(job.id))
            return state

        self.logger.info(
            "Separating video script",
            job_id=str(job.id),
            frame_count=len(script.video_frames or []),
        )

        # Extract audio narration from frames if not already set
        if script.video_frames and not script.audio_narration:
            audio_parts = [f.audio_cue for f in script.video_frames if f.audio_cue]
            script.audio_narration = " ".join(audio_parts)

        job.metadata["separated_tracks"] = {
            "video_frame_count": len(script.video_frames or []),
            "audio_narration_length": len(script.audio_narration or ""),
        }

        state.messages.append({
            "agent": self.agent_id,
            "action": "script_separated",
            "frame_count": len(script.video_frames or []),
            "has_audio": bool(script.audio_narration),
        })
        return state
