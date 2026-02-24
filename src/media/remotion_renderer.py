"""Remotion video renderer — renders React compositions to MP4 via Remotion CLI."""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import uuid
from pathlib import Path

import structlog

from src.config import get_settings
from src.utils.storage import StorageClient

logger = structlog.get_logger(__name__)


class RemotionRenderer:
    """Renders Remotion React compositions to MP4 using the Remotion CLI."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._storage = StorageClient()
        self._remotion_path = Path(self.settings.remotion_project_path).resolve()
        self._entry_point = self._remotion_path / "src" / "index.ts"

    def is_available(self) -> bool:
        """Check if Remotion CLI and project are available."""
        return (
            shutil.which("npx") is not None
            and self._remotion_path.exists()
            and self._entry_point.exists()
        )

    async def render(
        self,
        job_id: uuid.UUID,
        composition: str,
        props: dict,
        timeout: int = 300,
    ) -> str | None:
        """Render a Remotion composition to MP4. Returns storage path or None."""
        if not self.is_available():
            logger.warning(
                "Remotion not available, skipping render",
                remotion_path=str(self._remotion_path),
                entry_point=str(self._entry_point),
            )
            return None

        output_dir = Path(self.settings.local_storage_path) / str(job_id) / "video"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"remotion_{uuid.uuid4()}.mp4"

        cmd = [
            "npx",
            "remotion",
            "render",
            str(self._entry_point),
            composition,
            str(output_path),
            "--props",
            json.dumps(props),
        ]

        logger.info(
            "Starting Remotion render",
            composition=composition,
            job_id=str(job_id),
            output=str(output_path),
        )
        start = time.monotonic()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self._remotion_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            logger.error(
                "Remotion render timed out",
                timeout=timeout,
                job_id=str(job_id),
            )
            return None

        duration = time.monotonic() - start

        if proc.returncode != 0:
            logger.error(
                "Remotion render failed",
                returncode=proc.returncode,
                stderr=stderr.decode()[:500],
                job_id=str(job_id),
            )
            return None

        logger.info(
            "Remotion render complete",
            duration_seconds=round(duration, 2),
            job_id=str(job_id),
        )

        if output_path.exists():
            storage_path = self._storage.save_file(
                str(output_path),
                f"{job_id}/video/{output_path.name}",
            )
            return storage_path

        logger.error(
            "Remotion output file not found after render",
            output_path=str(output_path),
            job_id=str(job_id),
        )
        return None
