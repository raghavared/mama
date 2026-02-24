"""Unit tests for core domain models."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from src.models import (
    ContentJob,
    ContentBrief,
    Script,
    VideoFrame,
    MediaAsset,
    ApprovalRecord,
    ContentJobStatus,
    PipelineType,
    TopicSource,
    Platform,
    ApprovalGate,
    MediaSource,
)


def test_content_job_creation():
    job = ContentJob(
        topic="AI in marketing",
        topic_source=TopicSource.MANUAL,
    )
    assert job.id is not None
    assert job.status == ContentJobStatus.PENDING
    assert job.topic == "AI in marketing"
    assert job.topic_source == TopicSource.MANUAL
    assert job.media_assets == []
    assert job.approval_records == []


def test_content_job_status_update():
    job = ContentJob(topic="test", topic_source=TopicSource.MANUAL)
    original_updated_at = job.updated_at
    job.update_status(ContentJobStatus.IN_PROGRESS)
    assert job.status == ContentJobStatus.IN_PROGRESS
    assert job.updated_at >= original_updated_at


def test_content_job_add_approval():
    job = ContentJob(topic="test", topic_source=TopicSource.MANUAL)
    record = ApprovalRecord(
        job_id=job.id,
        gate=ApprovalGate.SCRIPT_CSA,
        subject_type="script",
        subject_id=uuid.uuid4(),
        decision="approved",
        reviewer="agent:csa",
    )
    job.add_approval(record)
    assert len(job.approval_records) == 1
    assert job.approval_records[0].decision == "approved"


def test_content_job_latest_approval():
    job = ContentJob(topic="test", topic_source=TopicSource.MANUAL)
    record1 = ApprovalRecord(
        job_id=job.id,
        gate=ApprovalGate.SCRIPT_CSA,
        subject_type="script",
        subject_id=uuid.uuid4(),
        decision="rejected",
        reviewer="agent:csa",
    )
    record2 = ApprovalRecord(
        job_id=job.id,
        gate=ApprovalGate.SCRIPT_CSA,
        subject_type="script",
        subject_id=uuid.uuid4(),
        decision="approved",
        reviewer="agent:csa",
    )
    job.add_approval(record1)
    job.add_approval(record2)

    latest = job.latest_approval(ApprovalGate.SCRIPT_CSA)
    assert latest is not None
    assert latest.decision == "approved"


def test_content_brief_creation():
    brief = ContentBrief(
        job_id=uuid.uuid4(),
        topic="AI Marketing",
        marketing_angle="Transform your business with AI",
        target_audience="B2B SaaS founders",
        tone="authoritative",
        key_messages=["AI increases ROI", "Easy integration"],
        platform_strategy={"instagram": "Visual storytelling", "linkedin": "Data-driven insights"},
    )
    assert brief.created_by == "agent:cmi"
    assert len(brief.key_messages) == 2


def test_script_image_creation():
    script = Script(
        job_id=uuid.uuid4(),
        type="image_script",
        content="Hook: Did you know AI can 10x your marketing ROI?\n\n...",
        image_prompts=["Futuristic AI robot in marketing office, professional, clean"],
        created_by="agent:cst",
        version=1,
    )
    assert script.version == 1
    assert len(script.image_prompts) == 1


def test_script_video_creation():
    frames = [
        VideoFrame(
            frame_number=1,
            scene_description="Close-up of laptop screen showing marketing dashboard",
            duration_seconds=4.0,
            transition_type="fade",
            audio_cue="AI is revolutionizing how marketers work.",
        )
    ]
    script = Script(
        job_id=uuid.uuid4(),
        type="video_script",
        content="Caption text here",
        video_frames=frames,
        audio_narration="AI is revolutionizing how marketers work.",
        created_by="agent:vst",
        version=1,
    )
    assert len(script.video_frames) == 1
    assert script.video_frames[0].frame_number == 1


def test_media_asset_creation():
    asset = MediaAsset(
        job_id=uuid.uuid4(),
        type="image",
        source=MediaSource.DALLE.value,
        file_path="/tmp/test.jpg",
        format="jpg",
        quality_score=8.5,
    )
    assert asset.id is not None
    assert asset.quality_score == 8.5


def test_pipeline_type_enum():
    assert PipelineType.IMAGE_POST.value == "image_post"
    assert PipelineType.VIDEO_POST.value == "video_post"


def test_topic_source_enum():
    assert TopicSource.MANUAL.value == "manual"
    assert TopicSource.TRENDING.value == "trending"
    assert TopicSource.SCHEDULED.value == "scheduled"
