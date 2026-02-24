"""Unified storage client — local filesystem in dev, S3 in prod."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class StorageClient:
    """Handles media file storage. Uses local filesystem in dev, S3 in production."""

    def __init__(self) -> None:
        self.settings = get_settings()
        if self.settings.use_local_storage:
            self._storage_root = Path(self.settings.local_storage_path)
            self._storage_root.mkdir(parents=True, exist_ok=True)
        else:
            import boto3
            from botocore.config import Config
            self._s3 = boto3.client(
                "s3",
                region_name=self.settings.s3_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                config=Config(s3={"addressing_style": "path"}),
            )

    def save_bytes(self, data: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        """Save bytes to storage and return the storage path."""
        if self.settings.use_local_storage:
            path = self._storage_root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            storage_path = str(path)
        else:
            key = f"media/{filename}"
            self._s3.put_object(
                Bucket=self.settings.s3_bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            storage_path = self._public_url(key)

        logger.info("File saved", path=storage_path, size=len(data))
        return storage_path

    def save_file(self, local_path: str, remote_filename: str) -> str:
        """Upload a local file to storage and return the storage path."""
        with open(local_path, "rb") as f:
            data = f.read()
        return self.save_bytes(data, remote_filename)

    def generate_path(self, job_id: uuid.UUID, asset_type: str, extension: str) -> str:
        """Generate a unique storage path for a media asset."""
        filename = f"{job_id}/{asset_type}/{uuid.uuid4()}.{extension}"
        if self.settings.use_local_storage:
            return str(self._storage_root / filename)
        return self._public_url(f"media/{filename}")

    def get_public_url(self, storage_path: str) -> str:
        """Get a publicly accessible URL for a stored file."""
        if self.settings.use_local_storage:
            return f"file://{storage_path}"
        if storage_path.startswith("s3://"):
            key = storage_path.replace(f"s3://{self.settings.s3_bucket_name}/", "")
            return self._public_url(key)
        return storage_path

    def _public_url(self, key: str) -> str:
        """Build the public URL for an S3 key.

        Uses CDN domain when configured (avoids TLS issues with dot-bucket names),
        otherwise falls back to path-style S3 URL.
        """
        if self.settings.cdn_domain:
            return f"https://{self.settings.cdn_domain}/{key}"
        # Path-style URL — safe for bucket names that contain dots
        return (
            f"https://s3.{self.settings.s3_region}.amazonaws.com"
            f"/{self.settings.s3_bucket_name}/{key}"
        )
