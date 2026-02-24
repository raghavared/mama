# MAMA - Platform API Requirements & Content Specifications

## Overview

This document covers API requirements, authentication flows, rate limits, and content specifications for all social platforms targeted by MAMA's publishing pipeline.

**Target Platforms:**
- Instagram (Image Posts + Reels)
- LinkedIn (Image Posts + Video Posts)
- Facebook (Image Posts + Reels)
- X / Twitter (Image Posts + Videos)
- YouTube (Shorts + Long-form)

---

## 1. Instagram Graph API

### Authentication
- **Method**: OAuth 2.0 via Facebook Login
- **Token Type**: Long-lived User Access Token (60-day expiry) or Page Access Token
- **Scopes Required**:
  - `instagram_basic`
  - `instagram_content_publish`
  - `instagram_manage_insights`
  - `pages_show_list` (for business accounts)
- **Token Refresh**: Refresh long-lived tokens before expiry via `/refresh_access_token`
- **App Review**: `instagram_content_publish` requires Facebook App Review approval

### API Endpoints
| Action | Method | Endpoint |
|---|---|---|
| Create media container | POST | `/{ig-user-id}/media` |
| Publish media | POST | `/{ig-user-id}/media_publish` |
| Upload video (Reels) | POST | `/{ig-user-id}/media` with `media_type=REELS` |
| Check upload status | GET | `/{ig-container-id}?fields=status_code` |
| Get post insights | GET | `/{ig-media-id}/insights` |
| Get account insights | GET | `/{ig-user-id}/insights` |

### Rate Limits
| Limit Type | Value |
|---|---|
| API calls per hour (per user) | 200 |
| Content publish calls per day | 50 posts per IG account |
| Reel creation limit | 50 per day |
| Graph API rate limit (app-level) | 200 × monthly active users / 100 |

### Image Post Specifications
| Property | Requirement |
|---|---|
| Formats | JPEG, PNG (no GIF) |
| Aspect Ratios | 1:1 (square), 4:5 (portrait), 1.91:1 (landscape) |
| Recommended Resolution | 1080×1080 (square), 1080×1350 (portrait), 1080×566 (landscape) |
| Max File Size | 8 MB |
| Min Image Width | 320 px |
| Max Image Width | 1440 px |
| Caption Max Length | 2,200 characters |
| Max Hashtags | 30 |
| Max Tags | 20 accounts |

### Reel (Video) Specifications
| Property | Requirement |
|---|---|
| Formats | MP4, MOV |
| Aspect Ratio | 9:16 (vertical, full screen) |
| Recommended Resolution | 1080×1920 |
| Min Resolution | 540×960 |
| Max File Size | 1 GB |
| Max Duration | 90 seconds |
| Min Duration | 3 seconds |
| Min Frame Rate | 23 FPS |
| Max Frame Rate | 60 FPS |
| Audio | Required for Reels |
| Caption Max Length | 2,200 characters |

### Publishing Flow (Two-Step)
```
Step 1: POST /{ig-user-id}/media
  → Returns: ig_container_id

Step 2 (poll until status=FINISHED):
  GET /{ig-container-id}?fields=status_code

Step 3: POST /{ig-user-id}/media_publish
  Body: { creation_id: ig_container_id }
  → Returns: ig_media_id
```

---

## 2. LinkedIn API

### Authentication
- **Method**: OAuth 2.0 (3-legged for member context, 2-legged for org context)
- **Token Type**: Access Token (60-day expiry)
- **Scopes Required**:
  - `w_member_social` (post on behalf of member)
  - `r_liteprofile` (read profile)
  - `rw_organization_admin` (post on behalf of organization/company page)
  - `w_organization_social`
  - `r_organization_social`
- **Base URL**: `https://api.linkedin.com/v2/`

### API Endpoints
| Action | Method | Endpoint |
|---|---|---|
| Create text/image post | POST | `/ugcPosts` |
| Register video upload | POST | `/assets?action=registerUpload` |
| Upload video | PUT | `{uploadUrl}` (from registerUpload response) |
| Create video post | POST | `/ugcPosts` with video asset URN |
| Get post analytics | GET | `/organizationalEntityShareStatistics` |
| Get follower stats | GET | `/organizationalEntityFollowerStatistics` |

### Rate Limits
| Limit Type | Value |
|---|---|
| Daily application throttle | 100,000 API calls/day (varies by partner tier) |
| Member calls per day | 500/day |
| Organization calls per day | 200/day per organization |
| Video upload throttle | No hard limit (bandwidth constrained) |

### Image Post Specifications
| Property | Requirement |
|---|---|
| Formats | JPEG, PNG, GIF (static) |
| Recommended Size | 1200×627 px (1.91:1 landscape) or 1080×1080 (1:1) |
| Max File Size | 5 MB per image |
| Max Images per Post | 9 images (carousel) |
| Post Text Max Length | 3,000 characters |
| Hashtags | 3–5 recommended (no hard limit) |

### Video Post Specifications
| Property | Requirement |
|---|---|
| Formats | MP4, MOV, AVI, WMV |
| Aspect Ratios | 1:2.4 to 2.4:1 |
| Recommended | 1920×1080 (16:9) or 1080×1920 (9:16 for vertical) |
| Min Resolution | 256×144 |
| Max Resolution | 4096×2304 |
| Max File Size | 5 GB |
| Max Duration | 10 minutes (600 seconds) |
| Min Duration | 3 seconds |
| Frame Rate | 10–60 FPS |
| Post Text Max Length | 3,000 characters |

### Publishing Flow
```
For Images:
POST /ugcPosts
  Body: {
    author: "urn:li:person:{personId}",
    lifecycleState: "PUBLISHED",
    specificContent: {
      "com.linkedin.ugc.ShareContent": {
        shareCommentary: { text: "caption" },
        shareMediaCategory: "IMAGE",
        media: [{ status: "READY", media: "urn:li:digitalmediaAsset:{assetId}" }]
      }
    },
    visibility: { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" }
  }

For Videos:
Step 1: POST /assets?action=registerUpload → get uploadUrl + asset URN
Step 2: PUT {uploadUrl} with video binary
Step 3: POST /ugcPosts with video asset URN
```

---

## 3. Facebook Graph API

### Authentication
- **Method**: OAuth 2.0 via Facebook Login
- **Token Type**: Page Access Token (never expires if generated from long-lived user token)
- **Scopes Required**:
  - `pages_manage_posts`
  - `pages_read_engagement`
  - `pages_show_list`
  - `publish_video` (for video posts)
  - `read_insights`
- **Base URL**: `https://graph.facebook.com/v19.0/`

### API Endpoints
| Action | Method | Endpoint |
|---|---|---|
| Post to page feed | POST | `/{page-id}/feed` |
| Upload photo | POST | `/{page-id}/photos` |
| Upload video | POST | `/{page-id}/videos` |
| Create Reel | POST | `/{page-id}/video_reels` |
| Publish Reel | POST | `/{page-id}/video_reels` with `video_state=PUBLISHED` |
| Get post insights | GET | `/{post-id}/insights` |
| Get page insights | GET | `/{page-id}/insights` |

### Rate Limits
| Limit Type | Value |
|---|---|
| API calls per hour (per user token) | 200 |
| Page API calls | 4,800 per 24 hours |
| Video upload | No hard limit (bandwidth constrained) |
| Business Use Case (BUC) rate limit | Per app, varies by usage tier |

### Image Post Specifications
| Property | Requirement |
|---|---|
| Formats | JPEG, PNG, BMP, GIF, TIFF |
| Recommended Size | 1200×630 px (1.91:1) or 1080×1080 (1:1) |
| Max File Size | 30 MB |
| Aspect Ratios | 1.91:1 to 4:5 (optimal range) |
| Post Text Max Length | 63,206 characters |
| Hashtags | No hard limit (10–15 recommended) |

### Reel (Video) Specifications
| Property | Requirement |
|---|---|
| Formats | MP4, MOV |
| Aspect Ratio | 9:16 (vertical only for Reels) |
| Recommended Resolution | 1080×1920 |
| Max File Size | 1 GB |
| Max Duration | 90 seconds |
| Min Duration | 3 seconds |
| Frame Rate | 23–60 FPS |
| Audio | Required for Reels |

### Publishing Flow (Reels - Two-Step)
```
Step 1: POST /{page-id}/video_reels
  Body: { upload_phase: "start", ... }
  → Returns: video_id, upload_url

Step 2: Upload video binary to upload_url

Step 3: POST /{page-id}/video_reels
  Body: {
    video_id: "{video_id}",
    upload_phase: "finish",
    video_state: "PUBLISHED",
    description: "caption",
    title: "reel title"
  }
```

---

## 4. X / Twitter API v2

### Authentication
- **Method**: OAuth 2.0 (PKCE for user context) or OAuth 1.0a (for media upload endpoint)
- **Token Type**: Bearer Token (app-only) or User Access Token + Secret (OAuth 1.0a)
- **Scopes Required**:
  - `tweet.write`
  - `tweet.read`
  - `users.read`
  - `offline.access` (for refresh tokens)
- **Media Upload**: Still uses v1.1 endpoint (`/1.1/media/upload`)
- **Base URL v2**: `https://api.twitter.com/2/`
- **Base URL v1.1**: `https://api.twitter.com/1.1/`

### API Tiers (2025)
| Tier | Monthly Price | Tweet Limit | Notes |
|---|---|---|---|
| Free | $0 | 500 tweets/month | Read-only mostly |
| Basic | $100/month | 10,000 tweets/month | Good for testing |
| Pro | $5,000/month | 1,000,000 tweets/month | Production use |
| Enterprise | Custom | Custom | High volume |

### API Endpoints
| Action | Method | Endpoint |
|---|---|---|
| Create tweet | POST | `/2/tweets` |
| Upload media (chunked) | POST | `/1.1/media/upload` |
| Get tweet metrics | GET | `/2/tweets/{id}?tweet.fields=public_metrics` |
| Delete tweet | DELETE | `/2/tweets/{id}` |

### Rate Limits
| Endpoint | Limit |
|---|---|
| POST /2/tweets | 300/15min (per user) |
| GET /2/tweets | 300/15min (per app) |
| POST /1.1/media/upload | 30 requests/15min |
| Media upload per day | 300 per user |

### Image Post Specifications
| Property | Requirement |
|---|---|
| Formats | JPEG, PNG, GIF, WEBP |
| Max File Size (JPEG/PNG/WEBP) | 5 MB |
| Max File Size (PNG, high quality) | 15 MB |
| Max File Size (GIF) | 15 MB |
| Max Images per Tweet | 4 |
| Tweet Text Max Length | 280 characters |
| Hashtags | Count toward 280 char limit |
| Recommended Image Size | 1200×675 px (16:9) or 1080×1080 (1:1) |

### Video Post Specifications
| Property | Requirement |
|---|---|
| Formats | MP4, MOV |
| Max File Size | 512 MB |
| Max Duration | 140 seconds |
| Recommended Resolution | 1280×720 (720p) or 1920×1080 (1080p) |
| Aspect Ratios | 1:2.39 to 2.39:1 |
| Min Aspect Ratio | 1:2.39 (portrait) |
| Max Aspect Ratio | 2.39:1 (landscape) |
| Vertical (Shorts-style) | 9:16 (1080×1920) supported |
| Frame Rate | Up to 60 FPS |
| Video Bitrate | 25 Mbps max |
| Audio | AAC, mono or stereo |

### Media Upload Flow (Chunked)
```
Step 1: INIT
  POST /1.1/media/upload
  Body: { command: "INIT", total_bytes: N, media_type: "video/mp4" }
  → Returns: media_id

Step 2: APPEND (repeat in 5MB chunks)
  POST /1.1/media/upload
  Body: { command: "APPEND", media_id: X, segment_index: N, media: <chunk> }

Step 3: FINALIZE
  POST /1.1/media/upload
  Body: { command: "FINALIZE", media_id: X }

Step 4: STATUS (poll if processing_info present)
  GET /1.1/media/upload?command=STATUS&media_id=X

Step 5: Create Tweet
  POST /2/tweets
  Body: { text: "caption #hashtag", media: { media_ids: ["X"] } }
```

---

## 5. YouTube Data API v3

### Authentication
- **Method**: OAuth 2.0 (required for uploads)
- **Token Type**: Access Token + Refresh Token
- **Scopes Required**:
  - `https://www.googleapis.com/auth/youtube.upload`
  - `https://www.googleapis.com/auth/youtube`
  - `https://www.googleapis.com/auth/youtube.readonly`
  - `https://www.googleapis.com/auth/youtubepartner`
- **Base URL**: `https://www.googleapis.com/youtube/v3/`
- **Upload URL**: `https://www.googleapis.com/upload/youtube/v3/videos`

### API Endpoints
| Action | Method | Endpoint |
|---|---|---|
| Upload video (resumable) | POST | `/upload/youtube/v3/videos?uploadType=resumable` |
| Set video metadata | PUT | `/youtube/v3/videos` |
| Get video analytics | GET | `/youtube/analytics/v2/reports` |
| Get channel statistics | GET | `/youtube/v3/channels?part=statistics` |
| Create playlist | POST | `/youtube/v3/playlists` |
| Add to playlist | POST | `/youtube/v3/playlistItems` |

### API Quotas
| Quota Type | Value |
|---|---|
| Units per day | 10,000 |
| Video upload cost | 1,600 units |
| Playlist insert | 50 units |
| Channel read | 1 unit |
| Videos list | 1 unit |
| Analytics read | 1 unit |
| Max daily uploads | ~6 videos/day on free quota |

### YouTube Shorts Specifications
| Property | Requirement |
|---|---|
| Aspect Ratio | 9:16 (vertical) |
| Recommended Resolution | 1080×1920 |
| Max Duration | 60 seconds |
| Format | MP4 (H.264 video, AAC audio) |
| Max File Size | 256 GB (practical: under 2 GB recommended) |
| Frame Rate | 24, 25, 30, 48, 50, 60 FPS |
| Short Detection | Duration ≤60s AND 9:16 ratio → auto-categorized as Short |

### Regular Video Specifications
| Property | Requirement |
|---|---|
| Recommended Resolution | 1920×1080 (1080p) |
| Max File Size | 256 GB |
| Max Duration | 15 min (unverified), 12 hours (verified) |
| Formats | MP4, MOV, AVI, WMV, FLV, WebM, 3GPP |
| Title Max Length | 100 characters |
| Description Max Length | 5,000 characters |
| Tags | Up to 500 characters total |
| Max Tags | 50 tags |

### Resumable Upload Flow
```
Step 1: Initialize Upload Session
  POST /upload/youtube/v3/videos?uploadType=resumable
  Headers: X-Upload-Content-Type: video/mp4, X-Upload-Content-Length: N
  Body: { snippet: { title, description, tags, categoryId }, status: { privacyStatus } }
  → Returns: Location header with upload_url

Step 2: Upload Video (in chunks or single PUT)
  PUT {upload_url}
  Headers: Content-Range: bytes 0-N/Total
  Body: <video bytes>

Step 3: Monitor Processing
  GET /youtube/v3/videos?id={videoId}&part=processingDetails
  Poll until processingDetails.processingStatus == "succeeded"
```

---

## API Credentials Management

### Required Environment Variables
```bash
# Instagram / Facebook (same app)
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_PAGE_ACCESS_TOKEN=
INSTAGRAM_USER_ID=
INSTAGRAM_ACCESS_TOKEN=

# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_ORG_ID=

# X / Twitter
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
TWITTER_BEARER_TOKEN=

# YouTube / Google
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_CHANNEL_ID=
```

### Token Storage & Rotation
- Store all tokens in a secrets vault (AWS Secrets Manager, HashiCorp Vault, or environment-based `.env` with restricted access)
- Implement auto-refresh for OAuth tokens before expiry
- Log all token refresh events
- Alert on token expiry failures

---

## Platform Comparison Summary

| Feature | Instagram | LinkedIn | Facebook | X/Twitter | YouTube |
|---|---|---|---|---|---|
| Image Formats | JPEG/PNG | JPEG/PNG/GIF | JPEG/PNG/GIF | JPEG/PNG/GIF/WEBP | N/A |
| Video Format | MP4/MOV | MP4/MOV | MP4/MOV | MP4/MOV | MP4 (recommended) |
| Max Image Size | 8 MB | 5 MB | 30 MB | 5–15 MB | N/A |
| Max Video Size | 1 GB | 5 GB | 1 GB | 512 MB | 256 GB |
| Max Video Duration | 90s (Reels) | 10 min | 90s (Reels) | 140s | 60s (Shorts) |
| Caption Limit | 2,200 chars | 3,000 chars | 63,206 chars | 280 chars | 5,000 chars (desc) |
| Max Hashtags | 30 | ~3–5 | No limit | In char limit | 50 tags |
| Ideal Ratio (Video) | 9:16 | 9:16 or 16:9 | 9:16 | 9:16 | 9:16 (Shorts) |
| Auth Type | OAuth 2.0 | OAuth 2.0 | OAuth 2.0 | OAuth 2.0 + 1.0a | OAuth 2.0 |
| Two-Step Publish | Yes | Yes | Yes | Yes | Yes (resumable) |

---

## Error Handling & Retry Strategy

### Common Error Codes
| Platform | Code | Meaning | Action |
|---|---|---|---|
| Instagram/Facebook | 4 | App rate limit reached | Wait + exponential backoff |
| Instagram/Facebook | 190 | Invalid/expired token | Refresh token |
| LinkedIn | 422 | Unprocessable entity | Validate payload |
| LinkedIn | 429 | Too many requests | Back off, retry after header |
| Twitter | 187 | Duplicate tweet | Skip or modify content |
| Twitter | 429 | Rate limit | Respect `x-rate-limit-reset` header |
| YouTube | 403 | Quota exceeded | Wait until daily quota resets |
| YouTube | 400 | Invalid video | Check format/specs |

### Retry Policy
```python
RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_factor": 2,
    "initial_wait_seconds": 5,
    "retryable_status_codes": [429, 500, 502, 503, 504],
    "non_retryable_codes": [400, 401, 403, 404]
}
```

---

*Last updated: February 2026 — API specs subject to platform changes. Always verify against official docs.*
