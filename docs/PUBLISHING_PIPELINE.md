# MAMA - Multi-Platform Publishing Pipeline Design

## Overview

This document defines the multi-platform publishing pipeline for MAMA. The pipeline handles content formatting, scheduling, queue management, platform-specific optimization, and post-publish tracking.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    APPROVED CONTENT                         │
│         (Image Asset OR Merged Video + Caption)             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  CONTENT FORMATTER                          │
│  - Format adaptation per platform                           │
│  - Caption truncation / platform rules                      │
│  - Hashtag selection per platform                           │
│  - Thumbnail generation (video)                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   PUBLISH QUEUE                             │
│  - Redis-backed job queue (Celery)                          │
│  - Priority scheduling                                      │
│  - Optimal time-of-day scheduling                           │
│  - Rate limit awareness                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
           ┌────────────────┼────────────────────┐
           │                │                    │
           ▼                ▼                    ▼
    IMAGE PIPELINE   VIDEO PIPELINE      BOTH PIPELINES
    ─────────────    ──────────────      ──────────────
    Instagram        Instagram Reels     (Routed by
    LinkedIn         LinkedIn Video       content type)
    Facebook         Facebook Reels
                     X / Twitter
                     YouTube Shorts
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               PLATFORM PUBLISHER WORKERS                    │
│  - Parallel publish workers per platform                    │
│  - Chunked upload handling                                  │
│  - Container ID polling (Instagram/Facebook)                │
│  - Post ID capture                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               POST-PUBLISH ACTIONS                          │
│  - Save post IDs to DB                                      │
│  - Update tracking spreadsheet                              │
│  - Trigger analytics scheduler                              │
│  - Notify coordinator agent                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Content Formatter

### 1.1 Image Formatting

The formatter produces platform-optimized versions of the approved image.

```python
IMAGE_FORMAT_SPECS = {
    "instagram": {
        "square": { "width": 1080, "height": 1080, "ratio": "1:1" },
        "portrait": { "width": 1080, "height": 1350, "ratio": "4:5" },
        "landscape": { "width": 1080, "height": 566, "ratio": "1.91:1" },
        "format": "JPEG",
        "max_size_mb": 8,
        "default_ratio": "4:5"
    },
    "linkedin": {
        "landscape": { "width": 1200, "height": 627, "ratio": "1.91:1" },
        "square": { "width": 1080, "height": 1080, "ratio": "1:1" },
        "format": "JPEG",
        "max_size_mb": 5,
        "default_ratio": "1.91:1"
    },
    "facebook": {
        "landscape": { "width": 1200, "height": 630, "ratio": "1.91:1" },
        "square": { "width": 1080, "height": 1080, "ratio": "1:1" },
        "format": "JPEG",
        "max_size_mb": 30,
        "default_ratio": "1.91:1"
    }
}
```

**Processing Steps:**
1. Receive approved image (source format: PNG or JPEG, typically 1080×1080+)
2. For each target platform, resize/crop to target dimensions
3. Convert to JPEG at 85–95% quality for optimal size/quality
4. Validate file size against per-platform limits
5. Store formatted variants in S3/GCS under `assets/{content_id}/formatted/`

### 1.2 Video Formatting

The formatter adapts the merged video output for each platform.

```python
VIDEO_FORMAT_SPECS = {
    "instagram_reels": {
        "width": 1080, "height": 1920, "ratio": "9:16",
        "max_duration_s": 90, "min_duration_s": 3,
        "format": "mp4", "codec": "h264", "audio": "aac",
        "max_size_mb": 1000, "fps": 30
    },
    "linkedin_video": {
        "width": 1920, "height": 1080, "ratio": "16:9",
        "portrait_width": 1080, "portrait_height": 1920,
        "max_duration_s": 600, "min_duration_s": 3,
        "format": "mp4", "codec": "h264", "audio": "aac",
        "max_size_mb": 5000
    },
    "facebook_reels": {
        "width": 1080, "height": 1920, "ratio": "9:16",
        "max_duration_s": 90, "min_duration_s": 3,
        "format": "mp4", "codec": "h264", "audio": "aac",
        "max_size_mb": 1000, "fps": 30
    },
    "twitter_video": {
        "width": 1080, "height": 1920, "ratio": "9:16",
        "max_duration_s": 140, "format": "mp4",
        "codec": "h264", "max_size_mb": 512
    },
    "youtube_shorts": {
        "width": 1080, "height": 1920, "ratio": "9:16",
        "max_duration_s": 60, "format": "mp4",
        "codec": "h264", "audio": "aac", "fps": 30
    }
}
```

**FFmpeg Transcode Command Template:**
```bash
ffmpeg -i {input_path} \
  -vf "scale={width}:{height}:force_original_aspect_ratio=decrease,\
       pad={width}:{height}:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  -t {max_duration} \
  {output_path}
```

### 1.3 Caption & Hashtag Formatting

```python
CAPTION_RULES = {
    "instagram": {
        "max_chars": 2200,
        "max_hashtags": 30,
        "hashtag_strategy": "end_of_caption",
        "mention_limit": 20
    },
    "linkedin": {
        "max_chars": 3000,
        "max_hashtags": 5,
        "hashtag_strategy": "inline_or_end",
        "professional_tone": True
    },
    "facebook": {
        "max_chars": 63206,
        "max_hashtags": 15,  # recommended, no hard limit
        "hashtag_strategy": "end_of_caption"
    },
    "twitter": {
        "max_chars": 280,
        "hashtag_strategy": "inline",
        "note": "hashtags count toward char limit",
        "max_media": 4
    },
    "youtube": {
        "title_max_chars": 100,
        "description_max_chars": 5000,
        "max_tags": 50,
        "tags_total_chars": 500,
        "hashtags_in_description": True,
        "shorts_hashtag": "#Shorts"  # Required for Shorts classification
    }
}
```

**Caption Generation Pipeline:**
1. Base caption from approved script (generated by CMI/CST/VST agent)
2. Platform-specific truncation if over limit
3. Hashtag pool selection from CMI ideation output (ranked by relevance)
4. Per-platform hashtag count enforcement
5. YouTube title extraction (first sentence / AI-generated title)
6. YouTube `#Shorts` tag appended automatically for short videos

---

## 2. Publish Queue Design

### 2.1 Queue Architecture

**Technology**: Celery + Redis (as broker) + PostgreSQL (result backend)

```
Redis Queue
├── queue:high_priority     → Human-approved urgent posts
├── queue:scheduled         → Time-scheduled posts
├── queue:default           → Standard async posts
└── queue:retry             → Failed posts awaiting retry
```

### 2.2 Job Schema

```python
@dataclass
class PublishJob:
    job_id: str                    # UUID
    content_id: str                # FK to content table
    platform: str                  # instagram|linkedin|facebook|twitter|youtube
    content_type: str              # image|video|reel|short
    scheduled_at: datetime         # When to publish (None = immediate)
    asset_path: str                # S3/GCS path to formatted asset
    caption: str                   # Platform-formatted caption
    metadata: dict                 # Platform-specific extras (tags, title, etc.)
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"        # pending|processing|published|failed
    created_at: datetime = now()
    published_at: datetime = None
    platform_post_id: str = None   # ID returned by platform after publish
    error_message: str = None
```

### 2.3 Optimal Posting Times

```python
OPTIMAL_POST_TIMES = {
    "instagram": {
        "weekdays": ["08:00", "12:00", "17:00", "19:00"],
        "weekends": ["10:00", "14:00"],
        "timezone": "America/New_York"
    },
    "linkedin": {
        "weekdays": ["07:30", "10:00", "12:00", "17:00"],
        "weekends": [],  # Lower engagement on weekends
        "timezone": "America/New_York"
    },
    "facebook": {
        "weekdays": ["09:00", "13:00", "15:00"],
        "weekends": ["12:00", "14:00"],
        "timezone": "America/New_York"
    },
    "twitter": {
        "weekdays": ["08:00", "12:00", "17:00", "20:00"],
        "weekends": ["10:00", "15:00"],
        "timezone": "America/New_York"
    },
    "youtube": {
        "weekdays": ["14:00", "15:00", "16:00"],
        "weekends": ["11:00", "12:00"],
        "timezone": "America/New_York"
    }
}
```

### 2.4 Rate Limit Tracking

```python
# Redis-backed rate limit tracker
RATE_LIMITS = {
    "instagram": { "posts_per_day": 50, "api_per_hour": 200 },
    "linkedin":  { "posts_per_day": 100, "api_per_day": 500 },
    "facebook":  { "posts_per_day": 50, "api_per_hour": 200 },
    "twitter":   { "tweets_per_15min": 300, "media_per_15min": 30 },
    "youtube":   { "quota_units_per_day": 10000, "upload_cost": 1600 }
}
```

Rate limit state tracked in Redis with TTL-based keys:
```
rate_limit:{platform}:posts:{date}     → current count
rate_limit:{platform}:api:{hour}       → API call count
rate_limit:youtube:quota:{date}        → units consumed
```

---

## 3. Platform Publisher Workers

### 3.1 Worker Architecture

Each platform has a dedicated Celery worker class:

```
workers/
├── instagram_publisher.py
├── linkedin_publisher.py
├── facebook_publisher.py
├── twitter_publisher.py
└── youtube_publisher.py
```

All workers inherit from `BasePlatformPublisher`:

```python
class BasePlatformPublisher:
    def publish(self, job: PublishJob) -> PublishResult
    def upload_media(self, asset_path: str) -> str  # returns media ID
    def create_post(self, media_id: str, caption: str) -> str  # returns post ID
    def verify_publish(self, post_id: str) -> bool
    def handle_error(self, error: Exception, job: PublishJob) -> None
```

### 3.2 Instagram Publisher Flow

```python
async def publish_instagram(job: PublishJob) -> PublishResult:
    # 1. Upload to Instagram container
    container = await create_media_container(
        ig_user_id=config.INSTAGRAM_USER_ID,
        media_type="REELS" if job.content_type == "reel" else "IMAGE",
        asset_url=get_public_url(job.asset_path),
        caption=job.caption
    )

    # 2. Poll for container readiness (max 5 minutes)
    await poll_container_status(container.id, timeout=300)

    # 3. Publish
    post_id = await publish_container(container.id)
    return PublishResult(platform="instagram", post_id=post_id)
```

### 3.3 LinkedIn Publisher Flow

```python
async def publish_linkedin(job: PublishJob) -> PublishResult:
    if job.content_type == "video":
        # Register upload
        upload_info = await register_video_upload(
            owner=f"urn:li:organization:{config.LINKEDIN_ORG_ID}"
        )
        # Upload video binary
        await upload_video_binary(upload_info.upload_url, job.asset_path)
        # Wait for processing
        await wait_for_asset_ready(upload_info.asset_urn)
        # Create post
        post_id = await create_video_post(
            asset_urn=upload_info.asset_urn,
            text=job.caption
        )
    else:
        # Image post
        asset_urn = await upload_image(job.asset_path)
        post_id = await create_image_post(asset_urn=asset_urn, text=job.caption)
    return PublishResult(platform="linkedin", post_id=post_id)
```

### 3.4 Twitter Publisher Flow

```python
async def publish_twitter(job: PublishJob) -> PublishResult:
    # Chunked media upload
    media_id = await chunked_media_upload(
        file_path=job.asset_path,
        media_type="video/mp4" if job.content_type == "video" else "image/jpeg"
    )

    # Poll media processing (for video)
    if job.content_type == "video":
        await poll_media_processing(media_id, timeout=300)

    # Create tweet
    tweet_id = await create_tweet(
        text=job.caption[:280],
        media_ids=[media_id]
    )
    return PublishResult(platform="twitter", post_id=tweet_id)
```

### 3.5 YouTube Publisher Flow

```python
async def publish_youtube(job: PublishJob) -> PublishResult:
    # Initialize resumable upload session
    upload_url = await initialize_upload_session(
        title=job.metadata.get("title"),
        description=job.caption,
        tags=job.metadata.get("tags", []),
        privacy_status="public",
        category_id="22"  # People & Blogs
    )

    # Resumable chunked upload (10MB chunks)
    video_id = await resumable_upload(
        upload_url=upload_url,
        file_path=job.asset_path,
        chunk_size_mb=10
    )

    # Wait for processing
    await wait_for_video_processing(video_id, timeout=3600)
    return PublishResult(platform="youtube", post_id=video_id)
```

---

## 4. Error Handling & Retry Strategy

### 4.1 Retry Configuration

```python
@celery.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(RateLimitError, TemporaryAPIError),
    retry_backoff=True,
    retry_backoff_max=3600
)
def publish_task(self, job_id: str):
    job = get_job(job_id)
    try:
        result = publisher.publish(job)
        mark_published(job, result)
    except RateLimitError as e:
        retry_after = e.retry_after or 900
        raise self.retry(countdown=retry_after)
    except PermanentPublishError as e:
        mark_failed(job, error=str(e))
        alert_team(job, e)
```

### 4.2 Dead Letter Queue

Failed jobs (all retries exhausted) are moved to `queue:dead_letter` with full error context. Dead letter queue is monitored and alerts are sent to Slack/email.

### 4.3 Duplicate Detection

Before publishing, check Redis for recently published content:
```python
def check_duplicate(content_id: str, platform: str) -> bool:
    key = f"published:{platform}:{content_id}"
    return redis.exists(key)

def mark_published_cache(content_id: str, platform: str):
    key = f"published:{platform}:{content_id}"
    redis.setex(key, 86400, "1")  # 24h TTL
```

---

## 5. System & Sheet Integration

### 5.1 Content Tracking Database Schema

```sql
-- Core content table
CREATE TABLE content_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      VARCHAR(100) UNIQUE NOT NULL,
    topic           TEXT,
    content_type    VARCHAR(20),     -- 'image' | 'video'
    script_text     TEXT,
    approved_at     TIMESTAMPTZ,
    approved_by     VARCHAR(100),    -- agent ID or 'human'
    asset_s3_path   TEXT,
    thumbnail_path  TEXT,
    status          VARCHAR(30),     -- 'approved' | 'publishing' | 'published' | 'failed'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Per-platform publish records
CREATE TABLE platform_posts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      VARCHAR(100) REFERENCES content_posts(content_id),
    platform        VARCHAR(30),     -- 'instagram' | 'linkedin' | 'facebook' | 'twitter' | 'youtube'
    platform_post_id VARCHAR(200),   -- ID from platform API
    platform_url    TEXT,            -- Direct URL to post
    post_type       VARCHAR(30),     -- 'image' | 'reel' | 'video' | 'short' | 'tweet'
    caption_used    TEXT,
    hashtags_used   TEXT[],
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    status          VARCHAR(20),     -- 'pending' | 'published' | 'failed'
    error_message   TEXT,
    retry_count     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics snapshots
CREATE TABLE post_analytics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_post_id VARCHAR(200),
    platform        VARCHAR(30),
    captured_at     TIMESTAMPTZ DEFAULT NOW(),
    views           BIGINT DEFAULT 0,
    impressions     BIGINT DEFAULT 0,
    likes           BIGINT DEFAULT 0,
    comments        BIGINT DEFAULT 0,
    shares          BIGINT DEFAULT 0,
    saves           BIGINT DEFAULT 0,
    reach           BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,4),
    clicks          BIGINT DEFAULT 0,
    video_views     BIGINT DEFAULT 0,
    watch_time_sec  BIGINT DEFAULT 0,
    raw_data        JSONB
);
```

### 5.2 Google Sheets / Spreadsheet Integration

MAMA maintains a tracking spreadsheet with the following structure:

**Sheet: "Content Pipeline"**
| Column | Field | Auto-Updated |
|---|---|---|
| A | Content ID | ✓ |
| B | Topic | ✓ |
| C | Content Type | ✓ |
| D | Created Date | ✓ |
| E | Script Status | ✓ |
| F | Approved By | ✓ |
| G | Asset URL | ✓ |
| H | Instagram Status | ✓ |
| I | LinkedIn Status | ✓ |
| J | Facebook Status | ✓ |
| K | Twitter Status | ✓ |
| L | YouTube Status | ✓ |
| M | Instagram Post URL | ✓ |
| N | LinkedIn Post URL | ✓ |
| O | YouTube Video URL | ✓ |
| P | Total Engagement (24h) | ✓ |

**Sheet Update Triggers:**
- On content creation → add row
- On script approval → update script status column
- On publish → update platform status + URL
- On analytics capture → update engagement column

**Integration Method**: Google Sheets API v4 via service account credentials.

```python
async def update_sheet_row(content_id: str, updates: dict):
    sheet = await get_sheet_client()
    row = await find_row_by_content_id(sheet, content_id)
    await sheet.update_cells(row, updates)
```

---

## 6. Monitoring Dashboard Requirements

### 6.1 Key Metrics to Monitor

**Pipeline Health Metrics:**
- Jobs in queue by status (pending / processing / published / failed)
- Jobs per platform per hour
- Average publish latency per platform
- API rate limit utilization (% of limit used)
- Daily quota consumption (YouTube)
- Error rate per platform
- Retry rate

**Content Performance Metrics (post-publish):**
- Total posts published today / week / month
- Engagement rate by platform (avg)
- Top performing content by engagement
- Cost per content piece (API cost breakdown)

### 6.2 Grafana Dashboard Panels

```yaml
Dashboard: "MAMA Publishing Pipeline"
Panels:
  - name: "Queue Depth"
    type: gauge
    metric: mama_queue_depth{queue="default"}
    thresholds: [warn: 50, critical: 200]

  - name: "Publish Rate"
    type: timeseries
    metric: rate(mama_posts_published_total[5m])
    labels: [platform]

  - name: "API Rate Limit Usage"
    type: bargauge
    metrics:
      - mama_api_calls_used{platform="instagram"} / 200
      - mama_api_calls_used{platform="linkedin"} / 500
      - mama_api_calls_used{platform="twitter"} / 300

  - name: "Error Rate by Platform"
    type: timeseries
    metric: rate(mama_publish_errors_total[15m])
    labels: [platform, error_type]

  - name: "YouTube Quota Remaining"
    type: stat
    metric: 10000 - mama_youtube_quota_used_total
    thresholds: [warn: 3000, critical: 1000]

  - name: "End-to-End Pipeline Time"
    type: histogram
    metric: mama_pipeline_duration_seconds
    percentiles: [p50, p95, p99]
```

### 6.3 Prometheus Metrics

```python
# metrics.py
from prometheus_client import Counter, Gauge, Histogram

POSTS_PUBLISHED = Counter(
    'mama_posts_published_total',
    'Total posts published',
    ['platform', 'content_type']
)

PUBLISH_ERRORS = Counter(
    'mama_publish_errors_total',
    'Total publish errors',
    ['platform', 'error_type']
)

QUEUE_DEPTH = Gauge(
    'mama_queue_depth',
    'Current jobs in queue',
    ['queue', 'status']
)

PUBLISH_DURATION = Histogram(
    'mama_publish_duration_seconds',
    'Time to publish to platform',
    ['platform'],
    buckets=[5, 15, 30, 60, 120, 300, 600]
)

PIPELINE_DURATION = Histogram(
    'mama_pipeline_duration_seconds',
    'End-to-end pipeline duration',
    ['content_type'],
    buckets=[60, 300, 900, 1800, 3600, 7200]
)

API_RATE_LIMIT_USAGE = Gauge(
    'mama_api_calls_used',
    'API calls consumed this period',
    ['platform', 'period']
)
```

### 6.4 Alerting Rules

```yaml
# alerts.yaml
groups:
  - name: mama_publishing
    rules:
      - alert: HighPublishErrorRate
        expr: rate(mama_publish_errors_total[5m]) > 0.1
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "High publish error rate on {{ $labels.platform }}"

      - alert: QueueDepthCritical
        expr: mama_queue_depth{status="pending"} > 200
        for: 10m
        labels: { severity: critical }

      - alert: YouTubeQuotaLow
        expr: 10000 - mama_youtube_quota_used_total < 1600
        for: 1m
        labels: { severity: warning }
        annotations:
          summary: "YouTube quota nearly exhausted (< 1 upload remaining)"

      - alert: PublishWorkerDown
        expr: up{job="mama_workers"} == 0
        for: 2m
        labels: { severity: critical }

      - alert: TokenExpirySoon
        expr: mama_token_expiry_seconds < 86400
        for: 1m
        labels: { severity: warning }
        annotations:
          summary: "{{ $labels.platform }} access token expires in < 24h"
```

---

## 7. Pipeline Configuration

```yaml
# publishing_config.yaml
publishing:
  default_timezone: "America/New_York"
  max_concurrent_publishes: 5
  enable_optimal_scheduling: true
  retry_failed_after_hours: 1

  platforms:
    instagram:
      enabled: true
      content_types: [image, reel]
      daily_limit: 3
      publish_window: "08:00-22:00"

    linkedin:
      enabled: true
      content_types: [image, video]
      daily_limit: 2
      publish_window: "07:00-19:00"
      publish_weekdays_only: true

    facebook:
      enabled: true
      content_types: [image, reel]
      daily_limit: 3
      publish_window: "08:00-21:00"

    twitter:
      enabled: true
      content_types: [image, video]
      daily_limit: 5
      publish_window: "07:00-23:00"

    youtube:
      enabled: true
      content_types: [video]
      daily_limit: 2
      publish_window: "12:00-18:00"

  notifications:
    on_success: true
    on_failure: true
    channels: [slack, email]
    slack_webhook: "${SLACK_WEBHOOK_URL}"
```

---

*Last updated: February 2026*
