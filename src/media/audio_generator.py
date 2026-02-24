"""Audio Generator — ElevenLabs TTS integration."""
from __future__ import annotations

import re
import uuid

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.base import AgentState, BaseAgent
from src.models import MediaAsset, MediaSource
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class AudioGeneratorAgent(BaseAgent):
    """Generates audio narration from video scripts using ElevenLabs TTS."""

    agent_id = "module:audio-generator"

    def __init__(self) -> None:
        super().__init__()
        self._storage = StorageClient()

    async def run(self, state: AgentState) -> AgentState:
        """Generate audio narration from the video script's audio_narration field."""
        job = state.job
        script = state.script or job.script

        if not script or not script.audio_narration:
            self.logger.warning("No audio narration text found", job_id=str(job.id))
            return state

        self.logger.info("Generating audio narration", job_id=str(job.id))

        if not self.settings.elevenlabs_api_key:
            return self._stub_audio(state, script.audio_narration)

        try:
            asset = await self._generate_elevenlabs(job.id, script.audio_narration)
            job.add_asset(asset)
            state.messages.append({"agent": self.agent_id, "action": "audio_generated"})
        except Exception as exc:
            self.logger.error("Audio generation failed", job_id=str(job.id), error=str(exc))
            # Fall back to stub in case of error
            return self._stub_audio(state, script.audio_narration)

        return state

    def _process_narration(self, text: str) -> str:
        """Replace [PAUSE] markers with ElevenLabs SSML break tags."""
        text = re.sub(r'\[PAUSE\]', '<break time="0.8s"/>', text)
        text = re.sub(r'\[LONG PAUSE\]', '<break time="1.5s"/>', text)
        text = re.sub(r'\[SHORT PAUSE\]', '<break time="0.4s"/>', text)
        return text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    async def _generate_elevenlabs(self, job_id: uuid.UUID, narration_text: str) -> MediaAsset:
        """Call ElevenLabs TTS API to generate audio."""
        voice_id = self.settings.elevenlabs_voice_id
        processed_text = self._process_narration(narration_text)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": processed_text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.45,           # Slightly lower for more natural variation
                        "similarity_boost": 0.82,    # Higher — preserve voice identity strongly
                        "style": 0.35,               # Subtle style expressiveness
                        "use_speaker_boost": True,   # Always on for clarity
                    },
                    "optimize_streaming_latency": 0,
                },
            )
            response.raise_for_status()
            audio_data = response.content

        filename = f"{job_id}/audio/narration_{uuid.uuid4()}.mp3"
        storage_path = self._storage.save_bytes(audio_data, filename, "audio/mpeg")

        # Estimate duration: ~130 words per minute (professional narration pace with pauses)
        word_count = len(narration_text.split())
        estimated_duration = (word_count / 130) * 60

        return MediaAsset(
            job_id=job_id,
            type="audio",
            source=MediaSource.ELEVENLABS.value,
            file_path=storage_path,
            format="mp3",
            metadata={
                "voice_id": voice_id,
                "model": "eleven_multilingual_v2",
                "text_length": len(narration_text),
                "word_count": len(narration_text.split()),
                "duration_seconds": estimated_duration,
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.82, "style": 0.35},
            },
        )

    def _stub_audio(self, state: AgentState, narration_text: str) -> AgentState:
        """Create stub audio asset for development."""
        word_count = len(narration_text.split())
        estimated_duration = (word_count / 130) * 60

        asset = MediaAsset(
            job_id=state.job.id,
            type="audio",
            source=MediaSource.ELEVENLABS.value,
            file_path=f"stub:audio_narration.mp3",
            format="mp3",
            metadata={"stub": True, "duration_seconds": estimated_duration},
        )
        state.job.add_asset(asset)
        self.logger.info("Stub audio created", job_id=str(state.job.id), duration=estimated_duration)
        return state
