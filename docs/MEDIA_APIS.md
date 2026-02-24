# MAMA Media APIs Research
## API Capabilities, Pricing & Integration Guide

---

## 1. Google Veo-3 (Video Generation)

### Overview
Google Veo-3 is a state-of-the-art AI video generation model. Veo 3.1 is the current stable release (as of late 2025). It is the first major video model to natively generate synchronized audio alongside video.

### Capabilities
- **Text-to-video** and **image-to-video** generation
- **Resolution**: 720p and 1080p output
- **Duration**: Up to 8 seconds per generation
- **Native audio**: Dialogue, ambient sound effects, and music generated in a single pass
- **Physics simulation**: Realistic motion and real-world physics
- **Access**: Via Gemini API and Vertex AI (Google Cloud)

### Pricing (Dec 2025)
| Tier | Price/second | Audio |
|---|---|---|
| Veo 3.0 Full | $0.75/sec | Included |
| Veo 3.1 Standard | $0.40/sec | Included |
| Veo 3.1 Fast | $0.15/sec | Included |
| Veo 3.1 Fast (no audio) | $0.10/sec | None |
| Vertex AI Video+Audio | $0.75/sec | Included |
| Vertex AI Video only | $0.50/sec | None |

**Estimated cost per 8-second clip:**
- Fast tier: ~$1.20 (with audio)
- Standard tier: ~$3.20
- Full tier: ~$6.00

### Subscription Plans
- **Google AI Pro** ($19.99/mo): Veo 3 Fast via Gemini + Flow
- **Google AI Ultra** ($249.99/mo): Veo 3 Full via Gemini + Flow

### Rate Limits & Constraints
- Quota limits apply per project on Vertex AI
- Generation is asynchronous (polling required)
- Output: Video file (MP4) with optional audio track

### Integration Approach (MAMA)
```python
# Vertex AI SDK
from google.cloud import aiplatform
from vertexai.preview.vision_models import VideoGenerationModel

model = VideoGenerationModel.from_pretrained("veo-3.1-generate-preview")
operation = model.generate_video(
    prompt="...",
    output_gcs_uri="gs://bucket/output/",
    duration_seconds=8,
    aspect_ratio="16:9",
    resolution="1080p",
    include_audio=True
)
video = operation.result()
```

### MAMA Use Case
- Generate scene clips (4–8 sec each) from video script scene descriptions
- Extract frames for the Frame Combine Engine
- Use Fast tier for draft generation, Full tier for final renders

---

## 2. Kling AI (Video Generation)

### Overview
Kling AI (by Kuaishou) is a strong competitor to Sora/Veo. Kling 2.6 is the current model (late 2025). It supports both silent video and native audio generation.

### Capabilities
- **Text-to-video** and **image-to-video**
- **Resolution**: Up to 1080p at 30–48 FPS
- **Duration**: Up to 3 minutes (via video extension feature); standard clips 5–10 seconds
- **Audio**: Native audio generation (narration, ambient sound, effects) in Kling 2.6+
- **Elements feature**: Combine up to 4 reference images for character consistency across frames
- **Kling 2.5 Turbo**: 40% faster than prior versions

### Pricing (API via official or third-party, 2025)
| Clip Duration | Without Audio | With Audio |
|---|---|---|
| 5 seconds | ~$0.28 | ~$0.55 |
| 10 seconds | ~$0.55 | ~$1.10 |

**Alternative API access**: Platforms like Fal.ai and Kie.ai offer ~$0.90/10-sec clip pay-as-you-go.

### Credit Packages
- Credits must be purchased in advance
- Packages expire after **90 days** — financial risk for unused credits
- No refunds for failed generations
- Minimum significant upfront payment required

### Rate Limits & Constraints
- Generation can be **slow** (up to ~3 hours in some reported cases for high-quality)
- Asynchronous API — must poll for completion
- No per-minute rate limit published; generation queue-based
- Output: MP4 video file

### Integration Approach (MAMA)
```python
import requests

# Kling API (via official or Fal.ai proxy)
response = requests.post(
    "https://api.klingai.com/v1/videos/text2video",
    headers={"Authorization": f"Bearer {KLING_API_KEY}"},
    json={
        "model": "kling-v2-6",
        "prompt": "...",
        "duration": 10,
        "mode": "pro",
        "aspect_ratio": "16:9",
        "with_audio": True
    }
)
task_id = response.json()["data"]["task_id"]
# Poll for completion...
```

### MAMA Use Case
- Secondary/fallback video source when Veo-3 is unavailable or rate-limited
- Use for character-consistent scenes via Elements feature
- Generate action-heavy scenes that benefit from Kling's motion quality

---

## 3. Remotion (Programmatic Video Rendering)

### Overview
Remotion is an open-source React-based framework for programmatically creating videos. The development plan references "Render.io" — the closest match for programmatic video rendering with a code-based workflow is **Remotion** (remotion.dev). It uses React components + TypeScript to define video scenes and renders them server-side to MP4.

### Capabilities
- **React + TypeScript** video composition (declarative scenes, animations, timing)
- **Web technologies**: CSS, SVG, Canvas, WebGL supported
- **Server-side rendering**: Deterministic frame-by-frame rendering via headless Chromium
- **Dynamic content**: Variables, API calls, data-driven video generation
- **Remotion Lambda**: Distributed serverless rendering on AWS Lambda
- **Output**: MP4, WebM, GIF, image sequences
- **FPS Control**: Any custom FPS (typically 30 or 60)
- **Resolution**: Arbitrary (1920×1080, 1080×1920 for vertical, etc.)
- **Audio**: Supports audio mixing, sync, and voice-over tracks

### Pricing
| License | Who | Cost |
|---|---|---|
| Free | Individuals / teams ≤3 devs | Free (unlimited renders) |
| Company | Teams ≥4 devs | $25/dev/mo + $10/1000 renders (min $100/mo) |
| Enterprise | Large orgs | From $500/mo |

**Remotion Lambda rendering cost**: AWS Lambda compute charges only (~$0.001–0.005 per render depending on duration and complexity)

### Rate Limits & Constraints
- No API rate limits (self-hosted rendering)
- Limited by local CPU/GPU or AWS Lambda concurrency
- Render time: ~1–5 min for a 30-sec video on Lambda (parallel frame rendering)
- Requires Node.js 18+ environment and `ffmpeg` installed

### Integration Approach (MAMA)
```typescript
// Define a video composition in React
import { Composition } from 'remotion';
import { MyVideoScene } from './MyVideoScene';

export const Root = () => (
  <Composition
    id="MarketingVideo"
    component={MyVideoScene}
    durationInFrames={300}  // 10 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ title: "...", scenes: [] }}
  />
);

// Render via CLI or Node API
import { renderMedia, selectComposition } from '@remotion/renderer';
const composition = await selectComposition({ serveUrl, id: 'MarketingVideo' });
await renderMedia({ composition, serveUrl, codec: 'h264', outputLocation: 'out.mp4' });
```

**MAMA-specific workflow**:
1. LLM generates a **Remotion code plan** (scene layout, text overlays, timing, brand elements)
2. Plan is reviewed/validated
3. LLM writes the **Remotion React component code**
4. Remotion renders it to MP4 frames
5. Frames fed into Frame Combine Engine

### MAMA Use Case
- Brand-consistent motion graphics, lower-thirds, title cards
- Data-driven infographic animations
- Text overlays and CTA animations
- B-roll with programmatic transitions

---

## 4. ElevenLabs TTS (Audio Generation)

### Overview
ElevenLabs is the leading AI text-to-speech platform. It generates lifelike, emotionally expressive narration audio from text, supporting 70+ languages and 10,000+ voices.

### Capabilities
| Model | Latency | Languages | Max Characters | Quality |
|---|---|---|---|---|
| Eleven Flash v2.5 | ~75ms | 32 | 40,000 | Ultra-low latency |
| Eleven Turbo v2.5 | ~250–300ms | 32 | 40,000 | Balanced quality/speed |
| Eleven Multilingual v2 | ~500ms | 70+ | 10,000 | High quality, long-form |
| Eleven v3 | ~800ms | 70+ | 3,000 | Max expressiveness |

**Additional features:**
- Voice cloning (instant and professional)
- Voice design (create custom voices from text descriptions)
- 10,000+ voices in the Voice Library
- Emotional control: intonation, pacing, emphasis via SSML-like markers
- Audio output: MP3, PCM, OPUS, OGG

### Pricing (2025)
| Plan | Monthly Credits | Cost |
|---|---|---|
| Free | 10,000 chars | $0 |
| Starter | 30,000 chars | $5/mo |
| Creator | 100,000 chars | $22/mo |
| Pro | 500,000 chars | $99/mo |
| Scale | ~500,000 credits | $330/mo |
| Business | ~2M credits | $1,320/mo |
| Enterprise | Custom | Custom |

**Credit rates:**
- Standard TTS models: 1 credit/character
- Turbo models: 0.5 credits/character
- 1,000 credits ≈ 1 minute of TTS output

**Estimated cost per video**:
- Typical 60-second script (~600 words / ~3,600 characters)
- Turbo v2.5: ~1,800 credits = ~$0.36 at Pro plan rates

### Rate Limits
- Concurrency: 5 concurrent requests on standard plans
- ~100 simultaneous audio broadcasts at concurrency limit 5
- Higher concurrency available on Enterprise

### Integration Approach (MAMA)
```python
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

audio = client.generate(
    text="Your narration script here...",
    voice="Rachel",  # or custom voice ID
    model="eleven_turbo_v2_5",
    voice_settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.3,
        use_speaker_boost=True
    )
)

# Save to file
with open("narration.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)
```

### MAMA Use Case
- Generate voice-over narration from the Audio Script produced by the Video & Audio Script Separator
- Voice selection per brand persona
- Timing metadata from ElevenLabs used to sync audio with video frames

---

## 5. DALL-E 3 / GPT-Image (Image Generation)

### Overview
OpenAI's DALL-E 3 (and the newer GPT-Image-1) are the primary image generation APIs for MAMA's image post pipeline. DALL-E 3 offers superior text rendering and photorealism.

### Capabilities
- **Resolutions**: 1024×1024, 1024×1536 (portrait), 1536×1024 (landscape)
- **Quality tiers**: Standard and HD
- **Prompt adherence**: Excellent understanding of complex prompts
- **Text in images**: Better than most competitors
- **Revision**: Generates 1 image per API call (n=1 max for DALL-E 3)

### Pricing (2025)
| Quality | Resolution | Price/image |
|---|---|---|
| Standard | 1024×1024 | $0.04 |
| Standard | 1024×1792 or 1792×1024 | $0.08 |
| HD | 1024×1024 | $0.08 |
| HD | 1024×1792 or 1792×1024 | $0.12 |

### Rate Limits
- Default: 5 requests/minute (Tier 1)
- Higher tiers: Up to 100 req/min (Enterprise)
- No batch image generation (1 image per call for DALL-E 3)

### Integration Approach (MAMA)
```python
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

response = client.images.generate(
    model="dall-e-3",
    prompt="Marketing image: ...",
    size="1792x1024",
    quality="hd",
    n=1
)
image_url = response.data[0].url
```

---

## 6. Stability AI (Stable Diffusion) — Alternative Image Generation

### Overview
Stability AI's platform provides Stable Diffusion 3.5 via REST API. Useful as a fallback or for specific artistic styles.

### Pricing (2025)
| Model | Price/image |
|---|---|
| Stable Image Core | $0.03/image |
| Stable Image Ultra (SD3.5 Large) | $0.08/image |

- 1 credit = $0.01
- SD 3.0 deprecated Aug 2025; auto-upgraded to SD 3.5

---

## API Selection Summary

| Use Case | Recommended API | Fallback |
|---|---|---|
| Image Post Generation | DALL-E 3 / GPT-Image | Stable Diffusion Ultra |
| Video Scene Generation (primary) | Veo-3.1 Standard | Kling 2.6 |
| Video Scene Generation (fast/draft) | Veo-3.1 Fast | Kling 2.5 Turbo |
| Programmatic/Brand Video | Remotion + Lambda | — |
| Audio Narration | ElevenLabs Turbo v2.5 | ElevenLabs Multilingual v2 |

---

## Cost Estimate per Content Piece

### Image Post
| Item | Cost |
|---|---|
| 3 image variants (HD 1792×1024) | 3 × $0.12 = $0.36 |
| LLM calls (Claude) | ~$0.05 |
| **Total** | ~$0.41 |

### 30-Second Marketing Video
| Item | Cost |
|---|---|
| 4 × Veo-3.1 Standard clips (8s each) | 4 × 8 × $0.40 = $12.80 |
| 1 × Remotion render (Lambda) | ~$0.01 |
| ElevenLabs narration (3,600 chars Turbo) | ~$0.36 |
| LLM calls (Claude) | ~$0.20 |
| **Total** | ~$13.37 |

**With Veo-3.1 Fast:** ~$4.20/video (draft quality)

---

*Research date: February 2026*
*Sources: Google Developers Blog, Vertex AI Docs, Kling AI official pricing, Remotion.dev, ElevenLabs documentation, OpenAI pricing, Stability AI pricing*
