# MAMA - Analytics Tracking Design

## Overview

This document defines the analytics capture, storage, and reporting architecture for MAMA. The analytics system tracks post performance across all platforms, feeds data back into the content strategy loop, and provides dashboards for human review.

---

## 1. Analytics Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  PLATFORM APIS (Insights)                    │
│  Instagram Insights / LinkedIn Analytics / Twitter Metrics   │
│  Facebook Insights / YouTube Analytics                       │
└───────────────────────────┬──────────────────────────────────┘
                            │ scheduled polling
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              ANALYTICS COLLECTOR (Celery Beat)               │
│  - Polls platform APIs at intervals (1h, 24h, 7d, 28d)      │
│  - Captures raw metrics                                      │
│  - Normalizes to unified schema                              │
└───────────────────────────┬──────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────┐      ┌────────────────────────┐
│  PostgreSQL DB      │      │  Time-Series Store      │
│  (post_analytics    │      │  (TimescaleDB or        │
│   snapshots,        │      │   InfluxDB)             │
│   aggregates)       │      │  (hourly metrics)       │
└─────────────────────┘      └────────────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              ANALYTICS API / REPORTING LAYER                 │
│  - REST API for dashboard queries                            │
│  - Grafana data source                                       │
│  - Google Sheets export                                      │
│  - CMI feedback loop                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Metrics to Capture Per Platform

### 2.1 Universal Metrics (All Platforms)

| Metric | Field Name | Type | Description |
|---|---|---|---|
| Views | `views` | INT | Total views / impressions |
| Impressions | `impressions` | INT | Times content was displayed |
| Likes | `likes` | INT | Like/reaction count |
| Comments | `comments` | INT | Comment count |
| Shares | `shares` | INT | Share/repost/retweet count |
| Saves | `saves` | INT | Save/bookmark count |
| Reach | `reach` | INT | Unique accounts reached |
| Engagement Rate | `engagement_rate` | DECIMAL | (likes+comments+shares)/reach |
| Link Clicks | `clicks` | INT | CTA / link clicks |

### 2.2 Instagram-Specific Metrics

| Metric | API Field | Capture Interval |
|---|---|---|
| Impressions | `impressions` | 1h, 24h, 7d |
| Reach | `reach` | 1h, 24h, 7d |
| Likes | `like_count` | 1h, 24h |
| Comments | `comments_count` | 1h, 24h |
| Saves | `saved` | 24h, 7d |
| Video Views | `video_views` | 1h, 24h (Reels) |
| Plays | `plays` | 1h, 24h (Reels) |
| Total Interactions | `total_interactions` | 24h |
| Profile Visits | `profile_visits` | 24h |
| Follow from Post | `follows` | 24h |
| Reel Average Watch % | `ig_reels_avg_watch_time` | 24h |

**API Endpoint:**
```
GET /{ig-media-id}/insights?metric=impressions,reach,likes,saved,video_views&period=lifetime
GET /{ig-media-id}/insights?metric=plays,ig_reels_avg_watch_time&period=lifetime
```

### 2.3 LinkedIn-Specific Metrics

| Metric | API Field | Capture Interval |
|---|---|---|
| Impressions | `impressionCount` | 24h, 7d |
| Unique Impressions | `uniqueImpressionsCount` | 24h, 7d |
| Clicks | `clickCount` | 24h, 7d |
| Likes | `likeCount` | 24h, 7d |
| Comments | `commentCount` | 24h |
| Shares | `shareCount` | 24h |
| Engagement Rate | `engagement` | 24h, 7d |
| Video Views | `videoViews` | 24h (video posts) |
| Video Completions | `videoCompletions` | 24h |

**API Endpoint:**
```
GET /organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity={orgUrn}&shares[0]={shareUrn}
```

### 2.4 Facebook-Specific Metrics

| Metric | API Field | Capture Interval |
|---|---|---|
| Post Impressions | `post_impressions` | 24h, 28d |
| Post Reach | `post_reach` | 24h, 28d |
| Post Engagements | `post_engaged_users` | 24h, 28d |
| Post Reactions | `post_reactions_by_type_total` | 24h |
| Video Views (3s) | `post_video_views` | 24h (video) |
| Video Views (10s) | `post_video_views_10s` | 24h (video) |
| Average Watch Time | `post_video_avg_time_watched` | 24h (video) |
| Link Clicks | `post_clicks_by_type` | 24h |

**API Endpoint:**
```
GET /{post-id}/insights?metric=post_impressions,post_reach,post_engaged_users,post_video_views
```

### 2.5 Twitter / X-Specific Metrics

| Metric | API Field | Capture Interval |
|---|---|---|
| Impressions | `impression_count` | 1h, 24h |
| Likes | `like_count` | 1h, 24h |
| Retweets | `retweet_count` | 1h, 24h |
| Replies | `reply_count` | 1h, 24h |
| Quote Tweets | `quote_count` | 24h |
| Bookmarks | `bookmark_count` | 24h |
| URL Clicks | `url_link_clicks` | 24h (requires Elevated access) |
| Profile Clicks | `user_profile_clicks` | 24h |

**API Endpoint:**
```
GET /2/tweets/{id}?tweet.fields=public_metrics,non_public_metrics,organic_metrics
```

*Note: non_public_metrics requires OAuth 1.0a user context (not app-only)*

### 2.6 YouTube-Specific Metrics

| Metric | API Field | Capture Interval |
|---|---|---|
| Views | `views` | 1h, 24h, 7d, 28d |
| Likes | `likes` | 24h, 7d |
| Comments | `comments` | 24h, 7d |
| Shares | `shares` | 24h, 7d |
| Watch Time (minutes) | `estimatedMinutesWatched` | 24h, 7d |
| Average View Duration | `averageViewDuration` | 24h, 7d |
| Average View % | `averageViewPercentage` | 7d |
| Subscribers Gained | `subscribersGained` | 24h |
| Impressions (YouTube) | `impressions` | 24h, 7d |
| Click-Through Rate | `impressionsClickThroughRate` | 24h, 7d |

**API Endpoint:**
```
GET /youtube/analytics/v2/reports
  ?ids=channel==MINE
  &metrics=views,likes,comments,estimatedMinutesWatched,averageViewDuration
  &dimensions=video
  &filters=video=={videoId}
```

---

## 3. Data Storage Design

### 3.1 Analytics Database Schema

```sql
-- Raw snapshots from API polling
CREATE TABLE post_analytics_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform_post_id    VARCHAR(200) NOT NULL,
    content_id          VARCHAR(100) NOT NULL,
    platform            VARCHAR(30) NOT NULL,
    snapshot_type       VARCHAR(20) NOT NULL,  -- '1h' | '24h' | '7d' | '28d' | 'lifetime'
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Universal metrics
    views               BIGINT DEFAULT 0,
    impressions         BIGINT DEFAULT 0,
    reach               BIGINT DEFAULT 0,
    likes               BIGINT DEFAULT 0,
    comments            BIGINT DEFAULT 0,
    shares              BIGINT DEFAULT 0,
    saves               BIGINT DEFAULT 0,
    clicks              BIGINT DEFAULT 0,
    engagement_rate     DECIMAL(8, 6),

    -- Video-specific
    video_views         BIGINT DEFAULT 0,
    watch_time_seconds  BIGINT DEFAULT 0,
    avg_view_percent    DECIMAL(5, 2),
    completions         BIGINT DEFAULT 0,

    -- Platform-specific overflow
    raw_metrics         JSONB,

    UNIQUE(platform_post_id, platform, snapshot_type, captured_at::date)
);

-- Aggregated performance scores for CMI feedback
CREATE TABLE content_performance_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      VARCHAR(100) UNIQUE NOT NULL,
    topic           TEXT,
    content_type    VARCHAR(20),
    scored_at       TIMESTAMPTZ DEFAULT NOW(),

    -- Aggregated across platforms
    total_reach     BIGINT DEFAULT 0,
    total_views     BIGINT DEFAULT 0,
    total_likes     BIGINT DEFAULT 0,
    total_comments  BIGINT DEFAULT 0,
    total_shares    BIGINT DEFAULT 0,
    avg_engagement  DECIMAL(8, 6),

    -- Per-platform breakdown
    platform_scores JSONB,  -- { "instagram": { score: 8.5, ... }, ... }

    -- Derived performance tier
    performance_tier VARCHAR(20),  -- 'viral' | 'high' | 'medium' | 'low'
    performance_score DECIMAL(5, 2)  -- 0-100 composite score
);

-- Analytics collection job log
CREATE TABLE analytics_collection_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform        VARCHAR(30),
    post_count      INT,
    success_count   INT,
    error_count     INT,
    duration_ms     INT,
    run_at          TIMESTAMPTZ DEFAULT NOW(),
    errors          JSONB
);
```

### 3.2 TimescaleDB Hypertable (for time-series queries)

```sql
-- Convert snapshots table to TimescaleDB hypertable for efficient time queries
SELECT create_hypertable('post_analytics_snapshots', 'captured_at');

-- Create retention policy (keep raw data for 90 days, then aggregate)
SELECT add_retention_policy('post_analytics_snapshots', INTERVAL '90 days');

-- Create continuous aggregate for daily rollups
CREATE MATERIALIZED VIEW daily_platform_analytics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', captured_at) AS bucket,
    platform,
    SUM(views) AS total_views,
    SUM(likes) AS total_likes,
    SUM(comments) AS total_comments,
    AVG(engagement_rate) AS avg_engagement_rate,
    COUNT(DISTINCT platform_post_id) AS post_count
FROM post_analytics_snapshots
GROUP BY bucket, platform
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_platform_analytics',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
```

---

## 4. Analytics Collection Schedule

### 4.1 Polling Schedule (Celery Beat)

```python
ANALYTICS_SCHEDULE = {
    # 1-hour snapshots for first 48h after publish
    "collect_1h_snapshots": {
        "task": "analytics.collect_recent_posts",
        "schedule": crontab(minute=0),  # every hour
        "kwargs": { "max_age_hours": 48, "snapshot_type": "1h" }
    },

    # 24-hour snapshots for first 30 days
    "collect_daily_snapshots": {
        "task": "analytics.collect_all_posts",
        "schedule": crontab(hour=3, minute=0),  # daily at 3am
        "kwargs": { "max_age_days": 30, "snapshot_type": "24h" }
    },

    # 7-day rollup snapshots
    "collect_weekly_snapshots": {
        "task": "analytics.collect_all_posts",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),  # weekly Monday
        "kwargs": { "snapshot_type": "7d" }
    },

    # Feed performance data back to CMI
    "update_cmi_performance_context": {
        "task": "analytics.generate_performance_report",
        "schedule": crontab(hour=6, minute=0),  # daily at 6am
    },

    # Update tracking spreadsheet
    "sync_to_sheets": {
        "task": "analytics.sync_analytics_to_sheet",
        "schedule": crontab(hour=7, minute=0),  # daily at 7am
    }
}
```

### 4.2 Smart Collection (Adaptive Polling)

For newly published posts, increase polling frequency based on velocity:

```python
def get_poll_interval(post_age_hours: int, current_velocity: float) -> int:
    """Returns next poll interval in minutes."""
    if post_age_hours < 1:
        return 15      # First hour: every 15 minutes
    elif post_age_hours < 6:
        return 30      # First 6 hours: every 30 minutes
    elif post_age_hours < 24:
        return 60      # First day: hourly
    elif post_age_hours < 72:
        return 360     # First 3 days: every 6 hours
    else:
        return 1440    # After 3 days: daily
```

---

## 5. Performance Scoring Model

### 5.1 Composite Score Calculation

Each published piece of content receives a composite performance score (0–100) after 24 hours:

```python
PLATFORM_WEIGHTS = {
    "instagram":  0.30,
    "youtube":    0.25,
    "linkedin":   0.20,
    "facebook":   0.15,
    "twitter":    0.10
}

METRIC_WEIGHTS = {
    "engagement_rate":  0.40,
    "reach":            0.25,
    "views":            0.20,
    "shares":           0.10,
    "saves":            0.05
}

def calculate_performance_score(content_id: str) -> float:
    """
    Returns 0-100 score based on weighted platform + metric performance.
    Score is relative to account's historical average (z-score normalized).
    """
    snapshots = get_24h_snapshots(content_id)
    platform_scores = {}

    for platform, metrics in snapshots.items():
        baseline = get_platform_baseline(platform)  # historical avg
        normalized = {}
        for metric, weight in METRIC_WEIGHTS.items():
            value = metrics.get(metric, 0)
            avg = baseline.get(metric, 1)
            normalized[metric] = min((value / avg) * weight * 100, 100)
        platform_scores[platform] = sum(normalized.values())

    # Weighted average across platforms
    total_score = sum(
        platform_scores.get(p, 0) * w
        for p, w in PLATFORM_WEIGHTS.items()
    )
    return round(min(total_score, 100), 2)
```

### 5.2 Performance Tiers

| Tier | Score Range | Action |
|---|---|---|
| `viral` | 85–100 | Flag for CMI, boost similar content ideas |
| `high` | 65–84 | Good performance, replicate strategy |
| `medium` | 40–64 | Average, no special action |
| `low` | 20–39 | Below average, analyze why |
| `poor` | 0–19 | Flag for review, avoid similar approach |

---

## 6. CMI Feedback Loop

Analytics data feeds back into the Content Marketing Ideator (CMI) to improve future content:

```python
class CMIPerformanceFeedback:
    """Provides analytics context to CMI agent for better ideation."""

    def get_top_performing_topics(self, days: int = 30) -> list[dict]:
        """Returns topics with highest avg engagement in last N days."""
        return db.query("""
            SELECT topic, AVG(performance_score) as avg_score,
                   COUNT(*) as post_count
            FROM content_performance_scores
            WHERE scored_at > NOW() - INTERVAL '{days} days'
            GROUP BY topic
            ORDER BY avg_score DESC
            LIMIT 10
        """)

    def get_best_content_formats(self) -> dict:
        """Returns which content_type performs best per platform."""
        return db.query("""
            SELECT content_type, platform, AVG(engagement_rate) as avg_eng
            FROM content_performance_scores cps
            JOIN post_analytics_snapshots pas USING (content_id)
            GROUP BY content_type, platform
            ORDER BY avg_eng DESC
        """)

    def get_optimal_posting_times(self) -> dict:
        """Returns best posting hours based on historical performance."""
        ...

    def generate_context_prompt(self) -> str:
        """Generates a performance context string for CMI prompt injection."""
        top_topics = self.get_top_performing_topics()
        best_formats = self.get_best_content_formats()

        return f"""
        ## Recent Performance Context
        Top performing topics: {[t['topic'] for t in top_topics[:5]]}
        Best performing format: {best_formats[0]['content_type']} on {best_formats[0]['platform']}
        Avg engagement rate (30d): {self.get_avg_engagement(30):.2%}

        Use this context to prioritize similar content strategies.
        """
```

---

## 7. Reporting & Export

### 7.1 Daily Report Email

Automated daily report sent at 8am:

```
MAMA Daily Report — {date}

📊 Posts Published Yesterday: {count}
   • Instagram: {n} posts/reels
   • LinkedIn: {n} posts
   • Facebook: {n} posts/reels
   • Twitter: {n} tweets
   • YouTube: {n} shorts

📈 Top Performer: "{topic}" (score: {score}/100)
   Reach: {reach:,} | Likes: {likes:,} | Shares: {shares:,}

📉 Underperformer: "{topic}" (score: {score}/100)
   Suggested action: Review caption strategy

💰 API Cost Yesterday: ${cost:.2f}
   • Video gen: ${video_cost:.2f}
   • Image gen: ${image_cost:.2f}
   • LLM: ${llm_cost:.2f}
   • Publishing APIs: ${api_cost:.2f}

🔄 Pipeline Status: {status}
   • Queue depth: {queue_depth} items
   • Errors: {error_count}
```

### 7.2 Reporting API Endpoints

```python
# REST API for dashboard and sheet sync
GET  /api/analytics/posts?platform=&days=&limit=
GET  /api/analytics/posts/{content_id}
GET  /api/analytics/summary?period=daily|weekly|monthly
GET  /api/analytics/top?metric=engagement&limit=10
GET  /api/analytics/platforms/comparison
POST /api/analytics/export/csv
POST /api/analytics/export/sheets
```

### 7.3 Google Sheets Sync

Automatically pushes analytics to the tracking spreadsheet:

**Sheet: "Analytics" columns:**
| Col | Field | Update Frequency |
|---|---|---|
| A | Content ID | On creation |
| B | Platform | On publish |
| C | Published Date | On publish |
| D | Views (24h) | Daily |
| E | Likes (24h) | Daily |
| F | Comments (24h) | Daily |
| G | Shares (24h) | Daily |
| H | Engagement Rate | Daily |
| I | Reach (24h) | Daily |
| J | Video Views (24h) | Daily (if video) |
| K | Watch Time (min) | Daily (if video) |
| L | Performance Score | Daily |
| M | Performance Tier | Daily |
| N | Views (7d) | Weekly |
| O | Views (28d) | Weekly |

---

## 8. Cost Tracking

### 8.1 API Cost Model

```python
COST_PER_UNIT = {
    # Content generation
    "claude_input_token":   0.000003,   # $3/M tokens (Sonnet)
    "claude_output_token":  0.000015,   # $15/M tokens (Sonnet)
    "dalle_image":          0.040,      # $0.04 per image (1024x1024)
    "elevenlabs_char":      0.00003,    # $0.03/1K characters
    "veo3_second":          0.050,      # Estimated
    "kling_second":         0.040,      # Estimated

    # Storage
    "s3_gb_month":          0.023,      # $0.023/GB/month
    "s3_put_request":       0.000005,   # $0.005/1K PUTs

    # Infrastructure
    "celery_worker_hour":   0.05,       # EC2 t3.small estimate
}

def calculate_content_cost(content_id: str) -> dict:
    """Returns itemized cost breakdown for a content piece."""
    ...
```

### 8.2 Cost Tracking Table

```sql
CREATE TABLE content_costs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id      VARCHAR(100) NOT NULL,
    cost_type       VARCHAR(50),  -- 'llm' | 'image_gen' | 'video_gen' | 'audio' | 'storage'
    service         VARCHAR(50),  -- 'claude' | 'dalle' | 'veo3' | 'elevenlabs' | 's3'
    units_consumed  DECIMAL(12, 4),
    unit_cost       DECIMAL(12, 8),
    total_cost_usd  DECIMAL(10, 4),
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. Data Retention Policy

| Data Type | Retention Period | Action After |
|---|---|---|
| Raw API snapshots | 90 days | Archive to cold storage |
| Daily aggregates | 2 years | Keep in hot DB |
| Content performance scores | Indefinite | Core ML training data |
| Analytics collection logs | 30 days | Delete |
| Cost records | 3 years | Required for accounting |
| Exported CSVs | 30 days | Auto-delete from S3 |

---

*Last updated: February 2026*
