"""Frame Combiner — assembles multi-source video frames into a single video."""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog

from src.agents.base import AgentState, BaseAgent
from src.models import MediaAsset, MediaSource
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class FrameCombinerAgent(BaseAgent):
    """Combines video clips from Veo-3, Kling, and Render.io into one assembled video."""

    agent_id = "module:frame-combiner"

    def __init__(self) -> None:
        super().__init__()
        self._storage = StorageClient()

    async def run(self, state: AgentState) -> AgentState:
        """Combine all video clips into a single assembled video."""
        job = state.job
        video_clips = [a for a in job.media_assets if a.type == "video_clip"]

        if not video_clips:
            self.logger.warning("No video clips to combine", job_id=str(job.id))
            return state

        self.logger.info("Combining video frames", job_id=str(job.id), clip_count=len(video_clips))

        # In development mode or when clip files are stubs, create a stub combined video
        real_clips = [c for c in video_clips if not c.file_path.startswith("stub:") and Path(c.file_path).exists()]

        if not real_clips:
            return self._stub_combined(state)

        try:
            combined_path = await self._combine_clips(job.id, real_clips)
            asset = MediaAsset(
                job_id=job.id,
                type="video_clip",
                source=MediaSource.MERGED.value,
                file_path=combined_path,
                format="mp4",
                metadata={"combined_from": [c.source for c in real_clips], "clip_count": len(real_clips)},
            )
            job.add_asset(asset)
            state.messages.append({"agent": self.agent_id, "action": "frames_combined", "clip_count": len(real_clips)})
        except Exception as exc:
            self.logger.error("Frame combine failed", job_id=str(job.id), error=str(exc))
            return self._stub_combined(state)

        return state

    async def _combine_clips(self, job_id: uuid.UUID, clips: list[MediaAsset]) -> str:
        """Use moviepy to concatenate video clips."""
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
        except ImportError:
            raise RuntimeError("moviepy not installed — cannot combine video clips")

        loaded_clips = []
        try:
            for clip in clips:
                loaded_clips.append(VideoFileClip(clip.file_path))

            final_clip = concatenate_videoclips(loaded_clips, method="compose")
            output_path = self._storage.generate_path(job_id, "video", "mp4")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
            return output_path
        finally:
            for c in loaded_clips:
                c.close()

    def _stub_combined(self, state: AgentState) -> AgentState:
        asset = MediaAsset(
            job_id=state.job.id,
            type="video_clip",
            source=MediaSource.MERGED.value,
            file_path=f"stub:combined_video.mp4",
            format="mp4",
            metadata={"stub": True},
        )
        state.job.add_asset(asset)
        self.logger.info("Stub combined video created", job_id=str(state.job.id))
        return state
