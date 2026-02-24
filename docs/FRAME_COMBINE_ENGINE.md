# MAMA Frame Combine Engine
## Design: Frame Collection, Ordering & Assembly

---

## Overview

The Frame Combine Engine is the core component of Phase 5 that collects raw video frames from multiple heterogeneous sources (Veo-3, Kling AI, Remotion), intelligently orders and sequences them according to the video script timeline, applies transitions, and produces a single assembled MP4 file ready for audio merging.

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Veo-3.1    │   │   Kling 2.6  │   │   Remotion   │
│  (AI Video)  │   │  (AI Video)  │   │(Programmatic)│
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────────────────────────────────────────────┐
│               Frame Extraction Layer                  │
│  ffmpeg: MP4 → PNG frame sequences + metadata        │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│               Frame Normalization Layer               │
│  Resolution, FPS, color space, orientation alignment │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│              Frame Ordering & Sequencer              │
│  Script timeline → scene assignment → frame order    │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│              Transition Effect Engine                 │
│  Cut, crossfade, fade-in/out between scene segments  │
└──────────────────────────┬───────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                Final Assembly (ffmpeg)               │
│  Frame sequences → assembled_video.mp4               │
└──────────────────────────────────────────────────────┘
```

---

## Data Structures

### FramePacket
The fundamental unit of output from each video source:

```python
@dataclass
class FramePacket:
    scene_id: str           # References scene in video script
    source: str             # "veo3" | "kling" | "remotion"
    frames_dir: str         # Local path to extracted PNG frames directory
    frame_files: list[str]  # Sorted list: ["0001.png", "0002.png", ...]
    frame_count: int
    fps: float              # Actual FPS of extracted frames
    duration: float         # Actual duration in seconds
    target_duration: float  # Expected duration from video script
    width: int
    height: int
    has_audio: bool         # Whether source clip had native audio
    audio_file: str | None  # Path to extracted audio if present
    quality_score: float    # QA score from quality validator
    metadata: dict          # Source-specific metadata
```

### SceneAssignment
Maps each scene from the video script to a FramePacket:

```python
@dataclass
class SceneAssignment:
    scene_id: str
    position: int           # Order in final video (0-indexed)
    start_time: float       # Start time in seconds in final timeline
    end_time: float         # End time in seconds in final timeline
    frame_packet: FramePacket
    transition_in: TransitionType
    transition_out: TransitionType
    transition_duration: float  # seconds (0.3–1.0s typical)
```

### TransitionType Enum
```python
class TransitionType(Enum):
    CUT = "cut"                # Instantaneous (default between AI clips)
    CROSSFADE = "crossfade"    # Blend between two clips
    FADE_BLACK = "fade_black"  # Fade to black then from black
    FADE_WHITE = "fade_white"  # Fade to white then from white
    DISSOLVE = "dissolve"      # Similar to crossfade, softer
    NONE = "none"              # First/last clip boundary
```

---

## Layer 1: Frame Extraction

### Extraction Process
For each source clip (MP4 from Veo-3, Kling, or Remotion):

```python
import subprocess
import os

def extract_frames(
    clip_path: str,
    output_dir: str,
    target_fps: float = 30.0
) -> FramePacket:
    os.makedirs(output_dir, exist_ok=True)

    # Extract frames at target FPS
    subprocess.run([
        "ffmpeg", "-i", clip_path,
        "-vf", f"fps={target_fps}",
        "-frame_pts", "1",
        f"{output_dir}/%06d.png",
        "-hide_banner", "-loglevel", "error"
    ], check=True)

    # Extract audio if present
    audio_path = None
    if _has_audio_stream(clip_path):
        audio_path = f"{output_dir}/audio.wav"
        subprocess.run([
            "ffmpeg", "-i", clip_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", audio_path,
            "-hide_banner", "-loglevel", "error"
        ], check=True)

    frames = sorted(os.listdir(output_dir))
    frames = [f for f in frames if f.endswith(".png")]

    return FramePacket(
        frames_dir=output_dir,
        frame_files=frames,
        frame_count=len(frames),
        fps=target_fps,
        duration=len(frames) / target_fps,
        has_audio=audio_path is not None,
        audio_file=audio_path,
        ...
    )
```

### Extraction Parameters
| Source | Target FPS | Format | Notes |
|---|---|---|---|
| Veo-3 | 30 | PNG | Match output FPS |
| Kling | 30 | PNG | Kling outputs 30–48fps; normalize to 30 |
| Remotion | 30 | PNG | Matches render settings |

---

## Layer 2: Frame Normalization

All frames must be normalized to a unified specification before assembly:

### Normalization Spec
```python
NORMALIZATION_TARGET = {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "color_space": "yuv420p",
    "pixel_format": "rgb24",    # for PNG frames
    "orientation": "landscape"  # 16:9 default; 9:16 for vertical
}
```

### Normalization Operations

```python
def normalize_frame(
    frame_path: str,
    output_path: str,
    target_width: int,
    target_height: int
) -> None:
    """Normalize a single frame using ffmpeg."""
    subprocess.run([
        "ffmpeg", "-i", frame_path,
        "-vf", (
            f"scale={target_width}:{target_height}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
            f"format=yuv420p"
        ),
        output_path,
        "-hide_banner", "-loglevel", "error"
    ], check=True)
```

### Normalization Cases

| Source Resolution | Action |
|---|---|
| 1920×1080 | No-op (already correct) |
| 1080×1920 (vertical) | Pad with black bars OR crop-and-scale |
| 1280×720 (720p) | Upscale with bicubic interpolation |
| Non-standard aspect | Letterbox/pillarbox to target resolution |

### FPS Normalization

```
Source FPS differs from target (30fps):
  ffmpeg -i input.mp4 -filter:v fps=30 output.mp4

Kling at 48fps → 30fps:
  Apply frame blending to avoid judder:
  ffmpeg -i input.mp4 -vf "minterpolate=fps=30:mi_mode=blend" output.mp4
```

---

## Layer 3: Frame Ordering & Sequencer

### Sequencer Algorithm

The sequencer maps the video script's scene list to collected FramePackets, producing an ordered `SceneAssignment` list.

```python
def build_scene_assignments(
    video_script: VideoScript,
    frame_packets: dict[str, FramePacket]
) -> list[SceneAssignment]:
    assignments = []
    current_time = 0.0

    for i, scene in enumerate(video_script.scenes):
        packet = frame_packets[scene.scene_id]

        # Determine transition types
        transition_in = _get_transition_in(i, video_script.scenes)
        transition_out = _get_transition_out(i, video_script.scenes)
        transition_duration = _get_transition_duration(transition_in, transition_out)

        # Adjust start time to account for transition overlap
        adjusted_start = current_time - (transition_duration / 2 if i > 0 else 0)
        adjusted_end = adjusted_start + packet.duration

        assignments.append(SceneAssignment(
            scene_id=scene.scene_id,
            position=i,
            start_time=max(0.0, adjusted_start),
            end_time=adjusted_end,
            frame_packet=packet,
            transition_in=transition_in,
            transition_out=transition_out,
            transition_duration=transition_duration
        ))

        current_time = adjusted_end

    return assignments
```

### Duration Mismatch Handling

If a generated clip's duration doesn't match the scripted duration:

```
Target: 8s | Actual: 7.2s  (under by 10%)
  → If < 15% under: freeze last frame to fill gap
  → If ≥ 15% under: flag for regeneration (quality issue)

Target: 8s | Actual: 9.1s  (over by 14%)
  → Trim last N frames: drop from frame_files list
  → Calculate trim point: 8s × 30fps = 240 frames; keep frames 0001–0240

Target: 8s | Actual: 5s  (under by 38%)
  → Regeneration required: log warning, request new generation
```

### Transition Selection Logic

```python
def _get_transition_in(
    scene_index: int,
    scenes: list[Scene]
) -> TransitionType:
    if scene_index == 0:
        return TransitionType.NONE

    prev_scene = scenes[scene_index - 1]
    curr_scene = scenes[scene_index]

    # Same source → hard cut (most natural for AI video)
    if prev_scene.source_preference == curr_scene.source_preference:
        return TransitionType.CUT

    # Programmatic → AI video: crossfade
    if prev_scene.source_preference == "remotion":
        return TransitionType.CROSSFADE

    # AI video → programmatic: fade to black
    if curr_scene.source_preference == "remotion":
        return TransitionType.FADE_BLACK

    # Different AI sources (Veo-3 → Kling): crossfade
    return TransitionType.CROSSFADE
```

---

## Layer 4: Transition Effect Engine

### Transition Implementation

Transitions are implemented as frame-level blending operations:

```python
from PIL import Image
import numpy as np

def apply_crossfade(
    frame_a: np.ndarray,  # last frames of scene A
    frame_b: np.ndarray,  # first frames of scene B
    alpha: float          # 0.0 (all A) → 1.0 (all B)
) -> np.ndarray:
    """Linear crossfade between two frames."""
    return (frame_a * (1.0 - alpha) + frame_b * alpha).astype(np.uint8)

def generate_transition_frames(
    packet_a: FramePacket,
    packet_b: FramePacket,
    transition: TransitionType,
    duration: float,    # seconds
    fps: float = 30.0
) -> list[np.ndarray]:
    n_frames = int(duration * fps)
    transition_frames = []

    # Get tail frames from A and head frames from B
    tail_a = _load_last_n_frames(packet_a, n_frames)
    head_b = _load_first_n_frames(packet_b, n_frames)

    for i in range(n_frames):
        alpha = i / (n_frames - 1)  # 0.0 → 1.0

        if transition == TransitionType.CROSSFADE:
            blended = apply_crossfade(tail_a[i], head_b[i], alpha)

        elif transition == TransitionType.FADE_BLACK:
            mid = n_frames // 2
            if i < mid:
                alpha_out = i / mid
                blended = apply_crossfade(tail_a[i], np.zeros_like(tail_a[i]), alpha_out)
            else:
                alpha_in = (i - mid) / (n_frames - mid)
                blended = apply_crossfade(np.zeros_like(head_b[i]), head_b[i], alpha_in)

        elif transition == TransitionType.CUT:
            blended = tail_a[i] if i < n_frames // 2 else head_b[i]

        transition_frames.append(blended)

    return transition_frames
```

### Transition Duration Guidelines

| Source Pair | Transition Type | Duration |
|---|---|---|
| Veo-3 → Veo-3 | CUT | 0s |
| Kling → Kling | CUT | 0s |
| Veo-3 → Kling | CROSSFADE | 0.5s |
| Kling → Veo-3 | CROSSFADE | 0.5s |
| Any AI → Remotion | FADE_BLACK | 0.6s |
| Remotion → Any AI | FADE_BLACK | 0.6s |
| First scene (in) | NONE or FADE_BLACK | 0.3s fade in |
| Last scene (out) | FADE_BLACK | 0.5s fade out |

---

## Layer 5: Final Assembly

### Assembly Algorithm

```python
def assemble_video(
    assignments: list[SceneAssignment],
    output_path: str,
    fps: float = 30.0,
    resolution: tuple[int, int] = (1920, 1080)
) -> str:
    """Assemble all scene frames into final video."""

    all_frames: list[np.ndarray] = []

    for i, assignment in enumerate(assignments):
        packet = assignment.frame_packet
        frames = _load_frame_sequence(packet)

        # Apply duration trim/pad
        frames = _adjust_duration(frames, assignment, fps)

        # Generate and insert transition frames
        if i > 0 and assignment.transition_in != TransitionType.NONE:
            prev_packet = assignments[i-1].frame_packet
            t_frames = generate_transition_frames(
                prev_packet, packet,
                assignment.transition_in,
                assignment.transition_duration,
                fps
            )
            # Remove overlap frames and insert transition
            overlap = int(assignment.transition_duration * fps / 2)
            all_frames = all_frames[:-overlap]  # trim tail of prev
            all_frames.extend(t_frames)          # add transition
            frames = frames[overlap:]            # skip head of curr

        all_frames.extend(frames)

    # Write assembled frames to video via ffmpeg
    return _frames_to_video(all_frames, output_path, fps, resolution)


def _frames_to_video(
    frames: list[np.ndarray],
    output_path: str,
    fps: float,
    resolution: tuple[int, int]
) -> str:
    """Write frame array to MP4 using ffmpeg pipe."""
    width, height = resolution
    process = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",           # High quality
        "-pix_fmt", "yuv420p",
        output_path
    ], stdin=subprocess.PIPE)

    for frame in frames:
        process.stdin.write(frame.tobytes())

    process.stdin.close()
    process.wait()
    return output_path
```

### Assembly ffmpeg Filter Alternative (Batch Mode)

For very long videos or memory-constrained environments, use concat demuxer:

```python
def assemble_via_concat_demuxer(
    assignments: list[SceneAssignment],
    output_path: str
) -> str:
    """Alternative assembly using ffmpeg concat demuxer for large videos."""

    # Build concat list file
    concat_file = "/tmp/concat_list.txt"
    with open(concat_file, "w") as f:
        for assignment in assignments:
            # Write normalized scene MP4 path
            scene_mp4 = _frames_to_scene_mp4(assignment)
            f.write(f"file '{scene_mp4}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        output_path
    ], check=True)

    return output_path
```

---

## Quality Validation

### Post-Assembly Checks

```python
@dataclass
class AssemblyQualityResult:
    total_duration: float
    target_duration: float
    duration_ok: bool           # within 2% of target
    resolution_ok: bool         # matches target resolution
    fps_ok: bool                # matches target FPS
    no_black_frames: bool       # no unexpected black frame runs > 0.5s
    no_freeze_frames: bool      # no unexpected freeze > 1s
    scene_count: int
    transition_count: int
    overall_pass: bool

def validate_assembled_video(
    video_path: str,
    script: VideoScript
) -> AssemblyQualityResult:
    probe = _ffprobe(video_path)

    return AssemblyQualityResult(
        total_duration=probe["duration"],
        target_duration=script.total_duration,
        duration_ok=abs(probe["duration"] - script.total_duration) / script.total_duration < 0.02,
        resolution_ok=probe["width"] == 1920 and probe["height"] == 1080,
        fps_ok=abs(probe["fps"] - 30.0) < 0.1,
        no_black_frames=_check_black_frames(video_path),
        no_freeze_frames=_check_freeze_frames(video_path),
        ...
    )
```

---

## Intelligent Frame Selection

For scenes where multiple generations were produced (retries, variants), select the best:

```python
def select_best_frame_packet(
    candidates: list[FramePacket],
    scene: Scene
) -> FramePacket:
    """
    Score each candidate FramePacket and select the best one.

    Scoring criteria:
    1. Quality score from automated validator (40%)
    2. Duration accuracy vs target (20%)
    3. Content alignment via LLM vision evaluation (40%)
    """
    scored = []
    for candidate in candidates:
        duration_score = 1.0 - abs(
            candidate.duration - scene.duration
        ) / scene.duration

        content_score = _llm_evaluate_content_alignment(
            candidate.frames_dir,
            scene.prompt
        )

        composite = (
            0.4 * candidate.quality_score +
            0.2 * duration_score +
            0.4 * content_score
        )
        scored.append((composite, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]
```

---

## Engine Configuration

```python
FRAME_COMBINE_CONFIG = {
    # Output specification
    "output_fps": 30,
    "output_width": 1920,
    "output_height": 1080,
    "output_codec": "libx264",
    "output_crf": 18,           # Quality level (lower = better quality)
    "output_preset": "medium",  # Encoding speed vs compression

    # Frame extraction
    "extract_format": "png",
    "extract_quality": 2,       # ffmpeg -q:v for JPEG; not used for PNG

    # Duration tolerance
    "duration_trim_threshold": 0.15,    # >15% over → trim
    "duration_pad_threshold": 0.15,     # >15% under → regenerate
    "duration_freeze_threshold": 0.10,  # <10% under → freeze last frame

    # Transitions
    "default_ai_to_ai_transition": "cut",
    "default_ai_to_programmatic_transition": "fade_black",
    "default_transition_duration": 0.5,

    # Storage
    "temp_frames_dir": "/tmp/mama_frames/",
    "assembled_output_dir": "/data/assembled/",

    # Parallelism
    "max_parallel_extractions": 4,      # Parallel ffmpeg extraction jobs
    "max_parallel_normalizations": 8,   # Parallel normalization jobs
}
```

---

## Complete Engine Flow (Pseudocode)

```
INPUT: VideoScript, frame_packets: dict[scene_id → FramePacket]

STEP 1: VALIDATE INPUTS
  - All scene_ids in script have corresponding frame_packets
  - All frame_packets have extracted frames

STEP 2: NORMALIZE ALL FRAMES (parallel)
  for each frame_packet in frame_packets.values():
    normalize_frames(frame_packet, NORMALIZATION_TARGET)

STEP 3: DURATION ADJUSTMENT
  for each (scene, frame_packet) pair:
    adjust = handle_duration_mismatch(scene.duration, frame_packet.duration)
    if adjust == REGENERATE:
      request_regeneration(scene)  # Async, wait for new packet

STEP 4: SELECT BEST CANDIDATES (if retries exist)
  for each scene with multiple candidates:
    best = select_best_frame_packet(candidates, scene)
    frame_packets[scene.scene_id] = best

STEP 5: BUILD SCENE ASSIGNMENTS
  assignments = build_scene_assignments(script, frame_packets)

STEP 6: GENERATE TRANSITION FRAMES
  for each consecutive pair in assignments:
    if transition_type != CUT and transition_type != NONE:
      generate_transition_frames(pair, transition_type, duration)

STEP 7: ASSEMBLE FINAL VIDEO
  assembled_path = assemble_video(assignments, output_path)

STEP 8: QUALITY VALIDATION
  result = validate_assembled_video(assembled_path, script)
  if not result.overall_pass:
    → identify failing scenes
    → request targeted regeneration for failing scenes
    → re-run from STEP 3 for affected scenes only

OUTPUT: assembled_video.mp4 (video only, no audio)
        → passed to Audio-Video Merger
```

---

## Storage Layout

```
/tmp/mama_frames/
  pipeline_{id}/
    scene_s1_veo3/
      000001.png
      000002.png
      ...
      audio.wav     (if native audio extracted)
    scene_s2_remotion/
      000001.png
      ...
    scene_s3_kling/
      000001.png
      ...
    transitions/
      s1_to_s2/
        000001.png
        ...
    normalized/
      scene_s1_normalized/
        000001.png
        ...

/data/assembled/
  pipeline_{id}/
    assembled_video.mp4
    quality_report.json
```

---

## Dependencies

| Dependency | Purpose |
|---|---|
| `ffmpeg` (system) | Frame extraction, normalization, assembly |
| `Pillow` (Python) | Frame-level image operations, crossfade |
| `numpy` | Fast array operations for blending |
| `ffprobe` (system) | Video metadata inspection |
| `boto3` / `google-cloud-storage` | Download source clips from cloud storage |

---

*Document created: February 2026*
