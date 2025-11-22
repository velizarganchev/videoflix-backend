# 06 – API Reference

This document describes the main REST endpoints exposed by the VideoFlix backend.  
All endpoints are prefixed by the backend origin, e.g.:

- **Production:** `https://api.videoflix-velizar-ganchev-backend.com`
- **Dev (local):** `http://127.0.0.1:8000`

Authentication is done via **HttpOnly JWT cookies** (access + refresh).  
Unless noted otherwise, the frontend must send requests with `withCredentials: true`.

---

## 1. Auth & Users (`users_app`)

### 1.1 Register

`POST /users/register/`

Create a new user and send an activation email.

**Request (JSON)**

```json
{
  "username": "velizar",
  "email": "user@example.com",
  "password": "StrongPassword123"
}
```

**Response 201**

```json
{
  "detail": "Please check your email to confirm your account."
}
```

---

### 1.2 Confirm Email

`GET /users/confirm/`

Called from the activation link that is sent via email.

**Query params**

- `uid` – base64 encoded user id
- `token` – confirmation token

Example:

```text
GET /users/confirm/?uid=NA&token=abc123...
```

**Typical responses**

- 200 – account activated
- 400 / 404 – invalid or expired link

---

### 1.3 Login

`POST /users/login/`

Logs the user in and sets **HttpOnly cookies** for access + refresh tokens.

**Request (JSON)**

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123",
  "remember_me": true
}
```

**Response 200**

```json
{
  "id": 1,
  "username": "velizar",
  "email": "user@example.com",
  "favorite_videos": [5, 7, 12]
}
```

Cookies set (example):

- `vf_access=<jwt>; HttpOnly; Secure; SameSite=None`
- `vf_refresh=<jwt>; HttpOnly; Secure; SameSite=None`

---

### 1.4 Logout

`POST /users/logout/`

Blacklists the refresh token and removes auth cookies.

**Request body**

```json
{}
```

**Response 204**

No content (cookies cleared).

---

### 1.5 Forgot Password

`POST /users/forgot-password/`

Trigger a password reset email.

**Request**

```json
{
  "email": "user@example.com"
}
```

**Response 200**

```json
{
  "detail": "If an account with this email exists, a reset link has been sent."
}
```

---

### 1.6 Reset Password

`POST /users/reset-password/`

Called from the reset email link.

**Request**

```json
{
  "uid": "NA",
  "token": "reset-token-here",
  "new_password": "NewStrongPassword123"
}
```

**Response 200**

```json
{
  "detail": "Password has been reset successfully."
}
```

---

## 2. Content (`content_app`)

### 2.1 List Videos

`GET /content/`

Returns all videos with metadata, processing flags and thumbnail URLs.  
The response is lightly cached to reduce DB load.

**Response 200 (example)**

```json
[
  {
    "id": 5,
    "created_at": "2025-11-22T10:53:08.473Z",
    "title": "Counting the Days",
    "description": "man in an orange prison uniform sits alone...",
    "category": "Action",
    "image_file": "https://videoflix-media-new.s3.amazonaws.com/images/Breakout.jpg",
    "image_url": "https://videoflix-media-new.s3.amazonaws.com/images/Breakout.jpg",
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
]
```

Notes:

- `processing_state` is one of: `pending`, `processing`, `ready`, `error`.
- Frontend uses this to display a spinner / error thumb while transcoding is running.

---

### 2.2 Toggle Favorite

`POST /content/add-favorite/`

Adds or removes a video from the current user's favorites.  
Requires authentication cookies.

**Request**

```json
{
  "video_id": 5
}
```

**Response 200 (example)**

```json
{
  "id": 1,
  "username": "velizar",
  "email": "user@example.com",
  "favorite_videos": [5, 7, 12]
}
```

---

### 2.3 Get Signed Playback URL

`GET /content/video-url/<id>/?quality=<q>`

Returns a playback URL for the requested video, tailored to either:

- Local media – absolute `/media/...` URL
- S3 media – **presigned URL** when `AWS_S3_QUERYSTRING_AUTH=True`
- S3 public bucket – direct object URL when `AWS_S3_QUERYSTRING_AUTH=False`

**Path / Query**

- `<id>` – numeric video id
- `quality` – one of `120p`, `360p`, `720p`, `1080p` (optional, defaults to original)

Example:

```text
GET /content/video-url/5/?quality=720p
```

**Response 200**

```json
{
  "url": "https://videoflix-media-new.s3.amazonaws.com/videos/Breakout_720p.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&..."
}
```

**Errors**

- `404` – video not found
- `400` – invalid quality
- `403/401` – user not authenticated (depending on auth config)

---

## 3. Health Endpoints

### 3.1 Django Health

`GET /health/`

Simple health probe for application server.

**Response 200**

```json
{"status": "ok"}
```

### 3.2 Nginx Health

`GET /healthz`

Served by Nginx directly; used by load balancers or uptime checks.

**Response 200**

Plain text `OK`.

---

## 4. Notes for Frontend Integration

- Always send cookies: `withCredentials: true`.
- Handle `401` responses by triggering a refresh‑token call (done by Angular interceptor in this project).
- For video playback:
  - Call `GET /content/` to get list + thumbnails + processing flags.
  - When user clicks an item, call `GET /content/video-url/<id>/?quality=...` to resolve the actual stream URL.
- Do **not** cache presigned URLs long term – they expire by design.
