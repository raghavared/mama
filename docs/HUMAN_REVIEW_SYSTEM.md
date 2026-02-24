# MAMA Human-in-the-Loop Review System

## Overview

The Human Review System is the final gate before content is published. It provides human reviewers with a streamlined interface to approve, reject, or request changes to content that has passed all automated approval gates. This document covers notification systems, review interfaces, feedback capture, and data contracts.

---

## 1. When Human Review Is Triggered

Human review is triggered for content in two scenarios:

| Scenario | Trigger | Priority |
|---|---|---|
| VAM Final Approval passed | Automated gates all pass; content ready for human sign-off | Normal |
| Escalation from any gate | Max revision cycles exceeded at any automated gate | High |
| Manual escalation | Any agent flags content for human judgment | High |

### Review Assignment

- **Default**: Round-robin assignment to available reviewers in the appropriate reviewer pool
- **Priority content**: Assigned to most experienced reviewer based on review history
- **Escalations**: Assigned to senior reviewer or team lead

---

## 2. Notification System

### Notification Channels

```
Reviewer
  │
  ├── Email notification (all reviews)
  ├── Slack/Teams message (configurable per reviewer)
  ├── In-app notification (web dashboard badge + toast)
  └── SMS (for high-priority / escalations only, opt-in)
```

### Notification Content

#### New Review Assignment Email

```
Subject: [MAMA] Review Required: {content_title} ({content_type}) — Due in {sla_hours}h

---
You have a new content review assignment.

Content: {content_title}
Type: {content_type}  (Image Post | Video Post)
Campaign: {campaign_name}
Target Platforms: {platforms}
Priority: {Normal | High | Escalation}
SLA: Review by {due_datetime}

Pipeline Summary:
  ✅ Script Approved (Score: {script_score})
  ✅ {Image/Video} Approved (Score: {media_score})
  ✅ VAM Final Check (Score: {vam_score})

Review Link: {review_url}

---
MAMA Content System
```

#### Escalation Notification (High Priority)

```
Subject: [MAMA ESCALATION] Human Decision Required: {content_title}

---
⚠️ This content has been escalated and requires your immediate attention.

Reason: {escalation_reason}
Escalated From: {gate_name} after {revision_cycles} revision attempts
Content: {content_title}
Review Link: {review_url}

Please review within 2 hours.
```

### Notification Configuration

```python
class ReviewerNotificationConfig:
    reviewer_id: str
    email: str
    slack_webhook: Optional[str]
    teams_webhook: Optional[str]
    sms_number: Optional[str]

    notification_preferences: NotificationPreferences

class NotificationPreferences:
    channels: List[str]              # ["email", "slack", "in_app"]
    escalation_channels: List[str]   # ["email", "slack", "sms"]
    quiet_hours_start: time          # e.g., 22:00
    quiet_hours_end: time            # e.g., 08:00
    timezone: str                    # e.g., "America/New_York"
    digest_mode: bool                # Batch notifications vs. immediate
    digest_interval_minutes: int     # If digest_mode=True
```

### SLA Definitions

| Priority | Review SLA | Escalation After |
|---|---|---|
| Normal | 24 hours | 28 hours (reminder at 20h) |
| High | 4 hours | 6 hours |
| Escalation | 2 hours | 3 hours (auto-assign to backup) |

### Reminder Notifications
- **At 50% of SLA**: Gentle reminder email
- **At 80% of SLA**: Urgent reminder (all channels)
- **At SLA expiry**: Auto-escalate to team lead + notify original reviewer

---

## 3. Review Interface

### Interface Type: Web Dashboard (Primary)

The review dashboard is a web application that presents content to human reviewers with all necessary context to make an informed decision.

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  MAMA Review Dashboard                    [Notifications: 3] [User] │
├─────────────────────────────────────────────────────────────────────┤
│  Review Queue                                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  [HIGH] Brand Launch Video — Due: 2h 15m   [Open Review]   │    │
│  │  [NORMAL] Product Feature Post — Due: 18h  [Open Review]   │    │
│  │  [NORMAL] Weekly Tips Image — Due: 22h     [Open Review]   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Individual Review Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back to Queue    Brand Launch Video    [Priority: HIGH] [Due: 2h]│
├─────────────┬───────────────────────────────────────────────────────┤
│             │                                                        │
│  CONTEXT    │          CONTENT PREVIEW                              │
│  PANEL      │                                                        │
│             │  ┌──────────────────────┐  ┌──────────────────────┐  │
│  Campaign:  │  │                      │  │   VIDEO PLAYER       │  │
│  Q1 Launch  │  │   IMAGE PREVIEW      │  │   [▶ Play]           │  │
│             │  │                      │  │   0:00 / 0:45        │  │
│  Platforms: │  │   [image here]       │  │   [▶▶ 1x 1.5x 2x]   │  │
│  Instagram  │  │                      │  └──────────────────────┘  │
│  LinkedIn   │  └──────────────────────┘                            │
│  Facebook   │                                                        │
│             │  Caption Preview:                                      │
│  Brief:     │  ┌──────────────────────────────────────────────────┐ │
│  [expand]   │  │ 🚀 Introducing our new product...                │ │
│             │  │ #Launch #Innovation #Brand                       │ │
│  Script:    │  └──────────────────────────────────────────────────┘ │
│  [expand]   │                                                        │
│             │  Platform Preview:  [Instagram] [LinkedIn] [Facebook] │
│  QA Scores: │                                                        │
│  Script: 84 │                                                        │
│  Media:  79 │                                                        │
│  Audio:  82 │                                                        │
│  VAM:    77 │                                                        │
│             │                                                        │
│  Pipeline:  │                                                        │
│  ✅ Script  │                                                        │
│  ✅ Image   │                                                        │
│  ✅ VAM     │                                                        │
├─────────────┴───────────────────────────────────────────────────────┤
│  DECISION                                                            │
│                                                                      │
│  [✅ Approve & Publish]  [✏️ Request Changes]  [❌ Reject]          │
│                                                                      │
│  Schedule:  ● Publish Now  ○ Schedule for: [date/time picker]       │
│  Platforms: ☑ Instagram  ☑ LinkedIn  ☑ Facebook  ☐ Twitter         │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision Flows

#### Approve Flow
```
Click [✅ Approve & Publish]
  → Select publish time (now or scheduled)
  → Select platforms (pre-checked based on campaign config)
  → [Confirm & Publish] button
  → Content enters PUBLISHING_QUEUE
  → Reviewer gets confirmation notification
```

#### Request Changes Flow
```
Click [✏️ Request Changes]
  → Change category selector:
      ○ Script/Copy change
      ○ Visual/Image change
      ○ Audio change
      ○ Caption/hashtag change
      ○ Timing/pacing change
      ○ Brand compliance fix
      ○ Other
  → Free-text feedback box (required)
  → Specific element selector (optional):
      - For video: timestamp range picker
      - For image: bounding box draw tool
  → Priority: ○ Minor  ○ Major
  → [Submit Change Request]
  → Content re-enters appropriate pipeline stage
  → Originating agents notified
  → Reviewer gets notification when fix is ready
```

#### Reject Flow
```
Click [❌ Reject]
  → Rejection reason selector:
      ○ Brand safety violation
      ○ Factual inaccuracy
      ○ Not aligned with campaign brief
      ○ Quality below acceptable standard
      ○ Legal/compliance concern
      ○ Timing no longer relevant
      ○ Other
  → Free-text explanation (required)
  → [Confirm Rejection]
  → Content archived with reason
  → Campaign manager notified
  → Analytics logged
```

### Context Panel Details

The context panel provides reviewers with everything needed to make an informed decision without switching tabs:

```
Context Panel Sections:
  1. Campaign Brief (expandable)
     - Campaign name, goal, target audience
     - Brand voice guidelines excerpt
     - Campaign start/end dates

  2. Original Script (expandable, with highlights)
     - Approved script text
     - Key messages highlighted
     - CTA highlighted in different color

  3. QA Score Summary
     - Each gate's score with color coding:
       ≥85: green, 70-84: yellow, <70: red (shouldn't reach here)
     - Expandable: shows dimension breakdown and issues flagged

  4. Pipeline History
     - Timeline: when each gate was passed
     - Number of revision cycles per gate
     - Any escalation notes

  5. Similar Past Content (if available)
     - 2-3 examples of previously approved similar content
     - Their engagement metrics (for reference)
```

---

## 4. Mobile Review Interface

For reviewers who need to approve on mobile devices:

```
Simplified mobile layout:
  1. Notification → deep link to mobile review page
  2. Swipe-based review:
     - Swipe right: Quick approve
     - Swipe left: Opens decision menu (reject/changes)
     - Tap: Full review with context
  3. Voice note feedback option for change requests
  4. Image pinch-to-zoom for image reviews
  5. Video controls with speed adjustment
```

---

## 5. Slack/Teams Integration (Optional)

For teams already using Slack/Teams as their primary tool:

### Slack Review Flow
```
MAMA Bot posts to #content-review channel:

┌─────────────────────────────────────────────────────────┐
│ MAMA Content Review                                      │
│                                                          │
│ 📸 Image Post: "Spring Campaign Week 2"                  │
│ Campaign: Spring 2024 | Platforms: Instagram, LinkedIn   │
│ Due: April 3, 2:00 PM                                    │
│ QA Score: Script 84 | Image 79 | VAM 77                 │
│                                                          │
│ [View Full Preview] [Approve] [Request Changes] [Reject] │
└─────────────────────────────────────────────────────────┘

Clicking [Approve] → Opens Slack modal with schedule options
Clicking [Request Changes] → Opens Slack modal with feedback form
Clicking [Reject] → Opens Slack modal with rejection form
```

---

## 6. Feedback Capture & Routing

### Feedback Data Model

```python
class HumanReviewDecision:
    id: str
    content_id: str
    approval_request_id: str
    reviewer_id: str
    reviewer_name: str

    decision: HumanDecision  # Enum: APPROVED | CHANGES_REQUESTED | REJECTED

    # For APPROVED
    approved_at: datetime
    publish_immediately: bool
    scheduled_publish_time: Optional[datetime]
    approved_platforms: List[str]

    # For CHANGES_REQUESTED
    change_requests: List[ChangeRequest]
    overall_feedback: str
    priority: str  # "minor" | "major"

    # For REJECTED
    rejection_reason_category: str
    rejection_explanation: str

    # Metadata
    time_spent_reviewing_seconds: int  # Tracked automatically
    review_started_at: datetime
    review_completed_at: datetime

class ChangeRequest:
    category: str       # Script, Visual, Audio, Caption, Timing, Brand, Other
    description: str    # Free-text from reviewer
    priority: str       # "minor" | "major"
    element_reference: Optional[ElementReference]  # Timestamp or bounding box

class ElementReference:
    type: str           # "timestamp_range" | "bounding_box" | "text_segment"
    # For video
    start_time: Optional[float]
    end_time: Optional[float]
    # For image
    x1: Optional[float]
    y1: Optional[float]
    x2: Optional[float]
    y2: Optional[float]
    # For text/script
    start_char: Optional[int]
    end_char: Optional[int]
```

### Change Request Routing Logic

```python
def route_change_request(change_requests: List[ChangeRequest]) -> List[PipelineRoute]:
    routes = []

    for cr in change_requests:
        if cr.category == "Script":
            routes.append(PipelineRoute(
                stage="VST_SCRIPTING",
                agent="VST",
                feedback=cr.description,
                requires_full_regeneration=True
            ))

        elif cr.category == "Visual":
            if "minor" in cr.priority:
                routes.append(PipelineRoute(
                    stage="IMAGE_REGENERATION",
                    agent="IMAGE_GENERATOR",
                    feedback=cr.description,
                    requires_full_regeneration=False  # Targeted re-gen
                ))
            else:
                routes.append(PipelineRoute(
                    stage="VST_SCRIPTING",
                    agent="VST",
                    feedback=cr.description,
                    requires_full_regeneration=True
                ))

        elif cr.category == "Audio":
            routes.append(PipelineRoute(
                stage="AUDIO_GENERATION",
                agent="ELEVENLABS_GENERATOR",
                feedback=cr.description,
                requires_full_regeneration=False
            ))

        elif cr.category == "Caption":
            routes.append(PipelineRoute(
                stage="CAPTION_GENERATION",
                agent="CAPTION_GENERATOR",
                feedback=cr.description,
                requires_full_regeneration=False  # No media re-gen needed
            ))

        elif cr.category == "Brand":
            routes.append(PipelineRoute(
                stage="RENDER_IO_REGENERATION",
                agent="RENDER_IO",
                feedback=cr.description,
                requires_full_regeneration=False
            ))

    return deduplicate_routes(routes)  # Merge overlapping routes
```

---

## 7. Review Dashboard Features

### Queue Management
- **Filter by**: Priority, content type (image/video), campaign, platform, due date
- **Sort by**: Due date (default), priority, content type
- **Bulk approve**: For clearly approved batches (e.g., approve 5 similar posts)
- **Reassign**: Team leads can reassign reviews

### Analytics & Reporting (Dashboard)
```
Review Metrics Panel:
  - Average review time per reviewer
  - Approval rate (approvals / total reviewed)
  - Change request rate
  - Rejection rate
  - Most common change request categories
  - Average time from submission to publish

Per-Content Metrics:
  - Time in review queue
  - Number of human change cycles
  - Final outcome (published, rejected, archived)
```

### Audit Trail
Every human decision is logged immutably:
```python
class AuditEntry:
    timestamp: datetime
    actor_type: str          # "human_reviewer" | "agent" | "system"
    actor_id: str
    action: str              # "approved" | "rejected" | "changes_requested" | "escalated"
    content_id: str
    approval_request_id: str
    decision_summary: str    # Human-readable summary
    ip_address: str          # For compliance
    session_id: str
```

---

## 8. API Contracts

### Submit for Human Review
```
POST /api/v1/review/submit
{
  "content_id": "cnt_xxxx",
  "approval_request_id": "apr_xxxx",
  "content_type": "video_post",
  "priority": "normal",
  "vam_score": 77,
  "asset_urls": {
    "video": "s3://...",
    "thumbnail": "s3://...",
    "caption": "...",
    "script": "s3://..."
  },
  "campaign_context": {
    "campaign_id": "camp_xxxx",
    "brief_url": "s3://...",
    "target_platforms": ["instagram", "linkedin"]
  },
  "qa_summary": {
    "script_score": 84,
    "media_score": 79,
    "audio_score": 82,
    "vam_score": 77
  }
}

Response 201:
{
  "review_id": "rev_xxxx",
  "assigned_to": "reviewer_001",
  "due_at": "2024-04-03T14:00:00Z",
  "review_url": "https://mama.dashboard/review/rev_xxxx"
}
```

### Submit Human Decision
```
POST /api/v1/review/{review_id}/decide
{
  "decision": "changes_requested",
  "change_requests": [
    {
      "category": "Audio",
      "description": "The voice is too monotone in the second half. Need more energy.",
      "priority": "minor",
      "element_reference": {
        "type": "timestamp_range",
        "start_time": 22.0,
        "end_time": 45.0
      }
    }
  ],
  "overall_feedback": "Good content overall, just needs audio polish."
}

Response 200:
{
  "review_id": "rev_xxxx",
  "status": "changes_requested",
  "routes": [
    {
      "stage": "AUDIO_GENERATION",
      "agent": "ELEVENLABS_GENERATOR",
      "estimated_completion_minutes": 15
    }
  ],
  "reviewer_notification": "You will be notified when changes are ready for re-review."
}
```

### Get Review Status
```
GET /api/v1/review/{review_id}

Response 200:
{
  "review_id": "rev_xxxx",
  "content_id": "cnt_xxxx",
  "status": "in_review",
  "assigned_to": "reviewer_001",
  "submitted_at": "...",
  "due_at": "...",
  "revision_cycle": 1,
  "history": [
    {
      "timestamp": "...",
      "action": "submitted_for_review",
      "actor": "vam_agent"
    },
    {
      "timestamp": "...",
      "action": "changes_requested",
      "actor": "reviewer_001",
      "summary": "Audio re-generation requested"
    }
  ]
}
```

---

## 9. Feedback Loop for Model Improvement

Human feedback is valuable training signal. All human decisions are stored for model improvement:

```python
class ModelImprovementRecord:
    """
    Captures human feedback to improve automated agents over time.
    Fed into fine-tuning or RLHF pipelines.
    """
    content_id: str
    gate: str
    automated_score: float           # What the automated agent scored it
    human_decision: str              # What human actually decided
    alignment: str                   # "aligned" | "misaligned"

    # When human overrides automated decision
    override_type: Optional[str]     # "human_approved_despite_low_score"
                                     # "human_rejected_despite_high_score"
                                     # "human_added_issues_agent_missed"

    missed_issues: List[str]         # Issues human found that agent missed
    false_positive_issues: List[str] # Issues agent flagged that human dismissed

    # Periodically aggregated for:
    # 1. Prompt engineering improvements to reviewer agents
    # 2. QA scoring threshold calibration
    # 3. Fine-tuning reviewer agent models
```

---

## 10. Access Control

| Role | Permissions |
|---|---|
| Reviewer | Review and decide on assigned content only |
| Senior Reviewer | Review any content, reassign reviews, view team metrics |
| Team Lead | All reviewer permissions + configure SLAs, manage reviewer pools |
| Admin | Full system access including audit logs and model improvement data |

### Reviewer Pools
- **Image Reviewers**: Review image posts (can be non-video experts)
- **Video Reviewers**: Review video posts
- **Brand Reviewers**: Review escalations involving brand compliance
- **Compliance Reviewers**: Review escalations involving legal/compliance concerns

Content is assigned to the appropriate pool based on content type and escalation reason.
