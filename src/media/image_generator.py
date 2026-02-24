"""Image Generator — DALL-E 3 and Gemini Imagen 3 integration for image post pipeline."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import httpx
import structlog
from google import genai
from google.genai import types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.base import AgentState, BaseAgent
from src.models import MediaAsset, MediaSource, ContentJobStatus
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class ImageGeneratorAgent(BaseAgent):
    """Generates images from script image_prompts using DALL-E 3 or Gemini Imagen 3."""

    agent_id = "module:image-generator"

    def __init__(self) -> None:
        super().__init__()
        self._storage = StorageClient()

    async def run(self, state: AgentState) -> AgentState:
        """Generate images from approved script prompts."""
        job = state.job
        script = state.script or job.script

        if not script or not script.image_prompts:
            self.logger.warning("No image prompts found in script", job_id=str(job.id))
            return state

        job.update_status(ContentJobStatus.IN_PROGRESS)
        self.logger.info("Generating images", job_id=str(job.id), prompt_count=len(script.image_prompts))

        provider = self.settings.image_generation_provider

        if provider == "gemini":
            has_key = bool(self.settings.gemini_api_key)
        else:
            has_key = bool(self.settings.openai_api_key)

        if not has_key:
            self.logger.warning("No API key for provider, using stub images", provider=provider, job_id=str(job.id))
            return self._stub_images(state, script.image_prompts)

        generated_assets = []
        for i, prompt in enumerate(script.image_prompts[:3]):
            try:
                if provider == "gemini":
                    asset = await self._generate_gemini(job.id, prompt, i)
                else:
                    asset = await self._generate_dalle(job.id, prompt, i)
                generated_assets.append(asset)
                job.add_asset(asset)
            except Exception as exc:
                self.logger.error("Image generation failed", job_id=str(job.id), prompt_idx=i, error=str(exc))

        state.messages.append({
            "agent": self.agent_id,
            "action": "images_generated",
            "count": len(generated_assets),
        })
        return state

    def _enhance_prompt(self, raw_prompt: str) -> str:
        """Append universal quality modifiers to ensure photorealistic, high-quality output.

        These modifiers work across both DALL-E 3 and Gemini Imagen 3.
        If the prompt already contains quality directives, they are not duplicated.
        """
        quality_tail = (
            "Photorealistic. Shot on a full-frame DSLR camera, 85mm prime lens, f/1.8 aperture. "
            "Professional three-point studio lighting with soft diffusers. "
            "8K resolution, ultra-sharp focus, fine detail in textures. "
            "Natural skin tones and authentic expressions where people are shown. "
            "Colour-graded with rich tones and slight cinematic grade. "
            "NOT an illustration, NOT AI art style, NOT cartoon. Looks like a real professional photograph."
        )
        # Avoid duplicating modifiers if the prompt already has them
        if "photorealistic" in raw_prompt.lower() or "8k" in raw_prompt.lower():
            return raw_prompt
        return f"{raw_prompt.rstrip('. ')}. {quality_tail}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    async def _generate_dalle(self, job_id: uuid.UUID, prompt: str, index: int) -> MediaAsset:
        """Call DALL-E 3 API to generate a high-quality image."""
        enhanced_prompt = self._enhance_prompt(prompt)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "dall-e-3",
                    "prompt": enhanced_prompt,
                    "n": 1,
                    "size": "1792x1024",   # highest resolution (landscape, great for social)
                    "quality": "hd",       # hd = 2x more detail than standard
                    "style": "natural",    # natural = photorealistic; "vivid" = hyper-real
                    "response_format": "url",
                },
            )
            response.raise_for_status()
            data = response.json()

        image_url = data["data"][0]["url"]
        revised_prompt = data["data"][0].get("revised_prompt", enhanced_prompt)
        async with httpx.AsyncClient(timeout=60.0) as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            image_data = img_response.content

        filename = f"{job_id}/images/dalle_{index}_{uuid.uuid4()}.png"
        storage_path = self._storage.save_bytes(image_data, filename, "image/png")

        return MediaAsset(
            job_id=job_id,
            type="image",
            source=MediaSource.DALLE.value,
            file_path=storage_path,
            format="png",
            metadata={
                "prompt": prompt[:200],
                "revised_prompt": revised_prompt[:400],
                "model": "dall-e-3",
                "quality": "hd",
                "size": "1792x1024",
            },
            quality_score=9.5,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    async def _generate_gemini(self, job_id: uuid.UUID, prompt: str, index: int) -> MediaAsset:
        """Call Gemini Imagen 3 API to generate a high-quality image."""
        api_key = self.settings.gemini_api_key
        model = self.settings.gemini_image_model
        enhanced_prompt = self._enhance_prompt(prompt)

        def _sync_generate() -> bytes:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_images(
                model=model,
                prompt=enhanced_prompt,
                config=genai_types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",   # JPEG for better colour fidelity
                    aspect_ratio="16:9",             # widescreen — best for social media
                    enhance_prompt=True,             # Gemini auto-refines prompt for quality
                    safety_filter_level="BLOCK_SOME",
                    person_generation="ALLOW_ADULT",
                ),
            )
            return response.generated_images[0].image.image_bytes

        image_data = await asyncio.to_thread(_sync_generate)

        filename = f"{job_id}/images/gemini_{index}_{uuid.uuid4()}.jpg"
        storage_path = self._storage.save_bytes(image_data, filename, "image/jpeg")

        return MediaAsset(
            job_id=job_id,
            type="image",
            source=MediaSource.GEMINI.value,
            file_path=storage_path,
            format="jpg",
            metadata={
                "prompt": prompt[:200],
                "model": model,
                "aspect_ratio": "16:9",
                "enhance_prompt": True,
            },
            quality_score=9.5,
        )

    def _stub_images(self, state: AgentState, prompts: list[str]) -> AgentState:
        """Return stub image assets for development."""
        provider = self.settings.image_generation_provider
        if provider == "gemini":
            source = MediaSource.GEMINI.value
        else:
            source = MediaSource.DALLE.value

        for i, prompt in enumerate(prompts[:3]):
            asset = MediaAsset(
                job_id=state.job.id,
                type="image",
                source=source,
                file_path=f"stub:image_{i}.png",
                format="png",
                metadata={"prompt": prompt[:100], "stub": True},
                quality_score=8.0,
            )
            state.job.add_asset(asset)
        self.logger.info("Stub images created", job_id=str(state.job.id))
        return state
