# AGENTS.md — MAMA Project Instructions

This file is read by AI coding assistants (Claude Code, Codex, etc.) before working on this codebase.
Follow every rule here precisely. When in doubt, read the relevant source file before making changes.

---

## Project Overview

MAMA (Marketing Agent Multi-Agent Architecture) is an AI-powered content generation system.

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), LangGraph, PostgreSQL, Redis
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Agents**: Claude API (primary) with GPT-4o and Gemini as automatic fallbacks
- **Package manager (Python)**: `uv` — always use `uv sync`, never `pip install`
- **Package manager (JS)**: `npm` inside `dashboard/`

---

## Repository Layout

```
src/
  agents/          # All LangGraph agent classes — MAMA, CMI, CST, VST, CSA, Decision Maker
  api/
    main.py        # FastAPI app entrypoint + WebSocket manager
    routers/       # One file per domain: jobs, auth, users, schedule, dashboard, config
  config/
    settings.py    # Pydantic-settings — single source of truth for all env vars
  database/
    __init__.py    # Exports: get_db, AsyncSessionLocal, all ORM classes
    models.py      # SQLAlchemy ORM — ContentJobORM, UserORM, etc.
  media/           # Image, video, audio generators (not agents — no LLM calls here)
  models/          # Pydantic domain models (ContentJob, Script, ContentBrief, etc.)
  utils/
    llm_client.py  # MultiLLMClient — handles Claude/GPT-4o/Gemini fallback chain
dashboard/
  app/             # Next.js App Router pages
  components/      # Shared UI components (shadcn/ui based)
  lib/             # api.ts (typed API client), auth.ts, websocket.ts, utils.ts
  types/           # index.ts — single file for all TypeScript types
migrations/
  versions/        # Alembic migration files named NNN_description.py
```

---

## Critical Rules

### Python

- **Always use `from __future__ import annotations`** at the top of every Python file.
- **Type annotations are mandatory** on all functions, methods, and class attributes. No bare `Any` unless unavoidable — always import from `typing`.
- All async DB work uses `AsyncSession` from `sqlalchemy.ext.asyncio`. Never use synchronous SQLAlchemy sessions.
- ORM models live in `src/database/models.py`. Domain (Pydantic) models live in `src/models/`. Do not mix them.
- **Never import ORM models directly** in agents or business logic. Use domain models from `src/models/`. Only routers and DB helpers touch ORM models.
- Settings are always obtained via `from src.config.settings import get_settings` — never read `os.environ` directly.
- Use `structlog.get_logger(__name__)` for logging — never `print()` or the stdlib `logging` directly.
- `src/utils/llm_client.py` provides `MultiLLMClient`. All agents must call LLMs through `BaseAgent.call_llm()` — never instantiate `anthropic.Anthropic()` directly in agents.

### Agents

- Every agent inherits from `BaseAgent` (`src/agents/base.py`) and implements `async def run(self, state: AgentState) -> AgentState`.
- `AgentState` is a Pydantic model that flows between all agents. Never mutate it in place — return a new or updated copy.
- Agent IDs follow the pattern `"agent:<name>"` (e.g. `"agent:cmi"`, `"agent:cst"`).
- Agents must **never** raise exceptions — catch errors, set `state.error = str(e)`, and return. The pipeline runner in `src/api/routers/jobs.py` handles error states.
- LLM responses from agents are always JSON. Parse with `json.loads()` inside a try/except — if parsing fails, set `state.error`.

### Database & Migrations

- **Never use `Base.metadata.create_all()`** to create tables. Always use Alembic migrations.
- Migration files must be named `NNN_short_description.py` where NNN is the next sequential number (e.g. `004_...`).
- Every migration must have both `upgrade()` and `downgrade()` functions.
- For JSONB columns added in migrations, import `from sqlalchemy.dialects.postgresql import JSONB` **inside** the `upgrade()` function, not at the top level.
- New ORM columns should be added **after the last non-relationship column** and **before the `# Relationships` comment** in `models.py`.
- After adding a column to `models.py`, always create the corresponding migration — do not skip it.

### API Routers

- All endpoints require `user: dict = Depends(get_current_user)` unless they are public auth endpoints.
- The `_orm_to_dict()` helper in `jobs.py` is the single place that converts ORM rows to API dicts. When adding new ORM columns, always update `_orm_to_dict()` too.
- Use `await db.flush()` (not `commit()`) inside endpoints that are part of a larger transaction. Use `await db.commit()` only for top-level operations.
- WebSocket events are broadcast via `_broadcast_event()` in `jobs.py` — always fire these after state changes so the dashboard updates in real time.

### Frontend (Dashboard)

- **All TypeScript types live in `dashboard/types/index.ts`** — never define types inline in component files for shared data shapes.
- The typed API client is in `dashboard/lib/api.ts`. All HTTP calls go through it — never use `fetch()` directly in components.
- Use shadcn/ui components from `@/components/ui/` for all UI primitives. Do not install additional UI libraries.
- Icons come from `lucide-react` only.
- Dialog components must be rendered **outside** of `<Tabs>` — as siblings of the main content, not inside `TabsContent`.
- The `JobWithLogs` interface in `dashboard/app/jobs/[id]/page.tsx` extends `ContentJob` — when adding fields to `ContentJob` in `types/index.ts`, also extend `JobWithLogs` if the field comes from the pipeline log API response.

---

## Adding a New Agent

1. Create `src/agents/<name>.py` inheriting from `BaseAgent`.
2. Set `agent_id = "agent:<name>"`.
3. Implement `async def run(self, state: AgentState) -> AgentState`.
4. Call the LLM via `await self.call_llm(system_prompt, user_message)`.
5. Parse the JSON response; on failure set `state.error` and return.
6. Wire the agent into the pipeline in `src/api/routers/jobs.py` inside `run_pipeline()`.
7. Add the step label to `STEP_LABELS` in `dashboard/app/jobs/[id]/page.tsx`.

---

## Adding a New Database Column

1. Add the column to the correct ORM class in `src/database/models.py`.
2. Update `_orm_to_dict()` in `src/api/routers/jobs.py` to include it in API responses.
3. Update the corresponding Pydantic type in `dashboard/types/index.ts`.
4. Create a new migration: `migrations/versions/NNN_description.py` following the existing pattern.

---

## Running the Project

```bash
# Start infrastructure
docker compose up postgres redis -d

# Backend
uv sync
alembic upgrade head
uvicorn src.api.main:app --reload --port 8000

# Frontend
cd dashboard && npm install && npm run dev

# Tests
pytest

# Lint + type-check
ruff check . && mypy src/
```

---

## Environment

All configuration is in `.env` (copy from `.env.example`). Settings are validated at startup via `src/config/settings.py`. Never hardcode values — always add a new field to `Settings` and read from there.

The minimum required env vars to run the backend:
- `DATABASE_URL`
- `REDIS_URL`
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`
