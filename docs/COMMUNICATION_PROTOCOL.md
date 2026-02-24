# MAMA Communication Protocol
## Inter-Agent Message Formats and Event Schemas

---

## 1. Protocol Overview

MAMA agents communicate via two complementary mechanisms:

| Mechanism | Use Case | Transport |
|---|---|---|
| **LangGraph State** | Primary state passing between graph nodes (within a workflow run) | In-memory + Postgres checkpoint |
| **Event Bus** | Cross-workflow events, monitoring, notifications, async triggers | Redis pub/sub |

All messages and events use JSON. Every message has a standard envelope header plus a typed payload.

---

## 2. Standard Message Envelope

Every message exchanged between agents (whether via state or event bus) follows this envelope:

```json
{
  "message_id": "msg_01HX4K9P2ZR8B3M7N5Q6W0FJCT",
  "message_type": "task_assignment" | "task_result" | "approval_request" | "approval_decision" | "error" | "status_update" | "human_notification",
  "schema_version": "1.0",
  "timestamp": "2026-02-19T14:32:00.000Z",
  "source": {
    "agent_type": "MAMA" | "CMI" | "CST" | "VST" | "CSA" | "DECISION_MAKER" | "SYSTEM",
    "agent_id": "agent_mama_01HX4K9P2Z",
    "session_id": "sess_01HX4K9P2ZWORKFLOW"
  },
  "destination": {
    "agent_type": "CMI",
    "agent_id": "agent_cmi_01HX4K9P2Z" | null,
    "broadcast": false
  },
  "correlation": {
    "workflow_run_id": "run_01HX4K9P2ZR8B3M7N5Q6W0FJCT",
    "parent_message_id": "msg_01HX4K..." | null,
    "trace_id": "trace_01HX4K9P2Z"
  },
  "payload": { ... }
}
```

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `message_id` | ULID string | Globally unique message identifier (ULID for time-sortability) |
| `message_type` | enum | Semantic type of the message (see Section 3) |
| `schema_version` | semver string | Protocol version for backward compatibility |
| `timestamp` | ISO 8601 | UTC timestamp of message creation |
| `source.agent_type` | enum | The type of agent that sent this message |
| `source.agent_id` | string | Instance ID of the sending agent |
| `destination.agent_type` | enum | The intended recipient agent type |
| `destination.broadcast` | boolean | If true, all agents of `destination.agent_type` receive this |
| `correlation.workflow_run_id` | string | ID of the workflow run this message belongs to |
| `correlation.parent_message_id` | string | The message this is in response to (null for initial triggers) |
| `correlation.trace_id` | string | End-to-end trace ID for distributed tracing |

---

## 3. Message Types and Payload Schemas

### 3.1 `task_assignment`

Sent by an orchestrator to assign a task to a downstream agent.

```json
{
  "message_type": "task_assignment",
  "payload": {
    "task_id": "task_01HX4K...",
    "task_type": "content_ideation" | "image_scripting" | "video_scripting" | "script_approval" | "asset_generation" | "publishing",
    "priority": "high" | "medium" | "low",
    "deadline_seconds": 300,
    "input_data": {
      "workflow_state_snapshot": { ... },
      "specific_input": { ... }
    },
    "execution_config": {
      "max_retries": 3,
      "timeout_seconds": 120,
      "callback_on_complete": true,
      "callback_on_failure": true
    }
  }
}
```

### 3.2 `task_result`

Sent by an agent after completing a task assignment.

```json
{
  "message_type": "task_result",
  "payload": {
    "task_id": "task_01HX4K...",
    "status": "success" | "partial_success" | "failure",
    "output_data": { ... },
    "state_updates": {
      "fields_modified": ["content_brief", "script_versions"],
      "new_state_snapshot": { ... }
    },
    "execution_metrics": {
      "duration_ms": 4823,
      "llm_tokens_input": 1240,
      "llm_tokens_output": 892,
      "llm_cost_usd": 0.0043,
      "retry_count": 0
    },
    "failure_details": null
  }
}
```

### 3.3 `approval_request`

Sent to CSA (or a human approver) requesting review of a script or asset.

```json
{
  "message_type": "approval_request",
  "payload": {
    "approval_id": "appr_01HX4K...",
    "approval_type": "script_image" | "script_video" | "image_asset" | "video_asset" | "final_video",
    "approver_type": "CSA" | "human" | "CMI" | "VST",
    "artifact": {
      "artifact_id": "art_01HX4K...",
      "artifact_type": "image_script" | "video_script" | "image_asset" | "video_asset",
      "artifact_url": "s3://mama-assets/...",
      "artifact_data": { ... }
    },
    "review_context": {
      "content_brief": { ... },
      "revision_number": 1,
      "max_revisions": 3,
      "previous_feedback": null
    },
    "deadline_seconds": 3600,
    "escalation_policy": {
      "auto_approve_on_timeout": false,
      "escalate_to_human_on_timeout": true
    }
  }
}
```

### 3.4 `approval_decision`

Sent by CSA (or human) after reviewing an artifact.

```json
{
  "message_type": "approval_decision",
  "payload": {
    "approval_id": "appr_01HX4K...",
    "decision": "APPROVED" | "REJECTED" | "NEEDS_REVISION",
    "decided_by": "CSA" | "human",
    "decided_at": "2026-02-19T14:35:00.000Z",
    "review_result": {
      "overall_score": 78,
      "scores": { ... },
      "strengths": ["Strong hook", "Clear CTA"],
      "issues": [
        {
          "severity": "major",
          "category": "message_clarity",
          "description": "Panel 3 text is too long for mobile viewing",
          "suggested_fix": "Reduce panel 3 text to max 12 words"
        }
      ]
    },
    "revision_instructions": "Shorten panel 3 text. Increase visual contrast on panel 5.",
    "approved_artifact_id": "art_01HX4K..." ,
    "escalate_to_human": false
  }
}
```

### 3.5 `error`

Sent when an agent encounters an unrecoverable error.

```json
{
  "message_type": "error",
  "payload": {
    "error_id": "err_01HX4K...",
    "error_code": "LLM_TIMEOUT" | "INVALID_OUTPUT" | "API_RATE_LIMIT" | "PARSING_FAILURE" | "STATE_CORRUPT" | "MAX_RETRIES_EXCEEDED",
    "error_message": "Claude API timed out after 30 seconds on attempt 3/3",
    "affected_task_id": "task_01HX4K...",
    "recoverable": false,
    "recovery_action": "retry" | "skip" | "escalate" | "terminate",
    "stack_trace": "...",
    "context": {
      "agent_state": "RUNNING",
      "last_successful_node": "cmi_ideation",
      "retry_count": 3
    }
  }
}
```

### 3.6 `status_update`

Sent periodically for monitoring and progress tracking (non-blocking).

```json
{
  "message_type": "status_update",
  "payload": {
    "agent_state": "RUNNING" | "PAUSED" | "IDLE",
    "current_task_id": "task_01HX4K...",
    "progress_percentage": 45,
    "current_step": "Generating content brief — iteration 2 of 3",
    "estimated_completion_seconds": 120
  }
}
```

### 3.7 `human_notification`

Sent to trigger human-in-the-loop review via external notification system.

```json
{
  "message_type": "human_notification",
  "payload": {
    "notification_id": "notif_01HX4K...",
    "notification_type": "approval_required" | "error_escalation" | "workflow_complete" | "quality_threshold_not_met",
    "urgency": "low" | "medium" | "high" | "critical",
    "title": "Script Approval Required: AI Marketing Trends",
    "body": "The video script for 'AI Marketing Trends' has been reviewed by CSA and requires human approval before proceeding to video generation.",
    "review_url": "https://mama.example.com/review/appr_01HX4K",
    "artifact_preview_url": "https://mama.example.com/preview/art_01HX4K",
    "workflow_context": {
      "workflow_run_id": "run_01HX4K...",
      "topic": "AI Marketing Trends",
      "pipeline": "video_post",
      "current_phase": "script_approval"
    },
    "action_buttons": [
      {"label": "Approve", "action": "approve", "style": "primary"},
      {"label": "Request Changes", "action": "request_changes", "style": "secondary"},
      {"label": "Reject", "action": "reject", "style": "danger"}
    ],
    "expires_at": "2026-02-20T14:32:00.000Z"
  }
}
```

---

## 4. Event Types and Routing

### 4.1 Event Bus Channels (Redis pub/sub)

| Channel | Publisher(s) | Subscriber(s) | Purpose |
|---|---|---|---|
| `mama.events.workflow` | All agents | MAMA, Monitoring | Workflow lifecycle events |
| `mama.events.approval` | CSA, Humans | MAMA, CMI, CST, VST | Approval decisions |
| `mama.events.assets` | Asset generators | Asset approvers | Asset ready for review |
| `mama.events.errors` | All agents | MAMA, Alerting | Error events |
| `mama.events.publishing` | Publisher | Analytics | Post published events |
| `mama.notifications` | MAMA | Human operators | Human notification requests |

### 4.2 Core Event Schema

```json
{
  "event_id": "evt_01HX4K...",
  "event_type": "workflow.started" | "workflow.completed" | "workflow.failed" | "agent.state_changed" | "script.approved" | "script.rejected" | "asset.generated" | "asset.approved" | "post.published",
  "schema_version": "1.0",
  "timestamp": "2026-02-19T14:32:00.000Z",
  "workflow_run_id": "run_01HX4K...",
  "source_agent": "MAMA",
  "data": { ... }
}
```

### 4.3 Workflow Lifecycle Events

#### `workflow.started`
```json
{
  "event_type": "workflow.started",
  "data": {
    "trigger_source": "trending" | "manual" | "scheduled",
    "topic": "AI tools for marketers",
    "pipeline_type": "image_post" | "video_post" | "undecided",
    "initiated_by": "user_id" | "scheduler" | "trend_detector"
  }
}
```

#### `workflow.phase_changed`
```json
{
  "event_type": "workflow.phase_changed",
  "data": {
    "previous_phase": "ideation",
    "new_phase": "scripting",
    "transition_reason": "CMI ideation complete, routing to CST"
  }
}
```

#### `workflow.completed`
```json
{
  "event_type": "workflow.completed",
  "data": {
    "total_duration_seconds": 847,
    "pipeline_type": "video_post",
    "published_to": ["Instagram", "LinkedIn"],
    "script_revision_cycles": 1,
    "total_llm_cost_usd": 0.42,
    "post_ids": {
      "instagram": "instagram_post_id",
      "linkedin": "linkedin_post_id"
    }
  }
}
```

### 4.4 Agent State Change Events

```json
{
  "event_type": "agent.state_changed",
  "data": {
    "agent_type": "CST",
    "agent_id": "agent_cst_01HX4K...",
    "previous_state": "IDLE",
    "new_state": "RUNNING",
    "reason": "Received task: image_scripting for workflow run_01HX4K"
  }
}
```

### 4.5 Script Events

#### `script.draft_created`
```json
{
  "event_type": "script.draft_created",
  "data": {
    "script_type": "image_post" | "video_post",
    "version": 1,
    "author_agent": "CST",
    "panel_count": 5,
    "word_count": 280
  }
}
```

#### `script.approved` / `script.rejected`
```json
{
  "event_type": "script.approved",
  "data": {
    "script_type": "image_post",
    "version": 2,
    "approved_by": "CSA",
    "overall_score": 84,
    "revision_cycles_taken": 1
  }
}
```

### 4.6 Asset Events

#### `asset.generation_requested`
```json
{
  "event_type": "asset.generation_requested",
  "data": {
    "asset_type": "image" | "video_clip" | "audio",
    "generation_source": "dalle" | "veo3" | "kling" | "renderio" | "elevenlabs",
    "request_id": "gen_req_01HX4K...",
    "prompt_preview": "Professional flat design illustration of...",
    "estimated_duration_seconds": 45
  }
}
```

#### `asset.generated`
```json
{
  "event_type": "asset.generated",
  "data": {
    "asset_id": "asset_01HX4K...",
    "asset_type": "video_clip",
    "source": "veo3",
    "url": "s3://mama-assets/video/run_01HX4K/scene_01.mp4",
    "duration_seconds": 3.5,
    "quality_score": 0.87,
    "generation_duration_seconds": 52
  }
}
```

### 4.7 Publishing Events

#### `post.published`
```json
{
  "event_type": "post.published",
  "data": {
    "platform": "Instagram",
    "post_type": "reel" | "image_post" | "carousel",
    "post_id": "instagram_post_id_123",
    "post_url": "https://instagram.com/p/...",
    "published_at": "2026-02-19T15:00:00.000Z",
    "scheduled": false
  }
}
```

---

## 5. Routing Logic

### 5.1 MAMA Routing Decision Matrix

```
Incoming Trigger
       │
       ▼
  ┌─────────────────────────────────────────┐
  │        MAMA Routing Logic                │
  ├─────────────────────────────────────────┤
  │                                         │
  │  trigger_source = "trending"            │
  │    → CMI task_assignment               │
  │      (priority: high)                   │
  │                                         │
  │  trigger_source = "manual"             │
  │    → CMI task_assignment               │
  │      (priority: user-specified)         │
  │                                         │
  │  trigger_source = "scheduled"          │
  │    → CMI task_assignment               │
  │      (priority: medium)                 │
  └─────────────────────────────────────────┘

After CMI completes:
       │
       ▼
  ┌─────────────────────────────────────────┐
  │       Decision Maker Routing             │
  ├─────────────────────────────────────────┤
  │                                         │
  │  decision = "image_post"               │
  │    → CST task_assignment               │
  │      (task_type: image_scripting)       │
  │                                         │
  │  decision = "video_post"              │
  │    → VST task_assignment               │
  │      (task_type: video_scripting)       │
  └─────────────────────────────────────────┘

After CST/VST completes:
       │
       ▼
  ┌─────────────────────────────────────────┐
  │       CSA Approval Routing               │
  ├─────────────────────────────────────────┤
  │                                         │
  │  decision = "APPROVED"                 │
  │    → Asset generation pipeline         │
  │                                         │
  │  decision = "NEEDS_REVISION"           │
  │  AND revision_number < max_revisions   │
  │    → Back to CST/VST with feedback     │
  │                                         │
  │  decision = "REJECTED"                 │
  │  OR revision_number >= max_revisions   │
  │    → Human notification + pause        │
  │      (interrupt node)                   │
  └─────────────────────────────────────────┘
```

### 5.2 Message Routing Rules (Code)

```python
from enum import Enum
from typing import Literal

class RoutingRule:
    """Defines how messages are routed between agents."""

    RULES = {
        # MAMA → CMI
        ("MAMA", "task_assignment", "content_ideation"): "CMI",

        # Decision Maker → CST or VST
        ("DECISION_MAKER", "task_result", "image_post"): "CST",
        ("DECISION_MAKER", "task_result", "video_post"): "VST",

        # CST/VST → CSA
        ("CST", "task_result", "image_scripting"): "CSA",
        ("VST", "task_result", "video_scripting"): "CSA",

        # CSA → MAMA (approval decision routing)
        ("CSA", "approval_decision", "APPROVED"): "MAMA",
        ("CSA", "approval_decision", "NEEDS_REVISION"): "MAMA",  # MAMA re-routes to CST/VST
        ("CSA", "approval_decision", "REJECTED"): "MAMA",        # MAMA escalates to human

        # Error routing — all errors go to MAMA for triage
        ("*", "error", "*"): "MAMA",
    }

    @classmethod
    def resolve(cls, source: str, message_type: str, context: str) -> str:
        key = (source, message_type, context)
        wildcard_key = ("*", message_type, "*")
        return cls.RULES.get(key) or cls.RULES.get(wildcard_key) or "MAMA"
```

---

## 6. Agent-to-Agent Communication Flows

### 6.1 Image Post Pipeline — Full Message Sequence

```
MAMA                CMI          Decision      CST          CSA          Publisher
  │                  │            Maker          │            │              │
  │──task_assign────►│            │              │            │              │
  │  (ideation)      │            │              │            │              │
  │                  │──task─────►│              │            │              │
  │                  │  result    │              │            │              │
  │                  │◄───────────│              │            │              │
  │◄─task_result─────│            │              │            │              │
  │  (brief+format)  │            │              │            │              │
  │──task_assign────────────────────────────────►│            │              │
  │  (image_script)  │            │              │            │              │
  │                  │            │              │──appr_req──►│            │
  │                  │            │              │            │              │
  │                  │            │              │◄──appr_dec──│            │
  │                  │            │              │  (APPROVED) │              │
  │◄─task_result─────────────────────────────────│            │              │
  │  (approved script)│           │              │            │              │
  │ [start asset gen]│            │              │            │              │
  │──task_assign────────────────────────────────────────────────────────────►│
  │  (publish)       │            │              │            │              │
  │◄─task_result─────────────────────────────────────────────────────────────│
  │  (published)     │            │              │            │              │
```

### 6.2 CSA Rejection Loop — Message Sequence

```
CST              CSA             MAMA             CST (revision)
 │                │               │                    │
 │──appr_req─────►│               │                    │
 │                │               │                    │
 │◄──appr_dec─────│               │                    │
 │   (REJECTED    │               │                    │
 │    + feedback) │               │                    │
 │────────────────────────────────►                    │
 │  task_result(rejected, feedback)                    │
 │                │               │                    │
 │                │               │──task_assign──────►│
 │                │               │  (revision + fb)   │
 │                │               │                    │──appr_req──►CSA
 │                │               │                    │◄──appr_dec──CSA
 │                │               │                    │  (APPROVED)
 │                │               │◄───task_result─────│
```

---

## 7. Message Validation

All incoming messages are validated against JSON schemas before processing:

```python
import jsonschema
from functools import lru_cache

@lru_cache(maxsize=32)
def get_message_schema(message_type: str) -> dict:
    """Load and cache the JSON schema for a message type."""
    schema_path = f"schemas/messages/{message_type}.json"
    with open(schema_path) as f:
        return json.load(f)

def validate_message(message: dict) -> tuple[bool, str | None]:
    """Validate a message against its schema."""
    try:
        schema = get_message_schema(message["message_type"])
        jsonschema.validate(message, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e.message)
    except KeyError:
        return False, f"Unknown message_type: {message.get('message_type')}"
```

---

## 8. Idempotency and Deduplication

All agents implement idempotent message processing to handle duplicate deliveries:

```python
class IdempotencyGuard:
    """Prevent duplicate message processing using Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl_seconds = 3600  # 1 hour deduplication window

    def is_duplicate(self, message_id: str) -> bool:
        key = f"mama:processed_msgs:{message_id}"
        # SET NX (only set if not exists) — atomic check-and-set
        was_new = self.redis.set(key, "1", nx=True, ex=self.ttl_seconds)
        return not was_new  # If not new, it's a duplicate

    def mark_processed(self, message_id: str):
        """Already handled by is_duplicate (SET NX), but explicit for clarity."""
        pass
```

---

## 9. Protocol Versioning

The protocol uses semantic versioning (`schema_version` field). Breaking changes increment the major version. All agents must declare the protocol versions they support, enabling graceful degradation during rolling upgrades:

```python
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]

def check_version_compatibility(message_version: str) -> bool:
    major = message_version.split(".")[0]
    return any(v.startswith(major) for v in SUPPORTED_SCHEMA_VERSIONS)
```

---

*Document Version: 1.0 | Author: AI Agent Architect | Project: MAMA*
