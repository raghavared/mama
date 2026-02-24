"""AV Merger — merges audio and video into final output."""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog

from src.agents.base import AgentState, BaseAgent
from src.models import MediaAsset, MediaSource, ContentJobStatus
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class AVMergerAgent(BaseAgent):
    """Merges approved audio and video into the final video asset."""

    agent_id = "module:av-merger"

    def __init__(self) -> None:
        super().__init__()
        self._storage = StorageClient()

    async def run(self, state: AgentState) -> AgentState:
        """Merge audio and video into final video."""
        job = state.job

        # Find latest assembled video clip and audio asset
        video_clips = [a for a in job.media_assets if a.type == "video_clip"]
        audio_assets = [a for a in job.media_assets if a.type == "audio"]

        if not video_clips:
            self.logger.warning("No video clips for AV merge", job_id=str(job.id))
            return state

        latest_video = video_clips[-1]
        latest_audio = audio_assets[-1] if audio_assets else None

        self.logger.info("Merging audio and video", job_id=str(job.id))

        # In development or when files are stubs, create stub final video
        if self.settings.is_development or latest_video.file_path.startswith("stub:"):
            return self._stub_final(state)

        if not latest_audio or latest_audio.file_path.startswith("stub:"):
            # No audio — just rename video as final
            final_asset = MediaAsset(
                job_id=job.id,
                type="final_video",
                source=MediaSource.MERGED.value,
                file_path=latest_video.file_path,
                format="mp4",
                metadata={"has_audio": False},
            )
            job.add_asset(final_asset)
            job.update_status(ContentJobStatus.AWAITING_APPROVAL)
            return state

        try:
            final_path = await self._merge(job.id, latest_video.file_path, latest_audio.file_path)
            audio_duration = latest_audio.metadata.get("duration_seconds", 0)
            final_asset = MediaAsset(
                job_id=job.id,
                type="final_video",
                source=MediaSource.MERGED.value,
                file_path=final_path,
                format="mp4",
                metadata={"has_audio": True, "duration_seconds": audio_duration},
            )
            job.add_asset(final_asset)
            job.update_status(ContentJobStatus.AWAITING_APPROVAL)
            state.messages.append({"agent": self.agent_id, "action": "av_merged"})
        except Exception as exc:
            self.logger.error("AV merge failed", job_id=str(job.id), error=str(exc))
            return self._stub_final(state)

        return state

    async def _merge(self, job_id: uuid.UUID, video_path: str, audio_path: str) -> str:
        """Use ffmpeg-python to merge audio and video."""
        try:
            import ffmpeg
        except ImportError:
            raise RuntimeError("ffmpeg-python not installed")

        output_path = self._storage.generate_path(job_id, "final", "mp4")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        video_stream = ffmpeg.input(video_path)
        audio_stream = ffmpeg.input(audio_path)
        (
            ffmpeg
            .output(video_stream, audio_stream, output_path, vcodec="copy", acodec="aac", shortest=None)
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path

    def _stub_final(self, state: AgentState) -> AgentState:
        asset = MediaAsset(
            job_id=state.job.id,
            type="final_video",
            source=MediaSource.MERGED.value,
            file_path="stub:final_video.mp4",
            format="mp4",
            metadata={"stub": True},
        )
        state.job.add_asset(asset)
        state.job.update_status(ContentJobStatus.AWAITING_APPROVAL)
        self.logger.info("Stub final video created", job_id=str(state.job.id))
        return state
