# MAMA Quality Assurance Criteria & Scoring Rubrics

## Overview

This document defines the quality check criteria and scoring rubrics for each content type in the MAMA pipeline. All scores are 0–100. Each approval gate uses a **minimum pass threshold** and **dimension weights** to compute an overall score.

---

## 1. Script Quality Criteria (CSA Gate)

### Applies To
- Image post scripts (from CST)
- Video scripts (from VST)

### Minimum Pass Threshold: 70/100

### Scoring Dimensions

| Dimension | Weight | Description |
|---|---|---|
| Hook Strength | 20% | Does the opening grab attention in the first 3 seconds / first line? |
| Brand Alignment | 20% | Does the tone, language, and values match brand guidelines? |
| Content Accuracy | 15% | Are facts, product names, and claims accurate? |
| Narrative Flow | 15% | Does the story progress logically and engagingly? |
| CTA Effectiveness | 15% | Is there a clear, compelling call to action? |
| Platform Fit | 10% | Is the format/length/style appropriate for the target platform? |
| Originality | 5% | Is the content fresh and not derivative/repetitive? |

### Scoring Rubric Per Dimension

#### Hook Strength (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Exceptional hook: bold statement, surprising fact, or provocative question that demands attention |
| 70–89 | Good hook: clearly engaging, relevant to topic |
| 50–69 | Adequate hook: present but weak; unlikely to stop scrolling |
| 30–49 | Poor hook: generic opener; no compelling reason to continue |
| 0–29 | No hook or actively off-putting opener |

#### Brand Alignment (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Perfect brand voice match; all messaging consistent with brand guidelines |
| 70–89 | Mostly aligned; minor tone deviations acceptable |
| 50–69 | Some misalignment; noticeable tone or vocabulary inconsistencies |
| 30–49 | Significant misalignment; brand may not be recognizable |
| 0–29 | Completely off-brand; contradicts brand values |

#### Content Accuracy (0–100)
| Score | Criteria |
|---|---|
| 90–100 | All facts verified, product names correct, no misleading claims |
| 70–89 | Mostly accurate; minor phrasing could be clearer |
| 50–69 | One factual issue or ambiguous claim present |
| 0–49 | **Critical fail**: false claims, wrong product info, or legally sensitive content |

#### Narrative Flow (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Seamless progression; each section builds on the previous |
| 70–89 | Clear structure with minor gaps |
| 50–69 | Some logical jumps; story requires effort to follow |
| 0–49 | Disjointed; no coherent through-line |

#### CTA Effectiveness (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Clear, specific, urgent CTA that directly maps to campaign goal |
| 70–89 | Clear CTA but could be more specific or urgent |
| 50–69 | Vague CTA; audience may not know what to do |
| 0–49 | No CTA or contradictory CTA |

#### Platform Fit (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Perfect length, format, hashtag count, and tone for platform |
| 70–89 | Mostly appropriate; minor adjustments needed |
| 50–69 | Some platform-specific issues (too long, wrong format) |
| 0–49 | Wrong format for platform (e.g., long-form script for Twitter) |

#### Originality (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Fresh angle; not seen in recent content calendar |
| 70–89 | Somewhat novel; slight similarity to previous content |
| 50–69 | Repetitive concept but new execution |
| 0–49 | Near-duplicate of recent content |

### Critical Failure Conditions (Immediate Rejection)
- Contains false product claims or fabricated statistics
- Violates platform community guidelines
- Includes legally sensitive content (unverified medical/financial claims)
- Contains competitor disparagement
- Brand safety violation (offensive language, sensitive topics)

### Score Calculation
```python
score = (
    hook_strength * 0.20 +
    brand_alignment * 0.20 +
    content_accuracy * 0.15 +
    narrative_flow * 0.15 +
    cta_effectiveness * 0.15 +
    platform_fit * 0.10 +
    originality * 0.05
)
pass_threshold = 70
```

---

## 2. Image Quality Criteria (CMI + CST Gate)

### Minimum Pass Threshold: 72/100 (both reviewers' weighted average)

### Scoring Dimensions

| Dimension | Weight | Reviewer |
|---|---|---|
| Visual Quality | 25% | Both |
| Brand Compliance | 20% | CMI primary |
| Content-Script Alignment | 20% | CST primary |
| Emotional Impact | 15% | CMI primary |
| Technical Specs | 10% | Both |
| Accessibility | 5% | Both |
| Platform Readiness | 5% | Both |

### CMI Reviewer Focus Areas

#### Brand Compliance (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Brand colors, fonts, logo placement all correct; brand identity unmistakable |
| 70–89 | Mostly compliant; minor color/spacing deviation |
| 50–69 | Some brand elements missing or incorrect |
| 0–49 | **Critical fail**: Wrong brand identity, competitor branding visible |

#### Emotional Impact (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Evokes desired emotion strongly (joy, trust, urgency, aspiration) |
| 70–89 | Clear emotional signal; somewhat compelling |
| 50–69 | Neutral; minimal emotional resonance |
| 0–49 | Wrong emotion conveyed or emotionally confusing |

### CST Reviewer Focus Areas

#### Content-Script Alignment (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Image perfectly illustrates the script's key message |
| 70–89 | Good alignment; one minor disconnect |
| 50–69 | Partial alignment; image could illustrate a different concept |
| 0–49 | Image contradicts or is unrelated to script |

### Shared Criteria (Both Reviewers)

#### Visual Quality (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Sharp, well-composed, professional lighting, no artifacts |
| 70–89 | Good quality with minor imperfections |
| 50–69 | Noticeable quality issues (blur, odd composition, mild artifacts) |
| 0–49 | Unacceptable quality (heavy artifacts, NSFW content, distorted faces) |

#### Technical Specs (0–100)
| Score | Criteria |
|---|---|
| 90–100 | Correct resolution, aspect ratio, file size for all target platforms |
| 70–89 | Meets most platform specs; minor adjustment needed |
| 50–69 | Some platform specs not met |
| 0–49 | Wrong format; cannot be used without regeneration |

#### Platform Readiness (0–100)
- Instagram: 1:1 or 4:5, 1080px min
- LinkedIn: 1.91:1 or 1:1, 1200×627px
- Facebook: 1.91:1 preferred
- Twitter/X: 16:9 or 1:1

### Critical Failure Conditions
- NSFW or offensive content
- Competitor brand elements visible
- Trademarked third-party imagery without license
- Faces with uncanny valley distortion (prominent subjects)
- Brand identity crisis (wrong brand identity)

### Score Calculation
```python
cmi_score = (
    visual_quality * 0.25 +
    brand_compliance * 0.25 +       # CMI weighted higher
    emotional_impact * 0.25 +       # CMI weighted higher
    technical_specs * 0.10 +
    accessibility * 0.05 +
    platform_readiness * 0.10
)

cst_score = (
    visual_quality * 0.25 +
    content_script_alignment * 0.35 +  # CST weighted higher
    brand_compliance * 0.15 +
    technical_specs * 0.15 +
    accessibility * 0.05 +
    platform_readiness * 0.05
)

# Both must exceed threshold, or combined weighted average must pass
combined_score = (cmi_score + cst_score) / 2
pass_threshold = 72
```

---

## 3. Audio Quality Criteria (Audio Approver Gate)

### Minimum Pass Threshold: 70/100

### Scoring Dimensions

| Dimension | Weight | Description |
|---|---|---|
| Clarity & Intelligibility | 25% | Is every word clearly audible and understandable? |
| Pacing & Rhythm | 20% | Is speaking rate appropriate? No rushed or dragging segments? |
| Script Compliance | 20% | Does audio match the approved audio script exactly? |
| Voice Quality | 15% | Is the voice natural, appropriate tone for content? |
| Timing Sync | 10% | Does audio timing align with video script timing markers? |
| Technical Quality | 10% | No clipping, background noise, or encoding artifacts |

### Automated Checks

| Check | Tool/Method | Pass Condition |
|---|---|---|
| Transcription match | Whisper STT | Word error rate < 5% |
| Duration match | FFprobe | Within ±2 seconds of target duration |
| Silence detection | FFmpeg silencedetect | No unintended silences > 2s |
| Clipping detection | FFmpeg | Peak level < -0.1 dBFS |
| Noise floor | FFmpeg | Background noise < -50 dBFS |
| Bit rate | FFprobe | ≥ 128kbps MP3 or AAC |
| Sample rate | FFprobe | ≥ 44.1 kHz |

### Pacing Analysis

```
Target speaking rate: 130–160 words per minute
Acceptable range:    120–180 wpm

Per-segment analysis:
  - Segment length: 5-second windows
  - Flag if any 5s window exceeds 200 wpm
  - Flag if any 5s window falls below 80 wpm (excluding intentional pauses)
```

### Pronunciation Check

- Brand names: compared against approved pronunciation list
- Product names: exact match required
- Numbers/dates: format validation

### Critical Failure Conditions
- Brand name mispronounced (if listed in brand guidelines)
- Script deviation (missing CTA, added content not in script)
- Offensive content introduced
- Audio too short (< 80% of target duration)

### Score Calculation
```python
score = (
    clarity_intelligibility * 0.25 +
    pacing_rhythm * 0.20 +
    script_compliance * 0.20 +
    voice_quality * 0.15 +
    timing_sync * 0.10 +
    technical_quality * 0.10
)
pass_threshold = 70
```

---

## 4. Video Quality Criteria (Video Approver Gate)

### Minimum Pass Threshold: 70/100

### Scoring Dimensions

| Dimension | Weight | Description |
|---|---|---|
| Scene-Script Alignment | 25% | Do video scenes match the video script descriptions? |
| Visual Continuity | 20% | Smooth transitions, consistent style across sources |
| Technical Quality | 20% | Resolution, framerate, no artifacts |
| Pacing & Timing | 15% | Does video timing match script timing markers? |
| Engagement Factors | 10% | Is video visually compelling? Would viewer keep watching? |
| Brand Consistency | 10% | Brand elements consistent throughout |

### Automated Video Checks

| Check | Method | Pass Condition |
|---|---|---|
| Resolution | FFprobe | ≥ 1080p (1920×1080) |
| Frame rate | FFprobe | ≥ 24 fps (30 fps preferred) |
| Duration | FFprobe | Within ±3 seconds of target |
| Codec | FFprobe | H.264 or H.265 |
| Bitrate | FFprobe | ≥ 5 Mbps for 1080p |
| Artifact detection | ML model | Artifact score < 0.2 |
| Scene count | Scene detect | Matches script scene count ±1 |
| Black frame detection | FFmpeg | No black frames > 0.5s (unintended) |

### Scene-Script Alignment Check

```
For each scene in approved video script:
  1. Extract keyframe at scene midpoint
  2. Run CLIP similarity between keyframe and scene description embedding
  3. Score: cosine similarity × 100
  4. Flag scenes with score < 60

Overall scene alignment score = average of all scene scores
```

### Visual Continuity Checks
- Style consistency across Veo-3, Kling, and Render.io segments (perceptual hash similarity)
- Color grading consistency (histogram comparison between adjacent scenes)
- Transition quality (no abrupt cuts unless intentional)

### Platform-Specific Requirements

| Platform | Format | Duration | Aspect Ratio | Max Size |
|---|---|---|---|---|
| Instagram Reels | MP4 H.264 | 15–90s | 9:16 | 650 MB |
| YouTube Shorts | MP4 H.264 | ≤60s | 9:16 | 256 GB |
| TikTok | MP4 H.264 | 15–60s | 9:16 | 287 MB |
| LinkedIn | MP4 H.264 | 3s–30min | 16:9 or 1:1 | 5 GB |
| Facebook Reels | MP4 H.264 | ≤60s | 9:16 | 4 GB |

### Critical Failure Conditions
- Resolution below 720p
- Frame rate below 20 fps
- Video contains prohibited content (NSFW, violence, copyright-infringing footage)
- Duration mismatch > 20% from target

### Score Calculation
```python
score = (
    scene_script_alignment * 0.25 +
    visual_continuity * 0.20 +
    technical_quality * 0.20 +
    pacing_timing * 0.15 +
    engagement_factors * 0.10 +
    brand_consistency * 0.10
)
pass_threshold = 70
```

---

## 5. Final Video Quality Criteria (VAM Gate)

### Minimum Pass Threshold: 75/100 (higher bar as final automated gate)

### Scoring Dimensions

| Dimension | Weight | Description |
|---|---|---|
| Brief Alignment | 25% | Does final output match original campaign brief? |
| Audio-Video Sync | 20% | Is narration perfectly synchronized with visuals? |
| Technical Excellence | 20% | All technical specs met for all target platforms |
| Brand Compliance | 15% | Brand guidelines fully adhered to in final render |
| Script Compliance | 10% | Final content matches approved script intent |
| Platform Readiness | 10% | Ready to publish on all target platforms without modification |

### Additional VAM Checks (Beyond Video Approval)

#### Audio-Video Sync
```
Sync tolerance: ±100ms
Method:
  1. Extract audio transcription timestamps
  2. Compare with video script timing markers
  3. Score: 100 - (avg_sync_offset_ms / 100 * 10)
```

#### Brief Alignment (Semantic Check)
```
Method:
  1. Extract text from video (captions, on-screen text, transcription)
  2. Embed text + original campaign brief
  3. Compute cosine similarity
  4. Score: similarity × 100
Pass threshold: ≥ 0.75 cosine similarity
```

#### Content Safety Check
- Run automated content moderation (AWS Rekognition or equivalent)
- Check: no adult content, violence, offensive symbols
- Check: no competitor logos
- Copyright check: no known copyrighted music/footage signatures

### Pass Conditions for Human Review Queue
Final video only enters human review queue if:
1. VAM overall score ≥ 75
2. All critical checks pass (no critical failures)
3. Audio-video sync within ±100ms average
4. Content safety check passes

If any critical check fails → route back to appropriate pipeline stage.

---

## Scoring Summary Table

| Gate | Min Pass Score | Critical Fail → | Reviewers |
|---|---|---|---|
| CSA Script | 70 | Halt pipeline | CSA agent |
| Image (CMI) | 72 | Halt pipeline | CMI agent |
| Image (CST) | 72 | Halt pipeline | CST agent |
| Audio | 70 | Regenerate | Audio Approver agent |
| Video | 70 | Regenerate frames | Video Approver agent |
| VAM Final | 75 | Re-route to fix stage | VAM agent |
| Human Review | N/A (subjective) | Archive | Human reviewer |

---

## Improvement Guidance by Score Range

| Score | Action |
|---|---|
| 90–100 | Approve |
| 75–89 | Approve with minor notes logged (no blocking) |
| 70–74 | Borderline pass: approve on first submission, flag for review on resubmission |
| 60–69 | Request improvement with specific feedback |
| 50–59 | Request improvement with comprehensive feedback + regeneration params |
| 0–49 | Reject for improvement unless critical fail → then reject permanently |

---

## QA Metrics & Tracking

```python
class QAMetrics:
    """Tracked per content piece and per pipeline run for system improvement."""

    content_id: str
    gate: str

    # Per-run metrics
    first_pass_score: float
    final_score: float
    revision_cycles_needed: int
    time_to_approval_minutes: float

    # Dimension breakdown
    dimension_scores: Dict[str, float]

    # Improvement tracking
    score_delta_per_cycle: List[float]  # Score change per revision
    improvement_areas: List[str]         # Which dimensions improved most

    # System-level aggregates (computed across all content)
    gate_pass_rate: float               # % passing on first submission
    avg_revision_cycles: float
    avg_time_to_approval: float
    common_failure_categories: List[str]
```
