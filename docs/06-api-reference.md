# 06 – API Reference (High‑Level)

This document summarizes the main API endpoints used by the Angular frontend. It is not a full OpenAPI spec, but it gives
a clear overview for reviewers and developers.

Base URL examples:

- Dev: `http://127.0.0.1:8000`
- Prod: `https://api.your-domain.com`

All authenticated endpoints rely on HttpOnly JWT cookies (no tokens in localStorage).

---

## 1. Authentication & User Lifecycle

### 1.1 Registration

**POST `/users/register/`**

Request JSON:

```json
{
  "email": "user@example.com",
  "username": "demo",
  "password": "StrongPass123!"
}
```

Response (201):

```json
{
  "email": "user@example.com"
}
```

Side‑effect: sends a confirmation email with a link to `/users/confirm/?uid=...&token=...`.

---

### 1.2 Email Exists

**GET `/users/email-exists/?email=...`**

Returns:

```json
{ "exists": true }
```

Used by the frontend to show inline validation on signup.

---

### 1.3 Confirm Account

**GET `/users/confirm/?uid=<base36>&token=<jwt>`**

Activates the account (if token is valid) and redirects to the frontend login page.

---

### 1.4 Login

**POST `/users/login/`**

Request JSON:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!",
  "remember": true
}
```

Response (200):

```json
{
  "id": 1,
  "username": "demo",
  "email": "user@example.com",
  "favorite_videos": [5, 7]
}
```

Side‑effects:

- Sets `vf_refresh` and `vf_access` cookies (names configurable via `.env`).

---

### 1.5 Refresh

**POST `/users/refresh/`**

- Reads the refresh token from the HttpOnly cookie.  
- Returns `{"detail": "Access token refreshed."}` and sets a new access cookie.  
- Optionally rotates the refresh token and blacklists the old one (SimpleJWT settings).

---

### 1.6 Logout

**POST `/users/logout/`**

- Attempts to blacklist the current refresh token.  
- Clears both JWT cookies.

---

### 1.7 Forgot Password

**POST `/users/forgot-password/`**

Request:

```json
{ "email": "user@example.com" }
```

Response (always 200, to avoid enumeration):

```json
{ "message": "If this email exists, a reset link has been sent." }
```

Sends a reset link to the email address if the user exists.

---

### 1.8 Reset Password

**POST `/users/reset-password/`**

Request:

```json
{
  "uid": "<base36>",
  "token": "<jwt>",
  "new_password": "NewStrongPass123!"
}
```

Response:

```json
{ "message": "Password has been reset successfully." }
```

Side‑effect: (optionally) a “password reset successful” email can be sent via a background task.

---

## 2. Content / Videos

All endpoints under `/content/` require authentication.

### 2.1 List Videos

**GET `/content/`**

Returns an array of videos, newest first. Example element:

```json
{
  "id": 5,
  "title": "Counting the Days",
  "description": "Man in an orange prison uniform sits alone...",
  "category": "Action",
  "created_at": "2025-11-22T10:53:08Z",
  "image_file": "images/Breakout.jpg",
  "image_url": "https://.../images/Breakout.jpg",
  "video_file": "videos/Breakout.mp4",
  "converted_files": {
    "120p": "videos/Breakout_120p.mp4",
    "360p": "videos/Breakout_360p.mp4",
    "720p": "videos/Breakout_720p.mp4",
    "1080p": "videos/Breakout_1080p.mp4"
  },
  "processing_state": "ready",
  "processing_error": ""
}
```

The Angular frontend uses `processing_state` to show spinners / disabled cards while transcoding is in progress.

---

### 2.2 Toggle Favorites

**POST `/content/add-favorite/`** (or similar path depending on your URL config)

Request:

```json
{ "video_id": 5 }
```

Response (200):

```json
[5, 7, 9]
```

Returns the full list of favorite video IDs for the current user.

---

### 2.3 Get Streaming URL

**GET `/content/video-url/<id>/?quality=720p`**

Response:

```json
{ "url": "https://videoflix-media.s3.eu-central-1.amazonaws.com/videos/Breakout_720p.mp4?X-Amz-Expires=3600&..." }
```

Depending on configuration this may be:

- A presigned S3 URL (private bucket)  
- A public S3 URL (public bucket, no querystring)  
- A local `/media/...` URL in development

---

## 3. Health & Admin

- `GET /health/` – application health (used for monitoring).  
- `GET /healthz` – Nginx health endpoint.  
- `/admin/` – Django admin (superuser only).  
- `/django-rq/` – Django‑RQ dashboard for monitoring background jobs.

---

This high‑level reference is intentionally concise. For implementation details, see the Django views and serializers in
`users_app` and `content_app`.
