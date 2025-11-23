# 04 – Architecture & Data Flow

This document complements the short overview in the main `README.md` and goes deeper into how Videoflix Backend is put
together and how requests flow through the system.

---

## 1. High‑Level Components

```text
+-------------------------+
|     Angular Frontend    |
|  (videoflix-frontend)   |
+------------+------------+
             |
             | HTTPS (JWT cookies, JSON)
             v
+------------+------------+
|     Nginx Reverse Proxy |
+------------+------------+
             |
             | proxy_pass to Gunicorn
             v
+-------------------------+
|   Django + DRF Backend  |
|  (videoflix-backend)    |
+------+------+-----------+
       |      |
       |      | enqueue jobs
       |      v
       |  +---+------------------+
       |  |  RQ Worker (FFmpeg)  |
       |  | SimpleWorker class   |
       |  +----------+-----------+
       |             |
       |             | reads/writes
       v             v
+-------------+   +-------------------+
|  Postgres   |   |  Media Storage    |
| (RDS / dev) |   |  S3 or local FS   |
+-------------+   +-------------------+
```

- The frontend communicates only with Django via JSON APIs and HttpOnly cookies.  
- Nginx terminates TLS and proxies requests to Gunicorn (WSGI).  
- Heavy video work is delegated to a background worker using Redis + RQ.  
- Final media files live either on S3 (production) or under `uploads/` (dev).

---

## 2. Request / Response Flow

1. Browser sends a request to `https://api.your-domain.com/...` with cookies.  
2. Nginx forwards the request to the `web` container (Gunicorn).  
3. Django + DRF handle routing, authentication, permissions, and serialization.  
4. Responses go back through Nginx to the client.

Because JWTs are stored in HttpOnly cookies, JavaScript cannot read or modify them. Authentication is handled entirely on
the server side (via SimpleJWT cookie integration).

---

## 3. Video Upload & Processing

1. Admin uploads a video file via Django admin.  
2. The `Video` model is saved and a post‑save signal enqueues background jobs:
   - One job per target resolution (120p / 360p / 720p / 1080p)
   - One job for thumbnail generation
3. The `rq_worker` container (or the local worker in dev) picks up these jobs:
   - Downloads the source from S3 (or reads from local disk)
   - Runs FFmpeg to create renditions
   - Uploads renditions back to S3 / local media
   - Updates the `converted_files` JSON field on the `Video` row
   - Generates and stores a thumbnail (`image_file`)
4. The frontend periodically receives updated `processing_state` values from the `/content/` endpoint and can show spinners,
   disabled cards, or errors based on that state.

Cleanup paths (pre‑save and post‑delete signals) ensure that old renditions and thumbnails are removed when a video is
replaced or deleted.

---

## 4. Streaming Flow

1. Frontend lists videos via `GET /content/` and shows thumbnails.  
2. When the user starts playback, the player requests:

   ```http
   GET /content/video-url/<id>/?quality=720p
   ```

3. Backend resolves the correct file key via `Video.get_key_for_quality()` and returns:

   - A **presigned S3 URL** when `USE_S3_MEDIA=True` and `AWS_S3_QUERYSTRING_AUTH=True`.  
   - A **public S3 URL** when querystring auth is disabled and the bucket is public.  
   - A **local `/media/...` URL** when running in dev with local storage.

4. The video player streams directly from S3 or local storage; Django is not in the hot path for bytes transfer.

---

## 5. Background Jobs & Monitoring

- All jobs are queued into Redis (queue name: usually `"default"`).  
- The custom `SimpleWorker` is used so long FFmpeg runs are handled reliably.  
- Django‑RQ provides a web dashboard at `/django-rq/` where you can:
  - Inspect queues and workers
  - See job history and failures
  - Requeue or delete failed jobs

In production this URL is protected by Django's admin authentication and should only be accessible to staff.

