# MAMA System Architecture
## Marketing Agent Multi-Agent Architecture

**Version**: 1.0.0 (Initial Draft)
**Date**: 2026-02-19
**Status**: Living Document — Updated as domain research is integrated

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Agent Roster & Responsibilities](#3-agent-roster--responsibilities)
4. [Pipeline Flows](#4-pipeline-flows)
   - 4.1 [Image Post Pipeline](#41-image-post-pipeline)
   - 4.2 [Video Post Pipeline](#42-video-post-pipeline)
5. [Workflow State Machine](#5-workflow-state-machine)
6. [Shared Data Models](#6-shared-data-models)
7. [Inter-Agent Communication Protocol](#7-inter-agent-communication-protocol)
8. [API Contracts Between Modules](#8-api-contracts-between-modules)
9. [Technology Stack](#9-technology-stack)
10. [Infrastructure & Deployment Architecture](#10-infrastructure--deployment-architecture)
11. [Security & Configuration Management](#11-security--configuration-management)
12. [Phase 1 & 2 Breakdown](#12-phase-1--2-breakdown)

---

## 1. System Overview

MAMA is an AI-powered marketing automation platform built on a multi-agent orchestration model. It transforms a topic (trending, manual, or auto-generated) into finished, published social media content through a sequence of specialized AI coordinator agents, each with defined skills and responsibilities.

**Two Content Pipelines:**
- **Image Post Pipeline**: Topic → Idea → Script → Image → Approval → Publish (Instagram, LinkedIn, Facebook)
- **Video Post Pipeline**: Topic → Idea → Script → Video+Audio → Merge → Approval → Publish (Instagram, LinkedIn, X, YouTube, Facebook)

**Core Principles:**
- Every content piece passes through human or AI approval gates before publishing
- Each agent has a single, well-defined responsibility
- All state is persisted — pipelines are resumable after failure
- Media generation is multi-source (Veo-3 + Kling + Render.io combined)
- All publishing events are tracked for analytics

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MAMA SYSTEM                                        │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────────────────────┐ │
│  │   TRIGGERS   │   │  ORCHESTRATION│   │      CONTENT PIPELINES          │ │
│  │              │   │  LAYER       │   │                                 │ │
│  │ • Trending   │──▶│              │   │  ┌─────────────┐  ┌──────────┐ │ │
│  │ • Manual API │   │ MAMA         │──▶│  │ IMAGE POST  │  │VIDEO POST│ │ │
│  │ • Scheduler  │   │ (Entry Point)│   │  │  PIPELINE   │  │ PIPELINE │ │ │
│  └──────────────┘   │              │   │  └─────────────┘  └──────────┘ │ │
│                     │ CMI          │   │                                 │ │
│                     │ (Ideator)    │   └─────────────────────────────────┘ │
│                     │              │                                        │
│                     │ Decision     │   ┌─────────────────────────────────┐ │
│                     │ Maker        │   │      APPROVAL LAYER             │ │
│                     └──────────────┘   │  CSA → Image/Video → VAM → Human│ │
│                                        └─────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     MEDIA GENERATION ENGINE                          │  │
│  │  DALL-E/SD (images) │ Veo-3 │ Kling │ Render.io │ ElevenLabs        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     PUBLISHING LAYER                                 │  │
│  │  Instagram │ LinkedIn │ Facebook │ X/Twitter │ YouTube               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     DATA & INFRASTRUCTURE                            │  │
│  │  PostgreSQL │ Redis │ S3/GCS │ Celery/RabbitMQ │ Grafana/Prometheus  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Roster & Responsibilities

| Agent | ID | Type | Skills | Responsibility |
|---|---|---|---|---|
| **MAMA** | `agent:mama` | Orchestrator | orchestration | Entry point; triggers content generation; routes to CMI |
| **CMI** | `agent:cmi` | Coordinator | marketing-ideas, social-content, marketing-psychology | Generates content ideas & marketing strategy |
| **Decision Maker** | `module:decision-maker` | Logic Module | — | Decides Image Post vs. Video Post based on content type |
| **CST** | `agent:cst` | Coordinator | story-collaborator, social-content, story-idea-generator | Image post script & story generation |
| **VST** | `agent:vst` | Coordinator | story-collaborator, social-content, story-idea-generator | Video post script (frame-by-frame, with audio cues) |
| **CSA** | `agent:csa` | Approver | script-review, quality-check | Script approval/rejection/improvement routing |
| **Audio Approver** | `agent:audio-approver` | Approver | audio-quality-check | Audio narration quality review |
| **Video Approver** | `agent:video-approver` | Approver | video-quality-check | Assembled video quality review |
| **VAM** | `agent:vam` | Final Approver | VST skills + CSA skills | Final video approval before human review |

---

## 4. Pipeline Flows

### 4.1 Image Post Pipeline

```
MAMA
  │
  ▼
[Topic Input: trending / manual / scheduled]
  │
  ▼
CMI Agent
  │ Generates: marketing ideas, social content strategy, content brief
  ▼
Decision Maker
  │ Decision: IMAGE POST
  ▼
CST Agent (Image Path)
  │ Generates: story-driven script + image prompt
  ▼
CSA Script Approval ◄──────────────────────────────┐
  │                                                  │
  ├─[APPROVED]─▶ Image Generation (DALL-E / SD)      │
  │               │                                  │
  │               ▼                                  │
  │           Image Approval (CMI + CST dual review) │
  │               │                                  │
  │               ├─[APPROVED]                        │
  │               │    ▼                              │
  │               │  Publish to Instagram/LinkedIn/FB │
  │               │    ▼                              │
  │               │  Update System & Sheet            │
  │               │                                  │
  │               └─[REJECTED]──▶ Image Improvement ─┘
  │
  └─[REJECTED]──▶ Script Improvement ──────────────────▶ CST (re-generate)
```

### 4.2 Video Post Pipeline

```
MAMA → CMI → Decision Maker
  │ Decision: VIDEO POST
  ▼
VST Agent (Video Path)
  │ Generates: frame-by-frame video + audio script
  ▼
CSA Script Approval ◄──────────────────────────────────────┐
  │                                                          │
  ├─[APPROVED]─▶ Video & Audio Script Separator              │
  │               │                                          │
  │               ├─[VIDEO SCRIPT]─────────────────────────┐ │
  │               │   ├─▶ Veo-3 → Group of Frames          │ │
  │               │   ├─▶ Kling → Group of Frames          │ │
  │               │   └─▶ Render.io:                       │ │
  │               │         Code Plan → Plan Review        │ │
  │               │         Code Write → Render → Frames   │ │
  │               │                  ↓                     │ │
  │               │         Frame Combine Engine           │ │
  │               │                  ↓                     │ │
  │               │         Video Quality Checker          │ │
  │               │                  ↓                     │ │
  │               │         Video Approver ◄───────────────┘ │
  │               │                  │                        │
  │               └─[AUDIO SCRIPT]   │                        │
  │                   │              │                        │
  │                   ▼              │                        │
  │              ElevenLabs TTS      │                        │
  │                   │              │                        │
  │                   ▼              │                        │
  │              Audio Approver ◄────┼───[IMPROVE AUDIO]      │
  │                   │[APPROVED]    │                        │
  │                   └──────────────┤                        │
  │                                  ▼                        │
  │                         Audio + Video Merger              │
  │                                  │                        │
  │                                  ▼                        │
  │                         VAM Final Approval                │
  │                                  │                        │
  │                                  ▼                        │
  │                         Human-in-the-Loop Review          │
  │                                  │                        │
  │                         ├─[APPROVED]─▶ Publish to all     │
  │                         │              platforms           │
  │                         │              ▼                  │
  │                         │           Update System & Sheet │
  │                         │                                 │
  │                         └─[REJECTED]──▶ Improvement ──────┘
  │
  └─[REJECTED]──▶ Script Improvement ──────────────────────────▶ VST
```

---

## 5. Workflow State Machine

### Content Job States
```
PENDING ──▶ IN_PROGRESS ──▶ AWAITING_APPROVAL ──▶ APPROVED ──▶ PUBLISHING ──▶ PUBLISHED
                │                    │                │
                ▼                    ▼                │
             FAILED              REJECTED             │
                                    │                 │
                                    ▼                 │
                              IMPROVING ──────────────┘
                                    │
                                    ▼
                              (loops back to IN_PROGRESS)
```

### State Definitions
| State | Description | Next States |
|---|---|---|
| `PENDING` | Job created, not yet started | `IN_PROGRESS` |
| `IN_PROGRESS` | Agent actively working | `AWAITING_APPROVAL`, `FAILED` |
| `AWAITING_APPROVAL` | Waiting for approval gate | `APPROVED`, `REJECTED` |
| `APPROVED` | Passed approval gate | `PUBLISHING` or next `IN_PROGRESS` |
| `REJECTED` | Failed approval, needs improvement | `IMPROVING` |
| `IMPROVING` | Regenerating based on feedback | `AWAITING_APPROVAL` |
| `PUBLISHING` | Being sent to social platforms | `PUBLISHED`, `FAILED` |
| `PUBLISHED` | Successfully posted | Terminal |
| `FAILED` | Unrecoverable error | Terminal (with alert) |

### Approval Gate States
```
WAITING ──▶ REVIEWING ──▶ APPROVED
                │
                └──▶ REJECTED_WITH_FEEDBACK ──▶ (trigger improvement)
```

---

## 6. Shared Data Models

### ContentJob
```python
class ContentJob:
    id: UUID                          # Unique job identifier
    topic: str                        # Input topic
    topic_source: Literal["trending", "manual", "scheduled"]
    pipeline_type: Literal["image_post", "video_post"]  # Set by Decision Maker
    status: ContentJobStatus          # Current state
    created_at: datetime
    updated_at: datetime
    content_brief: ContentBrief       # Output from CMI
    script: Script                    # Output from CST/VST
    media_assets: List[MediaAsset]    # Images/video/audio
    approval_records: List[ApprovalRecord]
    published_posts: List[PublishedPost]
    metadata: Dict[str, Any]
```

### ContentBrief
```python
class ContentBrief:
    job_id: UUID
    topic: str
    marketing_angle: str
    target_audience: str
    tone: str
    key_messages: List[str]
    platform_strategy: Dict[str, str]  # per-platform guidance
    created_by: str                    # "agent:cmi"
    created_at: datetime
```

### Script
```python
class Script:
    job_id: UUID
    type: Literal["image_script", "video_script"]
    content: str                       # Full script text
    image_prompts: Optional[List[str]] # For image pipeline
    video_frames: Optional[List[VideoFrame]]  # For video pipeline
    audio_narration: Optional[str]     # Extracted audio script
    created_by: str                    # "agent:cst" or "agent:vst"
    version: int                       # Increments on each improvement
    created_at: datetime
```

### VideoFrame
```python
class VideoFrame:
    frame_number: int
    scene_description: str             # Visual cue for video gen
    duration_seconds: float
    transition_type: Optional[str]
    audio_cue: Optional[str]           # Corresponding narration segment
```

### MediaAsset
```python
class MediaAsset:
    id: UUID
    job_id: UUID
    type: Literal["image", "video_clip", "audio", "final_video"]
    source: str                        # "dalle", "veo3", "kling", "renderio", "elevenlabs", "merged"
    file_path: str                     # S3/GCS path
    format: str                        # jpg, mp4, mp3, etc.
    metadata: Dict[str, Any]           # resolution, duration, size, etc.
    quality_score: Optional[float]
    created_at: datetime
```

### ApprovalRecord
```python
class ApprovalRecord:
    id: UUID
    job_id: UUID
    gate: Literal["script_csa", "image_cmi_cst", "audio", "video_approver", "vam", "human"]
    subject_type: str                  # "script", "image", "audio", "video"
    subject_id: UUID                   # ID of the asset being approved
    decision: Literal["approved", "rejected"]
    feedback: Optional[str]            # Improvement instructions if rejected
    reviewer: str                      # agent ID or human user ID
    reviewed_at: datetime
```

### PublishedPost
```python
class PublishedPost:
    id: UUID
    job_id: UUID
    platform: Literal["instagram", "linkedin", "facebook", "x_twitter", "youtube"]
    platform_post_id: str              # Platform's own post ID
    post_url: str
    posted_at: datetime
    analytics: PostAnalytics           # Updated periodically
```

### PostAnalytics
```python
class PostAnalytics:
    post_id: UUID
    platform: str
    impressions: int
    likes: int
    shares: int
    comments: int
    clicks: int
    reach: int
    updated_at: datetime
```

---

## 7. Inter-Agent Communication Protocol

### Message Envelope
All agent-to-agent messages use this standard envelope:

```json
{
  "message_id": "msg_uuid_here",
  "correlation_id": "job_uuid_here",
  "from_agent": "agent:mama",
  "to_agent": "agent:cmi",
  "message_type": "TASK_REQUEST",
  "payload": { ... },
  "timestamp": "2026-02-19T10:00:00Z",
  "retry_count": 0,
  "timeout_seconds": 300
}
```

### Message Types
| Type | Direction | Description |
|---|---|---|
| `TASK_REQUEST` | Coordinator → Worker | Request to perform a task |
| `TASK_RESULT` | Worker → Coordinator | Task completed with output |
| `APPROVAL_REQUEST` | Generator → Approver | Submit artifact for review |
| `APPROVAL_DECISION` | Approver → Coordinator | Decision with optional feedback |
| `IMPROVEMENT_REQUEST` | Coordinator → Generator | Request improvement with feedback |
| `PIPELINE_ROUTE` | Decision Maker → Pipeline | Route job to image or video pipeline |
| `PUBLISH_REQUEST` | Pipeline → Publisher | Send content to publishing module |
| `STATUS_UPDATE` | Any → Orchestrator | Progress notification |
| `ERROR_ALERT` | Any → Orchestrator | Error reporting |

### Event Topics (Queue)
```
mama.jobs.created          - New content job created
mama.jobs.routed           - Decision maker chose pipeline type
mama.pipeline.image.*      - All image pipeline events
mama.pipeline.video.*      - All video pipeline events
mama.approval.*            - All approval events
mama.publishing.*          - All publishing events
mama.analytics.*           - Analytics update events
```

---

## 8. API Contracts Between Modules

### MAMA → CMI
```
POST /agents/cmi/ideate
Body: { job_id, topic, topic_source }
Response: { content_brief }
```

### CMI → Decision Maker
```
POST /modules/decision-maker/route
Body: { job_id, content_brief }
Response: { pipeline_type: "image_post" | "video_post" }
```

### Decision Maker → CST/VST
```
POST /agents/cst/generate-script     (image path)
POST /agents/vst/generate-script     (video path)
Body: { job_id, content_brief }
Response: { script }
```

### CST/VST → CSA
```
POST /agents/csa/review-script
Body: { job_id, script, context: content_brief }
Response: { decision: "approved"|"rejected", feedback? }
```

### Script Separator (video path)
```
POST /modules/script-separator/separate
Body: { job_id, script }
Response: { video_script: [...frames], audio_script: string }
```

### Video Generation
```
POST /media/veo3/generate      Body: { job_id, frames }  Response: { frames_path }
POST /media/kling/generate     Body: { job_id, frames }  Response: { frames_path }
POST /media/renderio/render    Body: { job_id, frames }  Response: { frames_path }
```

### Frame Combine Engine
```
POST /media/frame-combine/assemble
Body: { job_id, veo3_frames, kling_frames, renderio_frames, sequence_order }
Response: { assembled_video_path }
```

### Audio Generation
```
POST /media/elevenlabs/generate
Body: { job_id, audio_script, voice_config }
Response: { audio_path, duration_seconds }
```

### Audio-Video Merger
```
POST /media/merger/merge
Body: { job_id, video_path, audio_path }
Response: { final_video_path }
```

### Publishing
```
POST /publish/post
Body: { job_id, content_type, asset_path, caption, platforms: [...], schedule? }
Response: { published_posts: [...] }
```

---

## 9. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Ecosystem for AI/ML, async support |
| **Agent Framework** | TBD (LangGraph / CrewAI / Custom) | See AGENT_FRAMEWORK.md when complete |
| **LLM Provider** | Claude API (Anthropic) | claude-sonnet-4-6 for all agent reasoning |
| **Image Generation** | DALL-E 3 / Stable Diffusion API | Quality + accessibility |
| **Video Generation** | Veo-3 API + Kling AI | Multi-source for quality |
| **Programmatic Video** | Render.io / Remotion | Code-based rendering for precise control |
| **Audio Generation** | ElevenLabs API | High-quality TTS with voice control |
| **Database** | PostgreSQL | Structured data, workflow state |
| **Cache / Queue State** | Redis | Fast state access, job queue |
| **Message Queue** | Celery + RabbitMQ | Async task processing |
| **Asset Storage** | AWS S3 / GCS | Media file storage |
| **API Layer** | FastAPI | RESTful API with async support |
| **Monitoring** | Grafana + Prometheus | Pipeline visibility |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Container** | Docker + Kubernetes | Scalable deployment |

---

## 10. Infrastructure & Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                   │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   API       │  │  Worker     │  │   Scheduler     │ │
│  │  Service    │  │  Pods       │  │   Pod (cron)    │ │
│  │ (FastAPI)   │  │ (Celery)    │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ PostgreSQL  │  │   Redis     │  │   RabbitMQ      │ │
│  │ (StatefulSet│  │  (Cache +   │  │  (Message Bus)  │ │
│  │  + PVC)     │  │   Queue)    │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
          │                    │
          ▼                    ▼
   External APIs          AWS S3 / GCS
   (Claude, Veo-3,        (Media Storage)
    Kling, ElevenLabs,
    Social Platforms)
```

### Environments
- **dev**: Local Docker Compose, mock external APIs
- **staging**: K8s cluster, real APIs with test accounts
- **prod**: K8s cluster, full production, rate-limited

---

## 11. Security & Configuration Management

### Secrets Management
- All API keys stored in AWS Secrets Manager / HashiCorp Vault
- Environment-specific `.env` files (never committed)
- Kubernetes Secrets for pod-level access

### API Key Inventory
```
ANTHROPIC_API_KEY          - Claude LLM
OPENAI_API_KEY             - DALL-E image generation
ELEVENLABS_API_KEY         - Audio TTS
VEO3_API_KEY               - Video generation
KLING_API_KEY              - Video generation
RENDERIO_API_KEY           - Programmatic video
INSTAGRAM_ACCESS_TOKEN     - Instagram Graph API
LINKEDIN_ACCESS_TOKEN      - LinkedIn API
FACEBOOK_ACCESS_TOKEN      - Facebook Graph API
TWITTER_BEARER_TOKEN       - X/Twitter API
YOUTUBE_API_KEY            - YouTube Data API
DATABASE_URL               - PostgreSQL connection
REDIS_URL                  - Redis connection
S3_BUCKET_NAME             - Asset storage
```

---

## 12. Phase 1 & 2 Breakdown

> Detailed subtasks are tracked in the project task system. Below is a summary.

### Phase 1: Foundation & Core Infrastructure

| Task | Owner | Dependencies |
|---|---|---|
| Project structure setup (monorepo layout) | AI Agent Architect | — |
| CI/CD pipeline (GitHub Actions) | AI Agent Architect | Project structure |
| Coding standards + linting config | AI Agent Architect | Project structure |
| Environment config (dev/staging/prod) | AI Agent Architect | Project structure |
| Agent framework implementation | AI Agent Architect | Framework decision |
| Agent communication protocol implementation | AI Agent Architect | Protocol design |
| Agent lifecycle management | AI Agent Architect | Framework |
| Database schema design + migrations | AI Agent Architect | Data models |
| Redis cache setup | AI Agent Architect | Infra |
| Asset storage setup (S3/GCS) | Media Gen Engineer | Infra |
| Secrets management setup | All | Infra |

### Phase 2: Content Ideation Pipeline

| Task | Owner | Dependencies |
|---|---|---|
| MAMA agent implementation | AI Agent Architect | Phase 1 complete |
| Trending topic detection | AI Agent Architect | MAMA base |
| Manual trigger API endpoint | AI Agent Architect | MAMA base |
| Scheduler (cron) setup | AI Agent Architect | MAMA base |
| CMI agent implementation | AI Agent Architect | MAMA complete |
| CMI LLM prompt engineering | AI Agent Architect | CMI base |
| Decision Maker module | AI Agent Architect | CMI complete |
| Content routing logic | AI Agent Architect | Decision Maker |

---

## Appendix: Domain Research Documents

The following documents contain detailed domain-specific research from each engineering specialty. They are referenced by this architecture and will be integrated into future revisions:

- **Agent Framework**: `docs/AGENT_FRAMEWORK.md`, `docs/AGENT_PROMPTS.md`, `docs/COMMUNICATION_PROTOCOL.md`
- **Media Generation**: `docs/MEDIA_APIS.md`, `docs/MEDIA_PIPELINE.md`, `docs/FRAME_COMBINE_ENGINE.md`
- **Approval & QA**: `docs/APPROVAL_WORKFLOWS.md`, `docs/QA_CRITERIA.md`, `docs/HUMAN_REVIEW_SYSTEM.md`
- **Publishing**: `docs/PLATFORM_APIS.md`, `docs/PUBLISHING_PIPELINE.md`, `docs/ANALYTICS_TRACKING.md`

---

*This document is maintained by the MAMA Project Coordinator. Last updated: 2026-02-19.*
