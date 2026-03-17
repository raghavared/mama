# OAuth Setup Guide for MAMA

This guide explains how to set up OAuth 2.0 authorization for each social media platform supported by MAMA. OAuth allows users to securely connect their social media accounts without sharing passwords, enabling automated publishing.

## Overview

MAMA uses the **OAuth 2.0 Authorization Code Flow** to obtain access tokens for publishing content. This flow is more secure than legacy token-based authentication and provides:

- Secure token storage with encryption
- Automatic token refresh (when supported by platform)
- Granular permission scopes
- User-level authentication

## Architecture

1. **User initiates connection** from the MAMA dashboard
2. **Backend generates authorization URL** with required scopes
3. **User authenticates** on the platform's website
4. **Platform redirects back** to MAMA with an authorization code
5. **Backend exchanges code** for access + refresh tokens
6. **Tokens are encrypted and stored** in the database
7. **Publishers use tokens** to post content on behalf of the user

## Supported Platforms

- Instagram (via Meta Graph API)
- Facebook Pages
- LinkedIn
- Twitter/X
- YouTube

---

## Platform Setup Instructions

### 1. Instagram OAuth

Instagram uses Meta's Graph API for OAuth. You'll need to create a Facebook/Meta App.

#### Step 1: Create a Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **My Apps** → **Create App**
3. Select **Business** as the app type
4. Fill in:
   - **App Name**: `MAMA Marketing Automation`
   - **Contact Email**: Your email
5. Click **Create App**

#### Step 2: Add Instagram Basic Display

1. In your app dashboard, click **Add Products**
2. Find **Instagram Basic Display** and click **Set Up**
3. Scroll down to **User Token Generator** section
4. Click **Add or Remove Instagram Testers**
5. Add your Instagram account as a tester
6. Accept the invitation from Instagram app → Settings → Apps and Websites → Tester Invites

#### Step 3: Configure OAuth Settings

1. Go to **Instagram Basic Display** → **Basic Display**
2. Under **Instagram App Settings**:
   - **Client OAuth Settings**:
     - **Valid OAuth Redirect URIs**: Add your callback URL:
       ```
       http://localhost:8000/api/oauth/callback/instagram
       ```
       For production, use your production domain:
       ```
       https://your-domain.com/api/oauth/callback/instagram
       ```
   - **Deauthorize Callback URL**: `https://your-domain.com/api/oauth/deauthorize`
   - **Data Deletion Request URL**: `https://your-domain.com/api/oauth/data-deletion`
3. Click **Save Changes**

#### Step 4: Get Client Credentials

1. Go to **Settings** → **Basic**
2. Copy your **App ID** (this is your Client ID)
3. Click **Show** next to **App Secret** and copy it (this is your Client Secret)

#### Step 5: Add to .env

```env
INSTAGRAM_CLIENT_ID=your_app_id_here
INSTAGRAM_CLIENT_SECRET=your_app_secret_here
```

#### Required Scopes

- `instagram_basic` - Access user profile and media
- `instagram_content_publish` - Publish photos and videos

#### Notes

- Instagram OAuth only works with Instagram Business or Creator accounts
- You must have a Facebook Page linked to your Instagram account
- For production, submit your app for review to get access to all users

---

### 2. Facebook Pages OAuth

Facebook Pages uses the same Meta app as Instagram.

#### Step 1: Create a Meta App

Follow the same steps as Instagram (Step 1 above), or use the same app if already created.

#### Step 2: Add Facebook Login Product

1. In your app dashboard, click **Add Products**
2. Find **Facebook Login** and click **Set Up**
3. Select **Web** as the platform
4. Enter your site URL: `http://localhost:3000` (or your production URL)

#### Step 3: Configure OAuth Redirect URIs

1. Go to **Facebook Login** → **Settings**
2. Under **Valid OAuth Redirect URIs**, add:
   ```
   http://localhost:8000/api/oauth/callback/facebook
   ```
   For production:
   ```
   https://your-domain.com/api/oauth/callback/facebook
   ```
3. Click **Save Changes**

#### Step 4: Get Client Credentials

Same as Instagram - use the App ID and App Secret from **Settings** → **Basic**.

#### Step 5: Add to .env

```env
FACEBOOK_CLIENT_ID=your_app_id_here
FACEBOOK_CLIENT_SECRET=your_app_secret_here
```

#### Required Scopes

- `pages_manage_posts` - Publish posts on behalf of pages
- `pages_read_engagement` - Read page engagement metrics

#### Notes

- User must be an admin of the Facebook Page they want to publish to
- For production, submit permissions for review
- Long-lived Page Access Tokens (60 days) can be obtained after initial OAuth

---

### 3. LinkedIn OAuth

LinkedIn uses OAuth 2.0 for API access.

#### Step 1: Create a LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click **Create app**
3. Fill in:
   - **App name**: `MAMA Marketing Automation`
   - **LinkedIn Page**: Select your company page (required)
   - **App logo**: Upload a logo (required)
   - **Legal agreement**: Accept terms
4. Click **Create app**

#### Step 2: Verify Your App

1. On the app settings page, go to the **Settings** tab
2. Click **Verify** under **App Settings**
3. Follow the verification process (you'll need to verify via your LinkedIn Page)

#### Step 3: Add OAuth 2.0 Redirect URLs

1. Go to the **Auth** tab
2. Under **OAuth 2.0 settings**, find **Redirect URLs**
3. Click **Add redirect URL** and enter:
   ```
   http://localhost:8000/api/oauth/callback/linkedin
   ```
   For production:
   ```
   https://your-domain.com/api/oauth/callback/linkedin
   ```
4. Click **Update**

#### Step 4: Request API Access

1. Go to the **Products** tab
2. Request access to:
   - **Share on LinkedIn** - Required for posting
   - **Sign In with LinkedIn using OpenID Connect** - Required for authentication
3. Wait for approval (usually instant for Share on LinkedIn)

#### Step 5: Get Client Credentials

1. Go to the **Auth** tab
2. Copy your **Client ID**
3. Copy your **Client Secret**

#### Step 6: Add to .env

```env
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
```

#### Required Scopes

- `w_member_social` - Share content on member's behalf
- `r_basicprofile` - Read basic profile information

#### Notes

- Requires a verified LinkedIn company page
- Access tokens are valid for 60 days
- Must request product access before using API in production

---

### 4. Twitter/X OAuth

Twitter uses OAuth 2.0 with PKCE (Proof Key for Code Exchange).

#### Step 1: Create a Twitter Developer Account

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Apply for a developer account (if you don't have one)
3. Complete the application process

#### Step 2: Create an App

1. In the Developer Portal, click **Projects & Apps**
2. Create a new project or select an existing one
3. Click **Add App** or **Create App**
4. Fill in:
   - **App name**: `MAMA Marketing Bot`
   - **Description**: Brief description of your app
5. Save your API keys (you'll see them once)

#### Step 3: Set Up OAuth 2.0

1. Go to your app settings
2. Click **Set up** under **User authentication settings**
3. Configure:
   - **App permissions**: Select **Read and write**
   - **Type of App**: **Web App**
   - **Callback URI / Redirect URL**:
     ```
     http://localhost:8000/api/oauth/callback/twitter
     ```
     For production:
     ```
     https://your-domain.com/api/oauth/callback/twitter
     ```
   - **Website URL**: `http://localhost:3000` (or your production URL)
4. Click **Save**

#### Step 4: Get OAuth 2.0 Credentials

1. After setup, you'll see your **OAuth 2.0 Client ID** and **Client Secret**
2. Copy both values

#### Step 5: Add to .env

```env
TWITTER_CLIENT_ID=your_oauth2_client_id_here
TWITTER_CLIENT_SECRET=your_oauth2_client_secret_here
```

#### Required Scopes

- `tweet.read` - Read tweets
- `tweet.write` - Post tweets
- `users.read` - Read user information

#### Notes

- OAuth 2.0 is different from Twitter's older OAuth 1.0a
- Requires app review for production use with elevated access
- Free tier has rate limits (1,500 tweets per month)

---

### 5. YouTube OAuth

YouTube uses Google's OAuth 2.0 system.

#### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Fill in:
   - **Project name**: `MAMA YouTube Publisher`
   - **Organization**: Your org (optional)
4. Click **Create**

#### Step 2: Enable YouTube Data API

1. In your project, go to **APIs & Services** → **Library**
2. Search for **YouTube Data API v3**
3. Click on it and press **Enable**

#### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or Internal if you have a Google Workspace)
3. Click **Create**
4. Fill in:
   - **App name**: `MAMA Marketing Automation`
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Search for and add:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube.readonly`
8. Click **Update** → **Save and Continue**
9. On **Test users**, add your Google account email
10. Click **Save and Continue**

#### Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Web application**
4. Fill in:
   - **Name**: `MAMA Backend`
   - **Authorized redirect URIs**: Add:
     ```
     http://localhost:8000/api/oauth/callback/youtube
     ```
     For production:
     ```
     https://your-domain.com/api/oauth/callback/youtube
     ```
5. Click **Create**
6. Copy your **Client ID** and **Client Secret**

#### Step 5: Add to .env

```env
YOUTUBE_CLIENT_ID=your_google_client_id_here
YOUTUBE_CLIENT_SECRET=your_google_client_secret_here
```

#### Required Scopes

- `https://www.googleapis.com/auth/youtube.upload` - Upload videos
- `https://www.googleapis.com/auth/youtube.readonly` - Read channel info

#### Notes

- Requires verified Google account
- App must be published (not in testing mode) for production
- Video uploads are subject to quota limits
- Requires OAuth verification for production (submit for review)

---

## Testing Your OAuth Setup

### 1. Check Configuration

Before testing OAuth flows, verify your environment variables are set:

```bash
# Backend
cd /path/to/MAMA
cat .env | grep "_CLIENT_ID\|_CLIENT_SECRET"
```

### 2. Start the Backend

```bash
# Start database and Redis
docker compose up postgres redis -d

# Run migrations
alembic upgrade head

# Start API
uvicorn src.api.main:app --reload --port 8000
```

### 3. Test Authorization URL Generation

```bash
# Test Instagram
curl http://localhost:8000/api/oauth/authorize/instagram

# Should return: {"authorization_url": "https://api.instagram.com/oauth/authorize?client_id=..."}
```

### 4. Test OAuth Flow (Manual)

1. Open the dashboard: `http://localhost:3000`
2. Go to **Settings** → **Social Connections**
3. Click **Connect** for a platform
4. You'll be redirected to the platform's authorization page
5. Authorize the app
6. You'll be redirected back to MAMA
7. Check that the connection status shows **Connected**

### 5. Verify Token Storage

```bash
# Check database for stored tokens
docker compose exec postgres psql -U mama -d mama_db -c "SELECT platform, expires_at, created_at FROM oauth_tokens;"
```

---

## Security Best Practices

### 1. Keep Secrets Secret

- **Never commit** `.env` files to git
- Use environment variables in production (not `.env` files)
- Rotate client secrets regularly
- Use different apps for development and production

### 2. Validate Redirect URIs

- Always use exact redirect URI matches
- Never use wildcard redirect URIs
- Use HTTPS in production (required by most platforms)

### 3. Token Storage

- Tokens are encrypted in the database using Fernet symmetric encryption
- The encryption key is derived from `SECRET_KEY` in your `.env`
- Use a strong, random `SECRET_KEY` in production (256-bit recommended)

### 4. Scope Minimization

- Only request the scopes your app actually needs
- Review and remove unused scopes
- Inform users why each scope is needed

### 5. Token Rotation

- Refresh tokens before they expire
- Handle token revocation gracefully
- Implement retry logic for expired tokens

---

## Troubleshooting

### "Missing OAuth credentials" Error

**Cause**: Client ID or Client Secret not set in `.env`

**Solution**:
```bash
# Check if variables are set
cat .env | grep INSTAGRAM_CLIENT

# If missing, add them:
echo "INSTAGRAM_CLIENT_ID=your_id" >> .env
echo "INSTAGRAM_CLIENT_SECRET=your_secret" >> .env
```

### "Invalid redirect URI" Error

**Cause**: Callback URL doesn't match what's registered in the platform's app settings

**Solution**:
1. Check the error message for the redirect URI that was used
2. Go to the platform's developer console
3. Add the exact URI to the allowed redirect URIs list
4. Make sure there are no trailing slashes or typos

### "Insufficient permissions" Error

**Cause**: Required scopes not requested or not approved

**Solution**:
1. Check that your app has requested the correct product/permissions
2. For Facebook/Instagram, you may need to submit for app review
3. For LinkedIn, verify your app and request product access
4. For YouTube, ensure the YouTube Data API is enabled

### Token Encryption Fails

**Cause**: `SECRET_KEY` has changed or is missing

**Solution**:
```bash
# Generate a new secret key (development only - will invalidate existing tokens)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
echo "SECRET_KEY=your_new_secret_key" >> .env
```

### Platform Rejects Token Exchange

**Cause**: Authorization code expired or already used

**Solution**:
- Authorization codes are single-use and expire quickly (usually 10 minutes)
- Restart the OAuth flow from the beginning
- Check server clock synchronization (NTP)

---

## Production Deployment Checklist

- [ ] Create separate OAuth apps for production (don't reuse dev apps)
- [ ] Use HTTPS for all redirect URIs
- [ ] Update redirect URIs to production domain
- [ ] Set strong, random `SECRET_KEY` (at least 256 bits)
- [ ] Submit apps for platform review (Facebook, LinkedIn, Twitter, YouTube)
- [ ] Request production API access levels
- [ ] Set up monitoring for token expiration
- [ ] Implement token refresh automation
- [ ] Add rate limiting to OAuth endpoints
- [ ] Set up logging for OAuth failures
- [ ] Test all platforms end-to-end
- [ ] Document platform-specific quirks for your team
- [ ] Set up alerts for OAuth token expiration

---

## Additional Resources

- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Meta Graph API Documentation](https://developers.facebook.com/docs/graph-api/)
- [LinkedIn API Documentation](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/authentication/oauth-2-0)
- [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3)

---

## Support

If you encounter issues not covered in this guide:

1. Check the [MAMA GitHub Issues](https://github.com/your-org/MAMA/issues)
2. Review platform-specific API documentation
3. Check platform status pages for outages
4. Open a new issue with detailed error messages and steps to reproduce
