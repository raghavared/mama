# MAMA Approval Workflows — State Machines

## Overview

MAMA has five approval gates across the image and video pipelines. Each gate follows the same base state machine pattern but with gate-specific transitions, actors, and rejection paths.

---

## Base State Machine (All Gates)

```
PENDING → SUBMITTED → IN_REVIEW → [APPROVED | REJECTED]
                                        ↓
                                   IMPROVEMENT_REQUESTED
                                        ↓
                                   RESUBMITTED → IN_REVIEW (loop)
                                        ↓
                                   MAX_ATTEMPTS_EXCEEDED → ESCALATED
```

### Universal States

| State | Description |
|---|---|
| `PENDING` | Item queued, awaiting review initiation |
| `SUBMITTED` | Item submitted to reviewer (notification sent) |
| `IN_REVIEW` | Reviewer is actively evaluating |
| `APPROVED` | Item passed; downstream pipeline triggered |
| `REJECTED` | Item permanently failed (max attempts exceeded or critical failure) |
| `IMPROVEMENT_REQUESTED` | Reviewer issued feedback; generator must revise |
| `RESUBMITTED` | Generator revised and resubmitted for another review cycle |
| `ESCALATED` | Max revision cycles exceeded; routed to human decision |

### Transition Guards

- `max_revision_cycles`: Default 3. After 3 rejections, auto-escalate to human.
- `timeout_hours`: Each `IN_REVIEW` state has a timeout. On timeout → auto-escalate.
- `critical_failure`: Certain QA violations (e.g., explicit content, brand violation) → immediate `REJECTED` with no improvement cycle.

---

## Gate 1: CSA Script Approval

**Actors**: Content Script Approver (CSA agent)
**Input**: Script from CST (image path) or VST (video path)
**Output**: Approved script → triggers image/video generation

### State Diagram

```
CST/VST generates script
         │
         ▼
    [PENDING]
         │  CSA picks up script
         ▼
    [SUBMITTED]
         │  CSA begins evaluation
         ▼
    [IN_REVIEW]  ←──────────────────────────────────────┐
         │                                               │
    ┌────┴────┐                                          │
    ▼         ▼                                          │
[APPROVED] [IMPROVEMENT_REQUESTED]                       │
    │            │                                       │
    │            ▼                                       │
    │       feedback sent to CST/VST                     │
    │            │                                       │
    │            ▼                                       │
    │       [RESUBMITTED] ───────────────────────────────┘
    │            (cycle count < 3)
    │
    │       (cycle count >= 3)
    │            ▼
    │       [ESCALATED] → Human decision
    │
    ▼
Trigger image gen / video script separator
```

### CSA Decision Types

| Decision | Next State | Action |
|---|---|---|
| `approve` | `APPROVED` | Pass script to downstream generator |
| `request_improvement` | `IMPROVEMENT_REQUESTED` | Send structured feedback to originating agent |
| `reject_critical` | `REJECTED` | Log reason; notify MAMA; halt pipeline branch |

### Feedback Structure (CSA → CST/VST)

```json
{
  "approval_request_id": "apr_xxxx",
  "gate": "CSA_SCRIPT",
  "decision": "request_improvement",
  "overall_score": 58,
  "issues": [
    {
      "category": "brand_alignment",
      "severity": "high",
      "description": "Script tone does not match brand voice guidelines",
      "suggestion": "Use more conversational language; avoid corporate jargon"
    },
    {
      "category": "hook_strength",
      "severity": "medium",
      "description": "Opening hook is weak; fails to grab attention in first 3 seconds",
      "suggestion": "Start with a bold question or surprising statistic"
    }
  ],
  "revision_cycle": 1,
  "max_cycles": 3
}
```

### Timeouts

- `IN_REVIEW` timeout: 30 minutes (CSA is an automated agent; fast review expected)
- On timeout: retry review once, then escalate to human

---

## Gate 2: Image Approval (CMI + CST Dual Review)

**Actors**: CMI Coordinator + CST Coordinator (both must approve)
**Input**: Generated image(s) from AI image service
**Output**: Approved image → caption generation → publishing pipeline

### State Diagram

```
Image generated
      │
      ▼
  [PENDING]
      │  Submit to both CMI and CST
      ▼
  [SUBMITTED]
      │
      ▼
  [IN_REVIEW]  ←─────────────────────────────────────┐
      │                                               │
      │ CMI reviews          CST reviews              │
      │    │                    │                     │
      │    ▼                    ▼                     │
      │ CMI_DECISION        CST_DECISION              │
      │                                               │
  Aggregate decisions:                                │
  ┌──────────────────────────────────────┐            │
  │ Both APPROVE → APPROVED              │            │
  │ Either REQUESTS_IMPROVEMENT →        │            │
  │   IMPROVEMENT_REQUESTED              │            │
  │ Either REJECTS_CRITICAL → REJECTED   │            │
  └──────────────────────────────────────┘            │
         │                │                           │
         ▼                ▼                           │
    [APPROVED]   [IMPROVEMENT_REQUESTED]              │
         │              │                             │
         │              ▼                             │
         │       merged feedback to                   │
         │       image generator                      │
         │              │                             │
         │              ▼                             │
         │       [RESUBMITTED] ──────────────────────┘
         │              (cycle < 3)
         │       (cycle >= 3) → [ESCALATED] → Human
         │
         ▼
  Caption generation → Platform formatting → Publish
```

### Dual Reviewer Consensus Logic

```
if cmi_decision == APPROVED and cst_decision == APPROVED:
    → APPROVED

elif cmi_decision == REJECT_CRITICAL or cst_decision == REJECT_CRITICAL:
    → REJECTED (critical failure overrides)

else:
    → IMPROVEMENT_REQUESTED
    feedback = merge(cmi_feedback, cst_feedback, deduplicate=True)
```

### Feedback Structure (CMI/CST → Image Generator)

```json
{
  "approval_request_id": "apr_xxxx",
  "gate": "IMAGE_APPROVAL",
  "decision": "request_improvement",
  "cmi_review": {
    "score": 65,
    "verdict": "request_improvement",
    "issues": [
      {
        "category": "content_alignment",
        "description": "Image does not reflect the campaign theme",
        "suggestion": "Include product visuals matching the brief"
      }
    ]
  },
  "cst_review": {
    "score": 72,
    "verdict": "approve",
    "issues": []
  },
  "merged_issues": [
    {
      "category": "content_alignment",
      "severity": "high",
      "description": "Image does not reflect the campaign theme",
      "suggestion": "Include product visuals matching the brief",
      "source_reviewer": "CMI"
    }
  ],
  "revision_cycle": 1,
  "max_cycles": 3
}
```

### Timeouts

- CMI review timeout: 2 hours (human-in-loop possible)
- CST review timeout: 2 hours
- If one reviewer times out, other's decision stands (with escalation flag)

---

## Gate 3: Audio Approval

**Actors**: Audio Approver (automated agent)
**Input**: ElevenLabs-generated audio narration file
**Output**: Approved audio → Audio-Video merger

### State Diagram

```
ElevenLabs generates audio
         │
         ▼
    [PENDING]
         │
         ▼
    [SUBMITTED]
         │  Audio Approver loads audio + script for comparison
         ▼
    [IN_REVIEW]  ←────────────────────────────────┐
         │                                         │
    ┌────┴────┐                                    │
    ▼         ▼                                    │
[APPROVED] [IMPROVEMENT_REQUESTED]                 │
    │            │                                 │
    │            ▼                                 │
    │       feedback to ElevenLabs generator       │
    │       (voice params, pacing, pronunciation)  │
    │            │                                 │
    │            ▼                                 │
    │       [RESUBMITTED] ──────────────────────── ┘
    │            (cycle < 3)
    │       (cycle >= 3) → [ESCALATED] → Human
    │
    ▼
Audio-Video Merger
```

### Feedback Structure (Audio Approver → ElevenLabs Generator)

```json
{
  "approval_request_id": "apr_xxxx",
  "gate": "AUDIO_APPROVAL",
  "decision": "request_improvement",
  "audio_score": 71,
  "issues": [
    {
      "category": "pacing",
      "severity": "medium",
      "timestamp_range": [12.3, 18.7],
      "description": "Narration is too fast in this segment; difficult to follow",
      "suggestion": "Reduce speaking rate by 15% for this segment"
    },
    {
      "category": "pronunciation",
      "severity": "low",
      "timestamp": 5.2,
      "description": "Brand name mispronounced",
      "suggestion": "Use phonetic spelling: 'MAY-mah' for correct pronunciation"
    }
  ],
  "regeneration_params": {
    "voice_id": "same",
    "stability": 0.75,
    "similarity_boost": 0.80,
    "speaking_rate": 0.90
  },
  "revision_cycle": 1,
  "max_cycles": 3
}
```

---

## Gate 4: Video Approval (Pre-Audio)

**Actors**: Video Approver (automated agent)
**Input**: Assembled video from Frame Combine Engine (before audio merge)
**Output**: Approved video → Audio-Video merger

### State Diagram

```
Frame Combine Engine outputs assembled video
         │
         ▼
    [PENDING]
         │
         ▼
    [SUBMITTED]
         │  Video Approver loads video + video script
         ▼
    [IN_REVIEW]  ←────────────────────────────────────┐
         │                                             │
    ┌────┴────┐                                        │
    ▼         ▼                                        │
[APPROVED] [IMPROVEMENT_REQUESTED]                     │
    │            │                                     │
    │            ▼                                     │
    │       feedback to Frame Combine / video sources  │
    │            │                                     │
    │            ▼                                     │
    │       [RESUBMITTED] ────────────────────────────┘
    │            (cycle < 3)
    │       (cycle >= 3) → [ESCALATED] → Human
    │
    ▼
Audio-Video Merger (merges with approved audio)
```

### Feedback Structure (Video Approver → Frame Engine)

```json
{
  "approval_request_id": "apr_xxxx",
  "gate": "VIDEO_APPROVAL",
  "decision": "request_improvement",
  "video_score": 68,
  "issues": [
    {
      "category": "scene_alignment",
      "severity": "high",
      "frame_range": [45, 90],
      "description": "Scene 3 visuals do not match script description",
      "suggestion": "Regenerate frames 45-90 with updated prompt: 'product in use, outdoor setting'"
    },
    {
      "category": "transition_quality",
      "severity": "medium",
      "frame_range": [120, 125],
      "description": "Abrupt cut between scenes; jarring visual transition",
      "suggestion": "Add fade transition of 0.5s between scenes"
    }
  ],
  "affected_sources": ["kling", "render_io"],
  "revision_cycle": 1,
  "max_cycles": 3
}
```

---

## Gate 5: VAM Final Video Approval

**Actors**: VAM (Final Video Approver coordinator), then Human Reviewer
**Input**: Merged audio+video final render
**Output**: Human-approved content → Multi-platform publishing

### State Diagram

```
Audio-Video Merger outputs final render
         │
         ▼
    [PENDING]
         │
         ▼
    [VAM_REVIEW]  ← automated agent review
         │
    ┌────┴────┐
    ▼         ▼
[VAM_APPROVED] [VAM_IMPROVEMENT_REQUESTED]
    │                    │
    │               improvement cycle (max 2 for VAM)
    │                    │
    ▼               [RESUBMITTED_TO_VAM]
[HUMAN_PENDING]          │
    │               [VAM_APPROVED] → [HUMAN_PENDING]
    │
    │  Human reviewer notified
    ▼
[HUMAN_REVIEW]
    │
    ├── HUMAN_APPROVED → [PUBLISHING_QUEUE]
    ├── HUMAN_REJECTED → [ARCHIVED] (with reason logged)
    └── HUMAN_CHANGE_REQUESTED → [CHANGE_REQUESTED]
                                      │
                                      ▼
                               route to appropriate
                               pipeline stage for fix
                                      │
                                      ▼
                               [HUMAN_PENDING] (loop)
```

### VAM Feedback Structure

```json
{
  "approval_request_id": "apr_xxxx",
  "gate": "VAM_FINAL",
  "decision": "request_improvement",
  "final_score": 74,
  "checks": {
    "brief_alignment": {"score": 80, "passed": true},
    "script_compliance": {"score": 70, "passed": true},
    "technical_quality": {"score": 75, "passed": true},
    "brand_compliance": {"score": 60, "passed": false},
    "platform_readiness": {"score": 85, "passed": true}
  },
  "issues": [
    {
      "category": "brand_compliance",
      "severity": "high",
      "description": "Logo placement violates brand guidelines (too small, low contrast)",
      "suggestion": "Increase logo size by 30%, ensure contrast ratio > 4.5:1",
      "route_to": "render_io_regeneration"
    }
  ],
  "revision_cycle": 1,
  "max_cycles": 2
}
```

### Human Change Request Routing

| Change Type | Route To |
|---|---|
| Script/narrative change | VST → CSA → full regeneration |
| Audio-only change | ElevenLabs → Audio Approver |
| Visual-only change (minor) | Frame engine → Video Approver |
| Caption/text change | Caption generator (no regeneration needed) |
| Brand/logo fix | Render.io → VAM re-review |

---

## Approval Request Data Model

```python
class ApprovalRequest:
    id: str                           # "apr_xxxx"
    gate: ApprovalGate                # Enum: CSA_SCRIPT, IMAGE, AUDIO, VIDEO, VAM_FINAL
    pipeline_run_id: str              # Links to the parent pipeline execution
    content_type: str                 # "image_post" | "video_post"
    subject_asset_url: str            # URL to file being reviewed (script, image, audio, video)
    subject_asset_type: str           # "script" | "image" | "audio" | "video"
    submitted_at: datetime
    submitted_by: str                 # Agent ID
    status: ApprovalStatus            # Enum of states above
    revision_cycle: int               # Current revision count (0-indexed)
    max_revision_cycles: int          # Default 3
    decisions: List[ApprovalDecision] # History of all decisions
    current_reviewer_ids: List[str]   # Active reviewer agent/human IDs
    timeout_at: datetime
    escalated: bool
    metadata: dict                    # Gate-specific extra data

class ApprovalDecision:
    id: str
    approval_request_id: str
    reviewer_id: str                  # Agent ID or human user ID
    reviewer_type: str                # "agent" | "human"
    decision: str                     # "approve" | "request_improvement" | "reject_critical"
    overall_score: int                # 0-100
    issues: List[QAIssue]
    feedback_text: str                # Optional free-text
    decided_at: datetime
    time_to_decide_seconds: int

class QAIssue:
    category: str                     # e.g. "brand_alignment", "pacing", "scene_alignment"
    severity: str                     # "critical" | "high" | "medium" | "low"
    description: str
    suggestion: str
    frame_range: Optional[Tuple[int, int]]  # For video issues
    timestamp_range: Optional[Tuple[float, float]]  # For audio issues

class FeedbackRecord:
    id: str
    approval_decision_id: str
    delivered_to_agent_id: str
    delivered_at: datetime
    acknowledged_at: Optional[datetime]
    acted_upon_at: Optional[datetime]   # When resubmission happened
    revision_outcome: Optional[str]     # "improved" | "no_change" | "degraded"
```

---

## Approval Gate Summary

| Gate | Actor(s) | Input | Timeout | Max Cycles | Critical Fail → |
|---|---|---|---|---|---|
| CSA Script | CSA agent | Script text | 30 min | 3 | Halt pipeline |
| Image Approval | CMI + CST | Image file | 2 hrs each | 3 | Halt pipeline |
| Audio Approval | Audio Approver | Audio file | 1 hr | 3 | Regenerate |
| Video Approval | Video Approver | Video file | 2 hrs | 3 | Regenerate |
| VAM Final | VAM + Human | Final render | 24 hrs human | 2 (VAM) / ∞ human | Human escalate |

---

## Pipeline Integration Points

```
MAMA
 └── CMI (ideation)
      └── CST / VST (scripting)
           │
           ▼
        [Gate 1: CSA Script Approval]
           │ APPROVED
           ▼
     Image Generator / Video Script Separator
           │
     Image Pipeline          Video Pipeline
           │                      │
        [Gate 2:              Veo3/Kling/Render.io
       Image Approval]            │
           │              [Gate 3: Audio Approval]
           │                      │
           │              [Gate 4: Video Approval]
           │                      │
           │              Audio+Video Merge
           │                      │
           └──────────────────────┘
                         │
                    [Gate 5: VAM Final → Human]
                         │ HUMAN_APPROVED
                         ▼
                  Multi-Platform Publishing
```
