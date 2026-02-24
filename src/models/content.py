"""Core domain models for the MAMA content pipeline."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContentJobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPROVING = "improving"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class PipelineType(str, Enum):
    IMAGE_POST = "image_post"
    VIDEO_POST = "video_post"


class TopicSource(str, Enum):
    TRENDING = "trending"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    X_TWITTER = "x_twitter"
    YOUTUBE = "youtube"


class MediaSource(str, Enum):
    DALLE = "dalle"
    STABLE_DIFFUSION = "stable_diffusion"
    GEMINI = "gemini"
    VEO3 = "veo3"
    KLING = "kling"
    RENDERIO = "renderio"
    REMOTION = "remotion"
    ELEVENLABS = "elevenlabs"
    MERGED = "merged"


class ApprovalGate(str, Enum):
    SCRIPT_CSA = "script_csa"
    IMAGE_CMI_CST = "image_cmi_cst"
    AUDIO = "audio"
    VIDEO_APPROVER = "video_approver"
    VAM = "vam"
    HUMAN = "human"


class ContentBrief(BaseModel):
    """Output from CMI agent — the marketing strategy for a topic."""

    job_id: uuid.UUID
    topic: str
    marketing_angle: str
    target_audience: str
    tone: str
    key_messages: list[str]
    platform_strategy: dict[str, str]
    created_by: str = "agent:cmi"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoFrame(BaseModel):
    """A single frame in a video script."""

    frame_number: int
    scene_description: str
    duration_seconds: float
    transition_type: Optional[str] = None
    audio_cue: Optional[str] = None


class Script(BaseModel):
    """Script output from CST or VST agents."""

    job_id: uuid.UUID
    type: str  # "image_script" or "video_script"
    content: str
    image_prompts: Optional[list[str]] = None
    video_frames: Optional[list[VideoFrame]] = None
    audio_narration: Optional[str] = None
    created_by: str  # "agent:cst" or "agent:vst"
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAsset(BaseModel):
    """A generated media asset (image, video clip, audio, or final video)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID
    type: str  # "image", "video_clip", "audio", "final_video"
    source: str  # MediaSource value
    file_path: str
    format: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalRecord(BaseModel):
    """Records an approval/rejection decision at a specific gate."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID
    gate: ApprovalGate
    subject_type: str  # "script", "image", "audio", "video"
    subject_id: uuid.UUID
    decision: str  # "approved" or "rejected"
    feedback: Optional[str] = None
    reviewer: str
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class PostAnalytics(BaseModel):
    """Analytics data for a published post."""

    post_id: uuid.UUID
    platform: str
    impressions: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    clicks: int = 0
    reach: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PublishedPost(BaseModel):
    """A post that has been published to a social platform."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID
    platform: Platform
    platform_post_id: str
    post_url: str
    posted_at: datetime = Field(default_factory=datetime.utcnow)
    analytics: Optional[PostAnalytics] = None


class ContentJob(BaseModel):
    """The central domain object tracking a content piece from topic to published post."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: Optional[str] = None
    description: Optional[str] = None
    topic: str
    topic_source: TopicSource
    pipeline_type: Optional[PipelineType] = None  # Set by Decision Maker
    status: ContentJobStatus = ContentJobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    content_brief: Optional[ContentBrief] = None
    script: Optional[Script] = None
    media_assets: list[MediaAsset] = Field(default_factory=list)
    approval_records: list[ApprovalRecord] = Field(default_factory=list)
    published_posts: list[PublishedPost] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    improvement_count: int = 0

    def update_status(self, new_status: ContentJobStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def add_approval(self, record: ApprovalRecord) -> None:
        self.approval_records.append(record)
        self.updated_at = datetime.utcnow()

    def add_asset(self, asset: MediaAsset) -> None:
        self.media_assets.append(asset)
        self.updated_at = datetime.utcnow()

    def latest_approval(self, gate: ApprovalGate) -> Optional[ApprovalRecord]:
        records = [r for r in self.approval_records if r.gate == gate]
        return max(records, key=lambda r: r.reviewed_at) if records else None
