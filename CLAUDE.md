# CLAUDE.md — MAMA Project

Read `AGENTS.md` first for project architecture, file layout, and coding rules.
This file governs *how* you work — your workflow, mindset, and decision-making process.

---

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps, new agent, schema change, new API endpoint)
- Read the relevant source files *before* proposing a plan — never plan from memory alone
- If something goes sideways, STOP and re-plan immediately — don't keep pushing blind changes
- Use plan mode for verification steps too, not just building
- Write detailed specs upfront: which files change, which migration is needed, what the API response looks like

### 2. Subagent Strategy
- Use subagents liberally to keep the main context window clean
- Offload file exploration, multi-file research, and parallel analysis to subagents
- When investigating a pipeline bug, throw separate subagents at backend vs. frontend simultaneously
- One task per subagent — never chain unrelated work inside one subagent prompt
- Use the Explore agent for broad codebase questions; use Grep/Glob directly for targeted lookups

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern that caused the mistake
- Write a rule that would have prevented it — be specific, not generic
- Ruthlessly iterate on these lessons until mistake rate drops
- Review `tasks/lessons.md` at the start of every session before touching code

### 4. Verification Before Done
- Never mark a task complete without proving it works
- For backend changes: check that the migration runs, the endpoint returns the right shape, and `_orm_to_dict()` includes the new field
- For frontend changes: verify the TypeScript type is updated in `types/index.ts` AND the component uses it
- Ask yourself: "Would a staff engineer approve this PR?"
- For agent changes: trace the full `AgentState` flow — input, LLM call, JSON parse, output, error path

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer a one-liner
- Challenge your own work before presenting it: could this be half the code?

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how
- For pipeline bugs: check `pipeline_logs` in the DB first — the error is almost always there

---

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items before writing any code
2. **Verify Plan**: Check in with the user before starting implementation on architectural changes
3. **Track Progress**: Mark items complete as you go — never lose track mid-task
4. **Explain Changes**: High-level summary at each step (what changed, why, what's next)
5. **Document Results**: Add review section to `tasks/todo.md` after completion
6. **Capture Lessons**: Update `tasks/lessons.md` after any correction or unexpected finding

---

## MAMA-Specific Rules

### Agent Changes
- Always read `src/agents/base.py` before touching any agent
- Never let an agent raise — set `state.error` and return the state
- After adding or changing an agent, add its step label to `STEP_LABELS` in `dashboard/app/jobs/[id]/page.tsx`
- Trace the full pipeline flow in `src/api/routers/jobs.py` to understand where your agent fits

### Database Changes
- Schema change = migration file, always. No exceptions. Never `create_all()`
- Migration naming: `NNN_short_description.py` — check the highest existing number in `migrations/versions/` first
- New column on `ContentJobORM` → update `_orm_to_dict()` in `jobs.py` → update `ContentJob` in `dashboard/types/index.ts`
- JSONB imports go *inside* `upgrade()`, not at module level

### API Changes
- New endpoint → update `dashboard/lib/api.ts` with the typed method
- Any change to the job response shape → update both `_orm_to_dict()` (backend) and `JobWithLogs` / `ContentJob` (frontend)
- Broadcast a WebSocket event via `_broadcast_event()` after every meaningful state change

### Frontend Changes
- All shared types in `dashboard/types/index.ts` — never define them inline in page files
- All HTTP calls go through `dashboard/lib/api.ts` — never raw `fetch()` in components
- Dialogs must be rendered **outside** `<Tabs>` — at the same level as the main content div
- Icons from `lucide-react` only — no other icon libraries

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal files.
- **No Laziness**: Find root causes. No temporary hacks. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs in unrelated code.
- **Types Everywhere**: Every Python function has type annotations. Every TypeScript value has a type. No exceptions.
- **Read Before Write**: Always read the file you are about to edit. Never write from memory.
- **One Migration Per Change**: Each schema change gets its own numbered migration file — never bundle unrelated schema changes.
