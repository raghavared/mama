# MAMA Agent Framework Design
## Multi-Agent Orchestration Architecture

---

## 1. Framework Comparison

### 1.1 LangGraph

**Overview**: LangGraph is a library built on top of LangChain that enables building stateful, multi-agent applications as directed graphs. Each node in the graph represents an agent or a processing step; edges define the flow of control.

| Dimension | Assessment |
|---|---|
| **Paradigm** | Graph-based state machine; nodes = agents/steps, edges = transitions |
| **State Management** | First-class: each graph maintains a typed `StateDict` that flows through all nodes |
| **Agent Communication** | Via shared graph state; agents read/write to the same state object |
| **Human-in-the-Loop** | Native `interrupt` mechanism for pausing and resuming at any graph node |
| **Persistence** | Built-in checkpoint system (SQLite, Postgres, Redis backends) |
| **Streaming** | Token-level and event-level streaming support |
| **Parallelism** | Fan-out/fan-in via `Send` API; parallel branches merge at sync nodes |
| **Observability** | LangSmith integration; trace every node invocation |
| **Maturity** | Production-ready; actively maintained by LangChain Inc. |
| **Learning Curve** | Medium; requires understanding of graph/state model |
| **Vendor Lock-in** | LangChain ecosystem; can use any LLM but tied to LC abstractions |

**Pros for MAMA**:
- The approval loop (generate → review → approve/reject → improve) maps perfectly to cyclic graph edges
- Built-in human interrupt is ideal for the human-in-the-loop approval step
- Persistent checkpoints let long-running pipelines survive crashes
- The `Send` API enables parallel image/video generation branches

**Cons for MAMA**:
- Verbose configuration for complex graphs
- LangChain dependency adds ~1,500 dependencies
- State dict must be defined upfront — less flexible for dynamic agent spawning

---

### 1.2 CrewAI

**Overview**: CrewAI is a role-based multi-agent framework where agents are defined by role, goal, and backstory. A `Crew` orchestrates tasks assigned to agents using either sequential or hierarchical process flows.

| Dimension | Assessment |
|---|---|
| **Paradigm** | Role-based task delegation; Crew → Agent → Tool |
| **State Management** | Task context passed between agents; no explicit shared state graph |
| **Agent Communication** | Via task output chaining; agent A output → agent B input |
| **Human-in-the-Loop** | `human_input=True` per task, but limited control |
| **Persistence** | Memory backends (short/long-term via embeddings, entity memory) |
| **Streaming** | Limited; verbose output streaming only |
| **Parallelism** | Sequential and hierarchical modes; limited true parallelism |
| **Observability** | CrewAI+ platform; basic logging otherwise |
| **Maturity** | Rapidly growing; some API instability across versions |
| **Learning Curve** | Low; role/goal/backstory is intuitive |
| **Vendor Lock-in** | Minimal; agents can wrap any LLM |

**Pros for MAMA**:
- Fast prototyping — CMI, CST, VST, CSA map naturally to crew roles
- Low boilerplate for simple pipelines
- Good built-in memory for agent context retention

**Cons for MAMA**:
- No native cyclic workflows — approval loops require workarounds
- Task parallelism is limited (process='parallel' is basic)
- State persistence is weaker than LangGraph checkpoints
- Less control over routing logic (Decision Maker module would need heavy customization)

---

### 1.3 Custom Framework (Python + Celery/Redis)

**Overview**: Build a bespoke agent orchestration layer using Python asyncio, Redis for message passing, Celery for task queuing, and PostgreSQL for state persistence.

| Dimension | Assessment |
|---|---|
| **Paradigm** | Event-driven message bus; agents are independent workers |
| **State Management** | Explicit DB records per workflow run; full control |
| **Agent Communication** | Redis pub/sub or Celery task chains |
| **Human-in-the-Loop** | Custom webhook/notification system required |
| **Persistence** | PostgreSQL + Redis; fully owned |
| **Streaming** | Custom SSE/WebSocket implementation |
| **Parallelism** | Full control via Celery workers and asyncio |
| **Observability** | Custom Prometheus metrics + Grafana dashboards |
| **Maturity** | N/A (greenfield); reliability depends on implementation quality |
| **Learning Curve** | High — must build routing, retry, and lifecycle from scratch |
| **Vendor Lock-in** | Zero lock-in |

**Pros for MAMA**:
- Maximum flexibility for MAMA's unique multi-pipeline architecture
- No dependency on third-party orchestration libraries
- Full ownership of state schema, routing logic, retry policies

**Cons for MAMA**:
- Significant engineering effort (estimated 4-6 weeks extra)
- Must re-implement features that LangGraph already provides
- Higher maintenance burden

---

## 2. Framework Recommendation: **LangGraph**

**Recommendation: Use LangGraph as the primary orchestration framework.**

### Rationale

MAMA's workflows are fundamentally **stateful approval loops with conditional branching** — a pattern that LangGraph handles natively:

1. **Cyclic approval loops** (generate → review → approve/reject → improve) are first-class citizens in LangGraph via back-edges in the graph
2. **Human-in-the-loop** approval (Phase 7) uses LangGraph's built-in `interrupt` — no custom notification plumbing needed
3. **Parallel branches** (Veo-3 + Kling + Render.io running concurrently) use the `Send` API
4. **Persistent checkpoints** survive long video generation jobs that may take 10-30 minutes
5. **Production readiness** — LangGraph is battle-tested in production systems

CrewAI is attractive for rapid prototyping but insufficient for MAMA's cyclic approval patterns and parallel video generation requirements. A custom framework provides maximum flexibility but carries unacceptable development overhead for Phase 1.

### Hybrid Strategy

Use **LangGraph for orchestration** but keep agents decoupled from LangGraph internals:

```
MAMA Graph Layer (LangGraph)
    └── Agents are plain Python classes (LangGraph-agnostic)
         └── Each agent exposes a .run(state) → state interface
              └── LangGraph nodes are thin wrappers around agent .run()
```

This ensures agents can be tested independently, and the framework can be replaced in the future if needed.

---

## 3. Recommended Tech Stack: Agent Framework Layer

| Component | Technology | Justification |
|---|---|---|
| Orchestration | LangGraph 0.2+ | Native state machine, loops, human-in-the-loop |
| LLM Provider | Claude API (claude-sonnet-4-6) | Highest capability for content generation |
| State Persistence | PostgreSQL + LangGraph Postgres Checkpointer | Durable workflow state |
| Message Bus | Redis (pub/sub) | Fast inter-agent event routing |
| Task Queue | Celery 5+ | Heavy jobs (video gen, image gen) off-loaded asynchronously |
| Agent Runtime | Python 3.11 + asyncio | Async-native for concurrent API calls |
| Monitoring | LangSmith + Prometheus/Grafana | Trace-level and metrics-level observability |
| API Layer | FastAPI | MAMA trigger endpoint, approval webhooks |

---

## 4. Agent Lifecycle State Machine

Each agent instance transitions through the following states:

```
                    ┌─────────────────────────────────────┐
                    │           AGENT LIFECYCLE            │
                    └─────────────────────────────────────┘

    [CREATED] ──► [INITIALIZING] ──► [IDLE] ──► [RUNNING]
                        │                          │    │
                        │                          │    ▼
                        │                    [PAUSED] ◄──┘
                        │                     │    │
                        │                     │    ▼
                        │                     │  [RESUMING] ──► [RUNNING]
                        │                     │
                        ▼                     ▼
                   [ERROR] ──────────────► [TERMINATED]
                                                 ▲
                              [COMPLETED] ───────┘
```

### State Definitions

| State | Description | Allowed Transitions |
|---|---|---|
| `CREATED` | Agent instance allocated, not yet initialized | → INITIALIZING |
| `INITIALIZING` | Loading config, LLM client, tools | → IDLE, ERROR |
| `IDLE` | Waiting for a task assignment | → RUNNING, TERMINATED |
| `RUNNING` | Actively processing a task | → PAUSED, COMPLETED, ERROR |
| `PAUSED` | Suspended (human approval awaited, rate limit, etc.) | → RESUMING, TERMINATED |
| `RESUMING` | Restoring from checkpoint | → RUNNING, ERROR |
| `COMPLETED` | Task finished successfully | → IDLE (if persistent agent), TERMINATED |
| `ERROR` | Unrecoverable failure | → TERMINATED |
| `TERMINATED` | Agent destroyed and resources freed | (terminal) |

### Lifecycle Events

```python
class AgentLifecycleEvent:
    event_type: Literal[
        "agent.created",
        "agent.initialized",
        "agent.task_started",
        "agent.task_paused",
        "agent.task_resumed",
        "agent.task_completed",
        "agent.task_failed",
        "agent.terminated"
    ]
    agent_id: str
    workflow_run_id: str
    timestamp: datetime
    metadata: dict
```

---

## 5. State Management Design

### 5.1 Workflow State Schema

The central `WorkflowState` flows through all LangGraph nodes:

```python
from typing import TypedDict, Literal, Optional, List
from datetime import datetime

class ContentBrief(TypedDict):
    topic: str
    target_audience: str
    key_message: str
    tone: str
    platforms: List[str]
    content_type: Literal["image_post", "video_post"]

class ScriptVersion(TypedDict):
    version: int
    content: str
    author_agent: str
    created_at: str
    review_feedback: Optional[str]
    status: Literal["draft", "under_review", "approved", "rejected"]

class AssetRecord(TypedDict):
    asset_id: str
    asset_type: Literal["image", "video_clip", "audio", "final_video"]
    source: str          # "dalle", "veo3", "kling", "renderio", "elevenlabs"
    url: str
    quality_score: Optional[float]
    approved: bool

class WorkflowState(TypedDict):
    # Identifiers
    workflow_run_id: str
    created_at: str
    updated_at: str

    # Pipeline phase tracking
    current_phase: Literal[
        "ideation", "scripting", "script_approval",
        "asset_generation", "asset_approval", "publishing", "completed"
    ]
    content_pipeline: Literal["image_post", "video_post"]

    # Content data
    trigger_source: Literal["trending", "manual", "scheduled"]
    raw_topic: str
    content_brief: Optional[ContentBrief]

    # Script management
    script_versions: List[ScriptVersion]
    current_script_version: int
    script_approval_cycles: int   # count of rejection → revision loops
    max_approval_cycles: int      # circuit breaker (default: 3)

    # Assets
    assets: List[AssetRecord]

    # Agent decisions and routing
    routing_decision: Optional[Literal["image_post", "video_post"]]
    approval_status: Optional[Literal["pending", "approved", "rejected", "changes_requested"]]
    rejection_reason: Optional[str]

    # Human approval
    human_review_required: bool
    human_review_url: Optional[str]
    human_decision: Optional[Literal["approved", "rejected", "changes_requested"]]

    # Error tracking
    errors: List[dict]
    retry_count: int
```

### 5.2 Persistence Strategy

```
┌──────────────────────────────────────────────────────┐
│                  Persistence Layers                   │
├──────────────────────────────────────────────────────┤
│  Layer 1: LangGraph Checkpointer (PostgreSQL)         │
│  - Saves graph state after every node execution       │
│  - Enables resume-from-failure at exact node          │
│  - Thread ID = workflow_run_id                        │
├──────────────────────────────────────────────────────┤
│  Layer 2: Redis (Hot State Cache)                     │
│  - Current workflow state for fast agent reads        │
│  - TTL: 24h (matches max pipeline duration)           │
│  - Key: mama:workflow:{workflow_run_id}:state         │
├──────────────────────────────────────────────────────┤
│  Layer 3: PostgreSQL (Content DB)                     │
│  - Permanent record of all workflow runs              │
│  - Script versions, asset records, decisions          │
│  - Source of truth for auditing and analytics         │
└──────────────────────────────────────────────────────┘
```

### 5.3 Checkpoint Configuration

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    conn_string=settings.POSTGRES_URL,
    serde=JsonPlusSerializer()   # Handles complex types
)

# Configure graph with checkpointer
graph = mama_workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_approval_node"]  # Pause for human review
)

# Resume a paused workflow
config = {"configurable": {"thread_id": workflow_run_id}}
graph.invoke(human_decision_input, config=config)
```

---

## 6. MAMA Graph Topology

```
                    ┌─────────────────────────┐
                    │       START NODE         │
                    │  (trigger: topic input)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │       MAMA NODE          │
                    │  (orchestrator entry)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │       CMI NODE           │
                    │  (content ideation)      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   DECISION MAKER NODE    │
                    │  (image vs video route)  │
                    └──────┬──────────┬───────┘
                           │          │
               ┌───────────▼─┐      ┌─▼────────────┐
               │  CST NODE   │      │   VST NODE    │
               │(image script│      │(video script) │
               └──────┬──────┘      └──────┬────────┘
                      │                    │
               ┌──────▼──────┐      ┌──────▼────────┐
               │  CSA NODE   │      │   CSA NODE    │
               │(img approve)│      │(vid approve)  │
               └──┬──────┬───┘      └───┬───────┬───┘
     [approved]   │      │ [rejected]   │       │ [rejected]
                  │      └──►(loop back)┘       └──►(loop back)
                  │
         ┌────────▼──────────────────────────────────┐
         │         ASSET GENERATION NODES             │
         │  (parallel: image gen / video gen / audio) │
         └────────────────────┬──────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  HUMAN APPROVAL     │
                    │  (interrupt node)   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │   PUBLISH NODE      │
                    │  (multi-platform)   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │       END           │
                    └────────────────────┘
```

---

## 7. Error Handling & Circuit Breakers

### Approval Loop Circuit Breaker
```python
def should_continue_approval(state: WorkflowState) -> Literal["retry", "escalate"]:
    if state["script_approval_cycles"] >= state["max_approval_cycles"]:
        # Escalate to human after N rejection cycles
        return "escalate"
    return "retry"
```

### API Failure Retry Policy
```python
RETRY_POLICY = {
    "llm_call": {"max_retries": 3, "backoff": "exponential", "base_delay": 1.0},
    "image_gen": {"max_retries": 2, "backoff": "fixed", "base_delay": 5.0},
    "video_gen": {"max_retries": 1, "backoff": "fixed", "base_delay": 30.0},
    "publishing": {"max_retries": 3, "backoff": "exponential", "base_delay": 2.0},
}
```

---

*Document Version: 1.0 | Author: AI Agent Architect | Project: MAMA*
