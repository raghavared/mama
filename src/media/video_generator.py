"""Video Generator — Veo-3, Kling, Render.io, and Remotion integrations."""
from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.base import AgentState, BaseAgent
from src.media.html_to_remotion import HTMLToRemotionGenerator
from src.media.remotion_renderer import RemotionRenderer
from src.models import MediaAsset, MediaSource, ContentJobStatus
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class VideoGeneratorOrchestrator(BaseAgent):
    """Orchestrates video frame generation across Veo-3, Kling, and Render.io."""

    agent_id = "module:video-generator"

    def __init__(self) -> None:
        super().__init__()
        self._storage = StorageClient()

    async def run(self, state: AgentState) -> AgentState:
        """Generate video clips from the video script frames."""
        job = state.job
        script = state.script or job.script

        if not script or not script.video_frames:
            self.logger.warning("No video frames to generate", job_id=str(job.id))
            return state

        job.update_status(ContentJobStatus.IN_PROGRESS)
        self.logger.info("Generating video frames", job_id=str(job.id), frame_count=len(script.video_frames))

        if not (self.settings.veo3_api_key or self.settings.kling_api_key):
            self.logger.warning("No video API keys configured, using stub video", job_id=str(state.job.id))
            return self._stub_video(state)

        tasks = []
        if self.settings.veo3_api_key:
            tasks.append(self._generate_veo3(job.id, script.video_frames))
        if self.settings.kling_api_key:
            tasks.append(self._generate_kling(job.id, script.video_frames))
        if self.settings.use_remotion:
            tasks.append(self._generate_remotion(job.id, script))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.error("Video generation error", error=str(result), job_id=str(job.id))
            elif result:
                job.add_asset(result)

        state.messages.append({"agent": self.agent_id, "action": "video_frames_generated"})
        return state

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=10, max=60))
    async def _generate_veo3(self, job_id: uuid.UUID, frames: list) -> MediaAsset | None:
        scene_text = "\n".join([
            f"Scene {f.frame_number} ({f.duration_seconds}s): {f.scene_description}"
            for f in frames[:5]
        ])
        total_duration = min(30, sum(f.duration_seconds for f in frames))

        async with httpx.AsyncClient(timeout=1800.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/veo-2.0-generate-001:predictLongRunning",
                headers={"x-goog-api-key": self.settings.veo3_api_key},
                json={
                    "instances": [{"prompt": scene_text}],
                    "parameters": {"aspectRatio": "9:16", "durationSeconds": total_duration},
                },
            )
            response.raise_for_status()
            operation = response.json()

        video_url = await self._poll_veo3(operation.get("name", ""))
        if not video_url:
            return None

        async with httpx.AsyncClient(timeout=120.0) as client:
            vid_resp = await client.get(video_url)
            vid_resp.raise_for_status()

        path = self._storage.save_bytes(vid_resp.content, f"{job_id}/video/veo3_{uuid.uuid4()}.mp4", "video/mp4")
        return MediaAsset(job_id=job_id, type="video_clip", source=MediaSource.VEO3.value,
                          file_path=path, format="mp4", metadata={"generator": "veo3"})

    async def _poll_veo3(self, op_name: str, max_wait: int = 1800) -> str | None:
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(30)
            waited += 30
            async with httpx.AsyncClient(timeout=30.0) as client:
                data = (await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/{op_name}",
                    headers={"x-goog-api-key": self.settings.veo3_api_key},
                )).json()
                if data.get("done"):
                    samples = data.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
                    return samples[0].get("video", {}).get("uri") if samples else None
        return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=10, max=60))
    async def _generate_kling(self, job_id: uuid.UUID, frames: list) -> MediaAsset | None:
        scene_text = " ".join([f.scene_description for f in frames[:3]])
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                "https://api.klingai.com/v1/videos/text2video",
                headers={"Authorization": f"Bearer {self.settings.kling_api_key}"},
                json={"prompt": scene_text, "model": "kling-v1", "duration": "5", "aspect_ratio": "9:16"},
            )
            resp.raise_for_status()
            task_id = resp.json().get("data", {}).get("task_id")

        if not task_id:
            return None
        video_url = await self._poll_kling(task_id)
        if not video_url:
            return None

        async with httpx.AsyncClient(timeout=120.0) as client:
            vid_resp = await client.get(video_url)
        path = self._storage.save_bytes(vid_resp.content, f"{job_id}/video/kling_{uuid.uuid4()}.mp4", "video/mp4")
        return MediaAsset(job_id=job_id, type="video_clip", source=MediaSource.KLING.value,
                          file_path=path, format="mp4", metadata={"generator": "kling"})

    async def _poll_kling(self, task_id: str, max_wait: int = 600) -> str | None:
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(15)
            waited += 15
            async with httpx.AsyncClient(timeout=30.0) as client:
                data = (await client.get(
                    f"https://api.klingai.com/v1/videos/text2video/{task_id}",
                    headers={"Authorization": f"Bearer {self.settings.kling_api_key}"},
                )).json()
                task_data = data.get("data", {})
                if task_data.get("task_status") == "succeed":
                    works = task_data.get("task_result", {}).get("videos", [])
                    return works[0].get("url") if works else None
        return None

    async def _generate_remotion(self, job_id: uuid.UUID, script) -> MediaAsset | None:
        """Render a video via Remotion CLI using LLM-generated composition props."""
        props_generator = HTMLToRemotionGenerator()
        props = await props_generator.generate_props(script)

        renderer = RemotionRenderer()
        storage_path = await renderer.render(
            job_id=job_id,
            composition=self.settings.remotion_composition,
            props=props,
            timeout=self.settings.video_generation_timeout_seconds,
        )

        if not storage_path:
            return None

        return MediaAsset(
            job_id=job_id,
            type="video_clip",
            source=MediaSource.REMOTION.value,
            file_path=storage_path,
            format="mp4",
            metadata={"generator": "remotion", "composition": self.settings.remotion_composition},
        )

    def _stub_video(self, state: AgentState) -> AgentState:
        for source in [MediaSource.VEO3, MediaSource.KLING]:
            state.job.add_asset(MediaAsset(
                job_id=state.job.id, type="video_clip", source=source.value,
                file_path=f"stub:video_{source.value}.mp4", format="mp4", metadata={"stub": True},
            ))
        self.logger.info("Stub video assets created", job_id=str(state.job.id))
        return state
