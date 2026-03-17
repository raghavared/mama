# MAMA — Marketing Agent Multi-Agent Architecture

> An open-source, AI-powered marketing automation system that orchestrates multiple specialist agents to generate, approve, and publish marketing content across social media platforms — fully autonomously, with a human-in-the-loop approval gate.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Running with Docker](#running-with-docker)
  - [Running Locally](#running-locally)
- [Dashboard](#dashboard)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

MAMA is a multi-agent system built on top of the **Claude API (Anthropic)** and **LangGraph** that takes a marketing topic and runs it through a full pipeline:

```
Topic → MAMA Agent → CMI (Brief) → Decision Maker
                                        ↓               ↓
                                   Image Path      Video Path
                                   CST Script      VST Script
                                        ↓               ↓
                                   CSA Approval    CSA Approval
                                        ↓               ↓
                                  Image Gen       Video + Audio Gen
                                        ↓               ↓
                                   Human Review ←──────┘
                                        ↓
                                   Publishing (Instagram, LinkedIn, Facebook, X, YouTube)
```

Each agent is a Claude-powered LLM with a focused prompt and skill set. The system persists all state to PostgreSQL and streams live pipeline progress via WebSockets to a Next.js dashboard.

---

## Architecture

### Agents

| Agent | Role |
|---|---|
| **MAMA** | Entry point — enriches topic, routes to CMI |
| **CMI** (Content Marketing Ideator) | Generates marketing brief, angles, platform strategy |
| **Decision Maker** | Decides image post vs. video post pipeline |
| **CST** (Content Story Teller) | Writes image post script with image prompts |
| **VST** (Video Story Teller) | Writes frame-by-frame video + audio script |
| **CSA** (Content Script Approver) | Reviews and approves/rejects scripts |
| **Image Generator** | Generates images from prompts (DALL-E / Gemini / Stable Diffusion) |
| **Video Generator** | Generates video clips (Veo-3, Kling, Remotion) |

### Pipelines

- **Image Post Pipeline** — Topic → Brief → Image Script → CSA Approval → Image Generation → Human Approval → Publish
- **Video Post Pipeline** — Topic → Brief → Video Script → CSA Approval → Video + Audio Generation → Human Approval → Publish

---

## Features

- Multi-agent orchestration with LangGraph
- Dual content pipelines (image + video)
- LLM fallback chain: Claude → GPT-4o → Gemini
- Real-time pipeline progress via WebSocket
- Human-in-the-loop approval with job reinitiation and run history
- Content job management dashboard (Next.js)
- PostgreSQL persistence with Alembic migrations
- JWT authentication with role-based access (admin, content_manager, reviewer)
- Scheduled content generation (cron-based)
- Multi-platform publishing (Instagram, LinkedIn, Facebook, X, YouTube)
- Structured logging with structlog
- Docker Compose setup for local development

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Agent Framework | LangGraph + LangChain |
| LLM | Claude (Anthropic), GPT-4o, Gemini (fallback) |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Cache / Queue | Redis + Celery |
| Media | Pillow, FFmpeg, MoviePy |
| Audio | ElevenLabs |
| Video | Veo-3, Kling, Remotion |
| Image | DALL-E, Gemini Imagen, Stable Diffusion |
| Dashboard | Next.js 14 + Tailwind CSS + shadcn/ui |
| Auth | JWT (PyJWT) + bcrypt |
| Monitoring | Prometheus + structlog |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Docker + Docker Compose
- PostgreSQL 15+
- Redis 7+

### Environment Variables

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

```env
# Core
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://mama:mama@localhost:5432/mama
REDIS_URL=redis://localhost:6379

# LLM (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...             # optional fallback
GOOGLE_API_KEY=AIza...            # optional fallback

# Image Generation (at least one required)
OPENAI_API_KEY=sk-...             # for DALL-E
GOOGLE_API_KEY=AIza...            # for Gemini Imagen
STABILITY_API_KEY=sk-...          # for Stable Diffusion

# Audio (optional)
ELEVENLABS_API_KEY=...

# Social Publishing (optional — required only for publishing)
INSTAGRAM_ACCESS_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
FACEBOOK_ACCESS_TOKEN=...

# Storage (optional — defaults to local disk)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
```

### Running with Docker

```bash
# Clone the repository
git clone https://github.com/your-org/MAMA.git
cd MAMA

# Start all services (PostgreSQL, Redis, API, Dashboard)
docker compose up --build

# Run database migrations
docker compose exec api alembic upgrade head

# Seed initial admin user
docker compose exec api python -m src.scripts.seed_admin
```

The API will be available at `http://localhost:8000` and the dashboard at `http://localhost:3000`.

### Running Locally

**Backend:**

```bash
# Install uv (recommended)
pip install uv

# Install dependencies
uv sync

# Start PostgreSQL and Redis (or use Docker just for infra)
docker compose up postgres redis -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn src.api.main:app --reload --port 8000
```

**Dashboard:**

```bash
cd dashboard
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`.

**Default credentials (development only):**
- Email: `admin@mama.ai`
- Password: `admin123`

### Setting Up OAuth for Social Publishing

MAMA supports two authentication methods for social media publishing:

1. **OAuth 2.0 (Recommended)** - Secure, user-level authentication with automatic token refresh
2. **Legacy Direct Tokens** - Platform-specific access tokens (deprecated, limited features)

To set up OAuth for each platform:

1. **Read the setup guide**: See [docs/oauth-setup.md](docs/oauth-setup.md) for detailed instructions
2. **Create developer apps** on each platform (Instagram, Facebook, LinkedIn, Twitter, YouTube)
3. **Configure redirect URIs** pointing to your MAMA backend callback endpoint
4. **Add client credentials** to your `.env` file
5. **Connect accounts** via the dashboard at Settings → Social Connections

**Quick start for development:**

```bash
# Example OAuth credentials in .env
INSTAGRAM_CLIENT_ID=your_instagram_app_id
INSTAGRAM_CLIENT_SECRET=your_instagram_app_secret

FACEBOOK_CLIENT_ID=your_facebook_app_id
FACEBOOK_CLIENT_SECRET=your_facebook_app_secret

LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

TWITTER_CLIENT_ID=your_twitter_oauth2_client_id
TWITTER_CLIENT_SECRET=your_twitter_oauth2_client_secret

YOUTUBE_CLIENT_ID=your_google_client_id
YOUTUBE_CLIENT_SECRET=your_google_client_secret
```

**Redirect URIs for development:**
```
http://localhost:8000/api/oauth/callback/instagram
http://localhost:8000/api/oauth/callback/facebook
http://localhost:8000/api/oauth/callback/linkedin
http://localhost:8000/api/oauth/callback/twitter
http://localhost:8000/api/oauth/callback/youtube
```

For production deployment, use your production domain with HTTPS.

See [docs/oauth-setup.md](docs/oauth-setup.md) for complete platform-specific instructions.

---

## Dashboard

The Next.js dashboard provides:

- **Jobs** — Trigger, monitor, pause, resume, reinitiate, and approve content jobs
- **Job Detail** — Live pipeline log, run history, media preview lightbox, brief and script viewer
- **Schedule** — Manage cron-based content generation schedules
- **Approvals** — Review pending human-approval gates
- **Agents** — Monitor active agent status
- **Analytics** — Published post performance
- **Settings** — Configure brand voice, API keys, and platform preferences
- **Users** — Manage team members and roles

---

## API Reference

Interactive API docs (Swagger) are available at `http://localhost:8000/docs`.

Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/jobs/trigger` | Trigger a new content job |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/jobs/{id}` | Get job detail + pipeline logs |
| `POST` | `/api/v1/jobs/{id}/pause` | Pause a running job |
| `POST` | `/api/v1/jobs/{id}/resume` | Resume a paused job |
| `POST` | `/api/v1/jobs/{id}/approve` | Submit human approval decision |
| `POST` | `/api/v1/jobs/{id}/reinitiate` | Restart a job from scratch |
| `DELETE` | `/api/v1/jobs/{id}` | Delete a job |
| `GET` | `/api/v1/dashboard/stats` | Dashboard statistics |
| `WS` | `/ws` | WebSocket for real-time events |

---

## Project Structure

```
MAMA/
├── src/
│   ├── agents/          # All LangGraph-powered agents (MAMA, CMI, CST, VST, CSA, ...)
│   ├── api/
│   │   ├── main.py      # FastAPI app + WebSocket manager
│   │   └── routers/     # jobs, auth, users, schedule, dashboard, config
│   ├── config/          # Settings (pydantic-settings)
│   ├── database/        # SQLAlchemy ORM models + session management
│   ├── media/           # Image, video, audio generators
│   ├── models/          # Pydantic domain models
│   └── utils/           # LLM client, helpers
├── dashboard/           # Next.js 14 frontend
│   ├── app/             # App Router pages
│   ├── components/      # UI components (shadcn/ui)
│   ├── lib/             # API client, auth, WebSocket hook
│   └── types/           # TypeScript types
├── migrations/          # Alembic migration files
├── tests/               # pytest test suite
├── docker/              # Dockerfiles
├── docs/                # Additional documentation
├── remotion/            # Remotion video rendering project
├── pyproject.toml       # Python project config
└── docker-compose.yml   # Local development stack
```

---

## Roadmap

- [ ] Veo-3 and Kling video generation integration
- [ ] ElevenLabs audio pipeline
- [ ] Full multi-platform publishing (Instagram, LinkedIn, X, YouTube, Facebook)
- [ ] Trending topic auto-detection (Google Trends, RSS)
- [ ] Analytics ingestion from social platforms
- [ ] Cost tracking per content piece
- [ ] Grafana monitoring dashboard
- [ ] Webhook support for external triggers
- [ ] Multi-tenant / workspace support
- [ ] Plugin system for custom agents

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

```bash
# Fork the repo, then:
git clone https://github.com/your-username/MAMA.git
cd MAMA
git checkout -b feature/your-feature-name

# Install dev dependencies
uv sync --extra dev

# Install pre-commit hooks
pre-commit install

# Make your changes, then run checks
ruff check .
mypy src/
pytest
```

---

## License

MAMA is released under the [MIT License](LICENSE).
