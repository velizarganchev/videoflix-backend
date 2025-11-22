# Architecture & Data Flow

This document explains how the Videoflix backend is structured internally and how requests and background jobs flow through the system.

---

## 1. High‑Level Components

```text
+-------------------------+
|       Angular App       |
|  (videoflix-frontend)   |
+------------+------------+
             |
             | HTTPS (JWT cookies, JSON)
             v
+------------+------------+
|         Nginx           |
|  TLS termination,       |
|  static, reverse proxy  |
+------------+------------+
             |
             | HTTP (Gunicorn)
             v
+------------+------------+
|     Django + DRF        |
|   (Gunicorn workers)    |
+------------+------------+
    |                |
    | ORM            | RQ enqueue
    v                v
+--------+     +-----------+
|  RDS   |     |  Redis    |
|  Postg.|     |  Queue    |
+--------+     +-----+-----+
                     |
                     | Jobs
                     v
             +---------------+
             |  RQ Worker    |
             |  (FFmpeg, S3) |
             +-------+-------+
                     |
                     | upload / download
                     v
                +---------+
                |   S3    |
                +---------+
```

---

## 2. Django Apps

### 2.1 `users_app`

Responsibilities:

- Custom user model / profile
- Registration and email confirmation
- Login/logout
- Password reset (email link → token)
- Favorite videos
- JWT cookie integration with SimpleJWT:
  - Access token: short‑lived (e.g. 5 minutes)
  - Refresh token: longer‑lived (e.g. 1 hour or 7 days for “remember me”)
- Helper functions to set/clear HttpOnly cookies on responses

### 2.2 `content_app`

Responsibilities:

- `Video` model and related logic
- Fields:
  - `title`, `description`, `category`
  - `video_file` (original)
  - `image_file` (thumbnail)
  - `converted_files` (JSON map of renditions by quality)
  - `processing_state` (`pending`, `processing`, `ready`, `error`)
  - `processing_error` (text, optional)
- API endpoints:
  - List videos
  - Toggle favorites
  - Generate signed playback URL (for requested quality)
- Tasks and signals for FFmpeg jobs and cleanup

### 2.3 `middleware`

- Contains range request / streaming helpers so that clients can seek within video content (especially important for large files and video players).

---

## 3. Video Upload & Processing Flow

The backend is designed so that **uploading a video** and **transcoding it** happen asynchronously.

### 3.1 Upload in Django Admin (or via API)

1. Admin uploads a file to the `Video.video_file` field.
2. Django saves the `Video` instance with:
   - `processing_state = "pending"` initially.
3. After `save()`, a **signal** (`post_save`) is triggered.

### 3.2 Signals → RQ Jobs

`content_app.signals` connects `Video` to Django signals:

- `post_save(Video)`
  - If a new video was created:
    - Enqueues **four FFmpeg jobs**:
      - `convert_to_120p`
      - `convert_to_360p`
      - `convert_to_720p`
      - `convert_to_1080p`
    - Enqueues a **thumbnail** job: `generate_thumbnail_task`
  - These jobs are put into the `default` RQ queue.

- `pre_save(Video)`  
  - If the `video_file` or `image_file` changes, it enqueues cleanup jobs to delete old originals/renditions/thumbnails.

- `post_delete(Video)`  
  - When a video is deleted, enqueues jobs to remove:
    - the original file
    - all renditions
    - the thumbnail

### 3.3 Worker Execution

The `rq_worker` container runs something like:

```bash
python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker --with-scheduler
```

For each queued job:

1. It downloads or locates the source file:
   - If `USE_S3_MEDIA=True` → download from S3 to a temp file.
   - Else → operate on a local path under `MEDIA_ROOT`.
2. It runs `ffmpeg` to produce a rendition at a specific height (e.g. 360p).
3. It writes the output:
   - Either back to S3 (`_s3_upload`)
   - Or to local storage under `MEDIA_ROOT`
4. It updates the `Video.converted_files` JSON mapping and, when all renditions are present, sets `processing_state = "ready"`.
5. If any error occurs, it sets `processing_state = "error"` and logs `processing_error` with details.

### 3.4 Frontend View

- The Angular frontend fetches videos via `/content/`.
- Each video item includes its `processing_state`.
- If `processing_state !== "ready"`:
  - The frontend can display a **spinner** or “processing” placeholder.
  - It can disable clicking to prevent playback attempts of incomplete videos.
- Once the worker finishes and the state becomes `"ready"`:
  - The thumbnail is available (`image_file`)
  - Clicking the card requests a signed playback URL from `/content/video-url/<id>/`.

---

## 4. Signed Playback URLs (S3)

When `USE_S3_MEDIA=True`:

1. The `Video` model stores only **keys** (paths) of objects in S3.
2. To actually stream a video, the frontend calls the backend:

   ```http
   GET /content/video-url/<id>/?quality=720p
   ```

3. The backend:
   - Looks up the `Video` and the appropriate key:
     - Original or one of the renditions from `converted_files`.
   - Uses `boto3` to generate a **presigned URL** with a short expiry.
   - Returns JSON: `{ "url": "<presigned-url>" }`.
4. The player loads this URL directly from S3.

If `AWS_S3_QUERYSTRING_AUTH=False` is configured and bucket policy allows public `GET`, the backend may also return a **plain public URL** instead of a presigned one.

---

## 5. Docker & Entry Point

The `Dockerfile` builds a single image that is used for both:

- `web` (Gunicorn + Django)
- `rq_worker` (RQ worker command)

The entry script (`backend.entrypoint.sh`) typically performs:

1. Django system checks
2. `python manage.py migrate`
3. Optional superuser creation (if env variables set)
4. `python manage.py collectstatic --noinput`
5. Starting the main process:
   - For `web`: `gunicorn`
   - For `rq_worker`: `python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker`

Docker services are defined in `docker-compose.yml` with named services:

- `web`
- `rq_worker`
- `redis`
- `nginx`
- `certbot` / `certbot_bootstrap`

Nginx forwards traffic to `web:8000` and exposes `80`/`443` publicly.

---

## 6. Health Endpoints

- `/health/`  
  Basic application health check (Django).

- `/healthz`  
  Nginx / container‑level health check, often used by load balancers or uptime monitors.

---

## 7. Summary of Data Lifecycle

1. **User signs up**  
   - Backend stores user in `users_app_userprofile`.
   - Sends email with confirm link → frontend.

2. **Admin uploads a video**  
   - `Video` model stores original file.
   - Signals enqueue conversions and thumbnail generation.
   - `processing_state` moves from `pending` → `processing` → `ready` (or `error`).

3. **Frontend lists videos**  
   - Calls `/content/`.
   - Shows spinner / disabled state if `processing_state` is not `ready`.

4. **User starts playback**  
   - Frontend requests `/content/video-url/<id>/?quality=...`.
   - Backend returns a presigned S3 URL.
   - Player streams directly from S3 (or local storage, in dev).

5. **Cleanup**  
   - When a `Video` is updated or deleted, RQ removes old files/renditions/thumbnails to avoid storage leaks.

This architecture keeps the web request/response path responsive while heavy video processing is offloaded to worker processes.
