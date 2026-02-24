# MAMA - Marketing Agent Multi-Agent Architecture
## Development Plan

---

## System Overview

MAMA is an AI-powered marketing automation system that orchestrates multiple coordinator agents to generate, approve, and publish marketing content across social media channels. The system supports two content pipelines: **Image Posts** and **Short Video Posts**.

---

## Architecture Components

### Core Agents & Coordinators
| Agent/Coordinator | Name | Skills | Role |
|---|---|---|---|
| Marketing Agent | MAMA | Orchestration | Entry point, triggers content generation |
| Content Marketing Ideator | CMI | marketing-ideas, social-content, marketing-psychology | Generates content ideas and strategies |
| Content Story Teller | CST | story-collaborator, social-content, story-idea-generator | Image post scripting & storytelling |
| Video Story Teller | VST | story-collaborator, social-content, story-idea-generator | Video post scripting & storytelling |
| Content Script Approver | CSA | script-review, quality-check | Approves/reviews scripts |
| Audio Approver | Audio Approver | audio-quality-check | Approves generated audio |
| Video Approver | Video Approver | video-quality-check | Approves generated video |
| Final Video Approver | VAM | VST & CAS skills | Final video approval coordinator |

### External Services & APIs
- **Image Generation**: AI image generation service (e.g., DALL-E, Midjourney API)
- **Video Generation**: Veo-3, Kling
- **Programmatic Video**: Render.io (code-based rendering)
- **Audio Generation**: ElevenLabs TTS
- **Social Platforms**: Instagram, LinkedIn, Facebook, X (Twitter), YouTube

---

## Development Phases

### Phase 1: Foundation & Core Infrastructure (Weeks 1-3)
**Objective**: Set up project structure, agent framework, and core communication layer.

#### Tasks:
1. **Project Setup**
   - Initialize repository structure (monorepo or modular)
   - Set up CI/CD pipeline
   - Define coding standards, linting, testing frameworks
   - Environment configuration (dev, staging, prod)

2. **Agent Framework Design**
   - Choose/build multi-agent orchestration framework (e.g., LangGraph, CrewAI, custom)
   - Define agent communication protocol (message passing, event-driven)
   - Implement agent lifecycle management (create, run, pause, resume, terminate)
   - Design state management for workflow tracking

3. **Database & Storage Design**
   - Content database schema (topics, scripts, assets, posts)
   - Workflow state persistence
   - Asset storage (images, videos, audio files)
   - Audit trail / logging system

4. **Configuration & Settings**
   - Agent configuration (skills, prompts, parameters)
   - API keys management (secure vault)
   - Channel configuration (platform credentials, posting rules)

---

### Phase 2: Content Ideation Pipeline (Weeks 3-5)
**Objective**: Build the MAMA entry point and CMI coordinator.

#### Tasks:
1. **MAMA Agent (Entry Point)**
   - Trending topic detection (RSS feeds, social listening APIs)
   - Manual trigger interface (API endpoint / UI)
   - Automatic generation scheduler (cron-based)
   - Content routing logic

2. **CMI Coordinator**
   - Marketing ideas generation (LLM-powered)
   - Social content strategy formulation
   - Marketing psychology analysis
   - Content brief creation

3. **Decision Maker Module**
   - Logic to decide: Image Post vs. Short Video Post
   - Criteria: content type, topic suitability, engagement predictions
   - Routing to appropriate downstream coordinator (CST or VST)

---

### Phase 3: Image Post Pipeline (Weeks 5-8)
**Objective**: Build the complete image post creation and approval workflow.

#### Tasks:
1. **CST Coordinator (Image Path)**
   - Story-driven script generation for image posts
   - Story points telling and narrative structure
   - Image prompt engineering

2. **Script Approval System (CSA)**
   - Script review workflow
   - Approval / rejection / improvement feedback loop
   - Approved script → image generation trigger
   - Rejected script → improvement cycle with feedback

3. **Image Generation Module**
   - Integration with AI image generation API
   - Prompt optimization and iteration
   - Image quality validation
   - Multiple variant generation

4. **Image Approval Workflow**
   - Dual approval: CMI & CST coordinators review
   - Image improvement feedback loop
   - Final approval gate

5. **Image Post Publishing**
   - Format images for each platform (Instagram, LinkedIn, Facebook)
   - Caption/text generation from approved script
   - Scheduled/immediate posting
   - Post tracking and analytics logging

---

### Phase 4: Video Post Pipeline - Scripting (Weeks 8-11)
**Objective**: Build video scripting, approval, and script separation.

#### Tasks:
1. **VST Coordinator (Video Path)**
   - Frame-by-frame video & audio script generation
   - Story-driven narrative for short-form video
   - Scene description and timing

2. **Script Approval for Video (CSA)**
   - Video script review workflow
   - Improvement feedback loop
   - Approval gate

3. **Video & Audio Script Separator**
   - Parse approved script into:
     - **Video Script**: scene descriptions, visual cues, timing
     - **Audio Script**: narration text, voice instructions, timing sync

---

### Phase 5: Video Generation Engine (Weeks 11-15)
**Objective**: Build multi-source video generation and frame combining.

#### Tasks:
1. **Veo-3 Integration**
   - API integration with Google Veo-3
   - Prompt-to-video generation
   - Frame extraction (group of frames output)

2. **Kling Integration**
   - API integration with Kling AI
   - Video clip generation
   - Frame extraction (group of frames output)

3. **Render.io Programmatic Video**
   - Code plan generation from video script
   - Plan review system
   - Code writing for programmatic rendering
   - Video rendering execution
   - Output: rendered video frames

4. **Frame Combine Engine**
   - Collect frames from all sources (Veo-3, Kling, Render.io)
   - Intelligent frame ordering and sequencing
   - Transition effects between sources
   - Assembled video output

5. **Video Quality Checker**
   - Automated quality validation (resolution, framerate, artifacts)
   - Content alignment check (does video match script?)
   - Quality score generation

---

### Phase 6: Audio Generation & Merging (Weeks 15-17)
**Objective**: Build audio pipeline and audio-video merging.

#### Tasks:
1. **ElevenLabs Audio Generation**
   - API integration with ElevenLabs
   - Voice selection and configuration
   - Audio narration generation from audio script
   - Timing synchronization with video frames

2. **Audio Approver Coordinator**
   - Audio quality review
   - Improvement feedback loop
   - Approved audio output

3. **Audio & Video Merger**
   - Synchronize audio with video timeline
   - Final render with combined audio + video
   - Format optimization for target platforms

---

### Phase 7: Final Approval & Publishing (Weeks 17-19)
**Objective**: Build final approval workflows and multi-platform publishing.

#### Tasks:
1. **Video Approver Coordinator (VAM)**
   - Final video quality review
   - Cross-check with original brief and script
   - Approval / improvement routing

2. **Human-in-the-Loop Approval**
   - Notification system for human reviewers
   - Review UI (web dashboard or messaging integration)
   - Approve / reject / request changes interface
   - Feedback capture for model improvement

3. **Multi-Platform Publishing**
   - Instagram Reels/Posts API integration
   - LinkedIn Video/Posts API integration
   - X (Twitter) media posting API
   - YouTube Shorts API integration
   - Facebook Reels/Posts API integration
   - Platform-specific formatting and optimization

4. **System & Sheet Update**
   - Content tracking spreadsheet/database update
   - Analytics data logging
   - Performance metrics capture
   - Workflow completion logging

---

### Phase 8: Integration, Testing & Deployment (Weeks 19-22)
**Objective**: End-to-end integration, testing, and production deployment.

#### Tasks:
1. **End-to-End Integration Testing**
   - Full image pipeline test (topic → post)
   - Full video pipeline test (topic → post)
   - Approval loop testing (approvals, rejections, improvements)
   - Error handling and recovery testing

2. **Performance & Scalability**
   - Load testing for concurrent content generation
   - API rate limiting and retry logic
   - Cost optimization (API calls, storage, compute)

3. **Monitoring & Observability**
   - Agent activity dashboards
   - Pipeline status monitoring
   - Error alerting and notifications
   - Cost tracking per content piece

4. **Documentation & Deployment**
   - System architecture documentation
   - API documentation
   - Deployment runbooks
   - User guides for human reviewers

---

## Technology Stack (Recommended)
| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Agent Framework | LangGraph / CrewAI / Custom |
| LLM Provider | Claude API (Anthropic) |
| Image Gen | DALL-E / Stable Diffusion API |
| Video Gen | Veo-3 API, Kling API |
| Programmatic Video | Render.io / Remotion |
| Audio Gen | ElevenLabs API |
| Database | PostgreSQL + Redis |
| Storage | S3 / GCS for media assets |
| Queue | Celery / RabbitMQ |
| Monitoring | Grafana + Prometheus |
| CI/CD | GitHub Actions |

---

## Risk & Dependencies
1. **API Availability**: Veo-3, Kling APIs may have waitlists or rate limits
2. **Cost Management**: Multiple AI API calls per content piece can be expensive
3. **Quality Consistency**: Multi-source video frame combining requires careful alignment
4. **Platform API Changes**: Social media APIs change frequently
5. **Human Bottleneck**: Human-in-the-loop approval can slow down pipeline
