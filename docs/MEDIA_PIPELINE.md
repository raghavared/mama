# MAMA Media Processing Pipeline
## Complete Design: Image Flow + Video Flow

---

## Overview

MAMA supports two content pipelines that share a common ideation stage before branching into dedicated media generation workflows:

```
MAMA Agent (Entry)
       │
       ▼
CMI Coordinator (Ideation)
       │
  ┌────┴─────┐
  │          │
  ▼          ▼
Image      Video
 Post       Post
Pipeline   Pipeline
```

---

## Pipeline A: Image Post Pipeline

### Flow Diagram

```
CMI Content Brief
       │
       ▼
CST Coordinator
  └─ Story-driven script generation
  └─ Image prompt engineering
       │
       ▼
Script Approver (CSA)
  ├─ [Approved] ──────────────────────────────▶ Image Generation Module
  └─ [Rejected] ──► Improvement Cycle ──────►┘
                    (max 3 iterations)
       │
       ▼
Image Generation Module
  └─ API: DALL-E 3 / GPT-Image (primary)
  └─ Fallback: Stable Diffusion Ultra
  └─ Generate 3 variants per scene
  └─ Quality validation (resolution, artifacts, content check)
       │
       ▼
Image Approval Workflow
  ├─ CMI Review
  ├─ CST Review
  ├─ [Approved] ──────────────────────────────▶ Image Post Publisher
  └─ [Rejected] ──► Regenerate with feedback (max 3 iterations)
       │
       ▼
Image Post Publisher
  └─ Format for each platform (Instagram 1:1, LinkedIn 1.91:1, Facebook)
  └─ Caption/text generation from approved script
  └─ Schedule / immediate post
  └─ Analytics logging
```

### Image Generation Module — Detailed Design

#### Input
```json
{
  "scene_description": "A confident entrepreneur standing at a whiteboard...",
  "brand_guidelines": { "colors": ["#FF6B35", "#1A1A2E"], "style": "professional" },
  "platform_target": "instagram",
  "aspect_ratio": "1:1",
  "quality": "hd"
}
```

#### Processing Steps
1. **Prompt Optimization**: Enhance raw scene description with style keywords, lighting, composition terms
2. **API Call**: DALL-E 3 HD — generate 1 image per API call (API limitation)
3. **Variant Loop**: Call API 3 times with slight prompt variations to get 3 candidates
4. **Quality Validation**:
   - Minimum resolution check (1024×1024 min)
   - NSFW/policy violation detection (OpenAI API returns policy flags)
   - Structural quality score (blur detection, exposure check)
   - Content alignment: LLM evaluates whether image matches prompt intent
5. **Output**: 3 validated image URLs + quality scores

#### Prompt Optimization Template
```
{scene_description}, {style_keywords}, {lighting_description},
{composition_style}, --ar {aspect_ratio} --quality {quality_tier}
Brand colors: {brand_colors}. Style: {brand_style}.
Do not include: text, watermarks, logos.
```

#### Quality Validation Schema
```python
class ImageQualityResult:
    resolution_ok: bool          # min 1024px on shortest side
    no_policy_violation: bool    # OpenAI policy check passed
    blur_score: float            # 0.0–1.0 (>0.7 = acceptable)
    content_alignment_score: float  # LLM evaluation 0.0–1.0
    selected: bool               # True if all checks pass
```

---

## Pipeline B: Video Post Pipeline

### High-Level Flow

```
CMI Content Brief
       │
       ▼
VST Coordinator
  └─ Frame-by-frame video + audio script
  └─ Scene descriptions + timing
  └─ Audio narration text + voice instructions
       │
       ▼
Script Approver (CSA)
  ├─ [Approved] ──────────────────────────────▶ Script Separator
  └─ [Rejected] ──► Improvement Cycle ──────►┘
       │
       ▼
Video & Audio Script Separator
  ├─ Video Script → Scene list with timing, visual cues
  └─ Audio Script → Narration text, timing sync markers
       │
  ┌────┴──────────────────┐
  │                       │
  ▼                       ▼
Video Generation       Audio Generation
Engine (Phase 5)       Engine (Phase 6)
  │                       │
  └──────────┬────────────┘
             │
             ▼
       Audio-Video Merger
             │
             ▼
       Video Approver (VAM)
  ├─ [Approved] ──────────────────────────────▶ Video Publisher
  └─ [Rejected] ──► Targeted Regeneration ──►┘
             │
             ▼
       Human-in-the-Loop Review
             │
             ▼
       Multi-Platform Publisher
```

---

## Video Generation Engine (Phase 5 Detail)

### Input: Video Script
```json
{
  "total_duration": 45,
  "fps": 30,
  "scenes": [
    {
      "scene_id": "s1",
      "duration": 8,
      "type": "ai_video",
      "source_preference": "veo3",
      "prompt": "Close-up of coffee being poured into a white cup, slow motion, golden hour lighting",
      "audio_sync_start": 0.0
    },
    {
      "scene_id": "s2",
      "duration": 5,
      "type": "programmatic",
      "source_preference": "remotion",
      "prompt": "Brand title card: 'Morning Ritual' in bold sans-serif on dark background",
      "audio_sync_start": 8.0
    },
    {
      "scene_id": "s3",
      "duration": 10,
      "type": "ai_video",
      "source_preference": "kling",
      "prompt": "Person reading a book in a cozy cafe, realistic, warm tones",
      "audio_sync_start": 13.0
    }
  ]
}
```

### Scene Source Routing Logic

```
For each scene in video_script:
  if scene.type == "programmatic":
    → Route to Remotion pipeline
  elif scene.source_preference == "veo3":
    → Primary: Veo-3.1 Standard
    → On failure/timeout: fallback to Kling
  elif scene.source_preference == "kling":
    → Primary: Kling 2.6
    → On failure: fallback to Veo-3.1 Fast
  elif scene.source_preference == "auto":
    → Score scene against API strengths
    → Select best-fit API
```

### API Strength Mapping

| Scene Type | Best API | Why |
|---|---|---|
| Realistic motion, nature, people | Veo-3 | Best physics simulation |
| Character consistency (multi-scene) | Kling | Elements feature (4 ref images) |
| Text overlays, brand graphics | Remotion | Pixel-perfect programmatic |
| Data visualizations, animations | Remotion | React/CSS animations |
| Fast draft generation | Veo-3.1 Fast | 10x cheaper, ~same quality |

### Veo-3 Integration Pipeline

```
1. Build prompt from scene description + brand style
2. Submit async job to Vertex AI Veo API
3. Poll job status (max 10 min timeout)
4. On completion: download MP4 to temp storage (GCS)
5. Extract frames: ffmpeg -i clip.mp4 -r 30 frames/s%04d.png
6. Return: frame list + metadata (duration, fps, audio track if present)
```

### Kling Integration Pipeline

```
1. Build prompt from scene description
2. POST to Kling API (text2video endpoint)
3. Get task_id, poll every 30 sec (max 60 min timeout)
4. On completion: download MP4
5. Extract frames: ffmpeg -i clip.mp4 -r 30 frames/s%04d.png
6. Return: frame list + metadata
```

### Remotion Programmatic Pipeline

```
1. LLM (Claude) generates Remotion code plan:
   - Component structure
   - Animation timeline
   - Text/graphic content
   - Timing and duration
2. LLM reviews and validates plan (self-review pass)
3. LLM generates Remotion React component code
4. Code validation: TypeScript compile check
5. Remotion Lambda render:
   renderMedia({ composition, outputLocation, codec: 'h264' })
6. Extract rendered frames from MP4
7. Return: frame list + metadata
```

---

## Audio Generation Engine (Phase 6 Detail)

### Input: Audio Script
```json
{
  "total_duration": 45,
  "voice_id": "Rachel",
  "model": "eleven_turbo_v2_5",
  "segments": [
    {
      "segment_id": "a1",
      "text": "Start your morning with intention...",
      "start_time": 0.0,
      "expected_duration": 4.5,
      "tone": "calm, warm"
    },
    {
      "segment_id": "a2",
      "text": "Build habits that transform your day.",
      "start_time": 10.0,
      "expected_duration": 3.2,
      "tone": "motivational"
    }
  ]
}
```

### Audio Generation Steps

```
1. For each audio segment:
   a. Call ElevenLabs API with segment text + voice settings
   b. Receive MP3 audio + word-level timing metadata
   c. Validate: duration within ±15% of expected
   d. If duration mismatch: adjust speech rate or split segment

2. Assemble segments:
   a. Insert silence padding between segments to match video timeline
   b. Merge all segments into single audio track (ffmpeg concat)

3. Quality check:
   a. Overall duration matches video duration ±0.5s
   b. No clipping or distortion (peak amplitude check)
   c. Silence gaps are intentional (not missing audio)

4. Output: narration.mp3 (mono or stereo) + timing_map.json
```

### Timing Map Format
```json
{
  "total_duration": 45.0,
  "segments": [
    {
      "segment_id": "a1",
      "actual_start": 0.0,
      "actual_end": 4.3,
      "words": [
        {"word": "Start", "start": 0.0, "end": 0.4},
        {"word": "your", "start": 0.4, "end": 0.6}
      ]
    }
  ]
}
```

---

## Audio-Video Synchronization Strategy

### Sync Architecture
The video timeline is the **master timeline**. Audio is fitted to match video timing, not the other way around.

```
Video Timeline (master):
|--s1(8s)--|--s2(5s)--|--s3(10s)--|--s4(8s)--|--s5(14s)--|

Audio Track (fitted):
|--a1(4.3s)--|--silence(8.7s)--|--a2(3.2s)--|--silence(7s)--|...

Final Merge:
|===VIDEO FRAMES===|
|=====AUDIO TRACK=====|
```

### Sync Method

1. **Segment-level sync**: Each audio segment has a `start_time` matching scene transitions
2. **Silence insertion**: `ffmpeg` inserts silence pads to align audio segments with their corresponding video scenes
3. **Final merge command**:
```bash
ffmpeg \
  -i assembled_video.mp4 \
  -i narration.mp3 \
  -c:v copy \
  -c:a aac \
  -map 0:v:0 \
  -map 1:a:0 \
  -shortest \
  final_output.mp4
```

4. **Drift correction**: If audio is >0.5s out of sync, apply time-stretch (±10% max) using `ffmpeg atempo` filter

### Platform-Specific Audio Handling

| Platform | Audio Requirement |
|---|---|
| Instagram Reels | AAC, stereo, 44.1kHz |
| YouTube Shorts | AAC, stereo, 44.1kHz |
| TikTok | AAC, mono or stereo |
| LinkedIn Video | AAC, stereo |
| Facebook Reels | AAC, stereo |

---

## Quality Validation Gates

### Gate 1: Script Quality (CSA)
- Narrative coherence check
- Scene count vs. duration feasibility
- Brand alignment check

### Gate 2: Image/Video Quality (automated)
```python
class VideoQualityResult:
    resolution_ok: bool          # min 720p
    framerate_ok: bool           # >= 24fps
    duration_ok: bool            # within 5% of target
    no_artifacts: bool           # visual artifact detection
    content_alignment_score: float  # LLM: does video match script?
    audio_sync_score: float      # audio-video alignment score
    overall_score: float         # weighted composite
    pass_threshold: float = 0.75
```

### Gate 3: Audio Quality (Audio Approver)
- Clarity and pronunciation
- Emotional tone matches script intent
- No distortion or clipping
- Duration alignment with video

### Gate 4: Final Video (VAM + Human)
- Cross-check with original content brief
- Brand consistency
- Platform compliance (aspect ratio, duration limits)
- Human review interface

---

## Error Handling & Retry Strategy

### API Failure Handling
```
API Call fails:
  → Retry with exponential backoff (1s, 2s, 4s, max 3 retries)
  → On 3rd failure: log error, switch to fallback API
  → If all APIs fail: mark scene as failed, alert coordinator

Generation timeout:
  → Veo-3: 10 min max polling
  → Kling: 60 min max polling
  → Remotion: 5 min max render

Quality check fails:
  → Regenerate with improved prompt (max 3 attempts)
  → If still failing: human escalation
```

### State Persistence
Each pipeline step writes its state to the database:
```json
{
  "pipeline_id": "pipe_abc123",
  "content_type": "video_post",
  "current_stage": "video_generation",
  "scenes": {
    "s1": { "status": "complete", "output_url": "gs://...", "quality_score": 0.89 },
    "s2": { "status": "in_progress", "attempts": 1 },
    "s3": { "status": "pending" }
  },
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:45:00Z"
}
```

This allows pipeline resumption on failure without re-generating already-approved content.

---

## Pipeline Performance Targets

| Metric | Image Post | 30s Video |
|---|---|---|
| Total pipeline time | 3–5 min | 25–45 min |
| Image/video generation | 30–60s | 15–35 min |
| Audio generation | N/A | 30–60s |
| Audio-video merge | N/A | 30–60s |
| Quality validation | 30–60s | 2–5 min |
| Publishing | 15–30s | 30–60s |

---

*Document created: February 2026*
