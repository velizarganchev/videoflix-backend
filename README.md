# VideoFlix Backend

[🌍 Live API](https://api.videoflix-velizar-ganchev-backend.com)

A production‑ready **Django 5 + DRF** backend powering the VideoFlix streaming platform.  
It provides authentication, secure cookie‑based sessions, email workflows, video management,
S3 media storage, background processing with FFmpeg + Redis RQ, and a full Docker/Nginx/Certbot stack.

The Angular 18 frontend lives in a separate repository:  
👉 **https://github.com/velizarganchev/videoflix-frontend**

---

## 1. Architecture Overview

```text
┌──────────────────────────┐
│      Angular 18 SPA      │
│  (videoflix-frontend)    │
└────────────┬─────────────┘
             │ HTTPS (JWT in HttpOnly cookies)
┌────────────▼─────────────┐
│       Nginx Reverse      │
│   Proxy + TLS (Certbot)  │
└────────────┬─────────────┘
             │ proxy_pass
┌────────────▼─────────────┐
│  Django 5 + DRF (Gunicorn)│
│  - Auth, Users, Content   │
│  - Signed S3 URLs         │
└────────────┬─────────────┘
     ORM     │
┌────────────▼─────────────┐
│       PostgreSQL (RDS)   │
└──────────────────────────┘

Background media pipeline:

┌───────────────┐      enqueue jobs     ┌───────────────────────┐
│   Django API  │ ───────────────────► │ Redis + RQ Worker     │
└───────────────┘                      │ (FFmpeg transcoding,  │
                                       │  thumbnails, cleanup) │
                                       └───────────┬───────────┘
                                           write   │
                                         media     ▼
                                       ┌───────────────────────┐
                                       │   AWS S3 Bucket       │
                                       └───────────────────────┘
```

---

## 2. Features

### 🔐 Authentication & Security

- Registration with **email confirmation**
- Login / Logout using **JWT in HttpOnly cookies**
- Password reset via secure email link
- User profile with favorite videos
- CSRF + CORS properly configured for SPA + API
- Refresh‑token flow handled transparently via frontend interceptor

### 🎬 Video API

- List all videos (short‑lived cached for performance)
- Group by category / favorites
- Toggle favorites per user
- Generate playback URL
  - Local media → `/media/...`
  - S3 media → **presigned** URLs (time‑limited access)

### 🖼 Media Processing

- FFmpeg transcoding to **120p / 360p / 720p / 1080p**
- Asynchronous conversions via Redis RQ
- Automatic thumbnail generation
- Cleanup of original + renditions on update/delete
- Backend exposes **processing_state + processing_error** so the frontend
  can show a spinner or error thumb while transcoding.

### ⚙️ DevOps & Deployment

- Dockerized services:
  - `web` (Gunicorn + Django)
  - `rq_worker` (Redis RQ worker)
  - `redis`
  - `nginx`
  - `certbot_bootstrap` (one‑shot)
- Nginx with HTTPS, HSTS and basic hardening
- Health endpoints:
  - `/health/` (app)
  - `/healthz` (nginx)

---

## 3. Tech Stack

- **Backend**: Python 3.12, Django 5, Django REST Framework
- **Auth**: Simple JWT (+ custom cookie handling)
- **Tasks**: Redis + RQ, FFmpeg
- **Database**: PostgreSQL (RDS in production, SQLite optional in dev)
- **Storage**: Local filesystem or AWS S3
- **Web server**: Gunicorn behind Nginx
- **Containerization**: Docker & Docker Compose
- **Cloud**: AWS EC2, RDS, S3 (recommended setup)

---

## 4. Requirements

### Local (no Docker)

- Python **3.12**
- Redis **5+**
- PostgreSQL 14+ (or SQLite for quick dev)
- FFmpeg installed and available in `PATH`
- Node / Angular CLI (for running the frontend, if needed)

### Docker

- Docker Engine
- Docker Compose V2

---

## 5. Environment Files

Two example env files are included:

- `.env.example.dev` – local development (no Docker or simple Docker dev)
- `.env.example.prod` – production (EC2 + RDS + S3 + HTTPS)

Typical usage:

```bash
# Local dev
cp .env.example.dev .env

# Production (on the server)
cp .env.example.prod .env
```

Edit all placeholders (`your-...`) before running anything.

---

## 6. Local Development (without Docker)

This is the **recommended** workflow for day‑to‑day development.

### 6.1. Setup

```bash
# Create virtualenv
python -m venv env
source env/bin/activate      # Windows: .\env\Scriptsctivate

# Install dependencies
pip install -r requirements.txt

# Create env file
cp .env.example.dev .env
# edit SECRET_KEY, DB_*, REDIS_*, etc. as needed
```

Run migrations:

```bash
python manage.py migrate
```

Create superuser (optional):

```bash
python manage.py createsuperuser
```

### 6.2. Run Django API

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000`.

### 6.3. Run Redis RQ Worker (local)

FFmpeg conversions and thumbnails require a running worker.  
Use the **custom SimpleWorker class**:

```bash
python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
```

By default this listens on the `default` queue.  
Make sure Redis is running (e.g. `redis-server` locally, or Docker Redis).

### 6.4. Run the Angular Frontend (optional)

Clone and start the frontend:

```bash
git clone https://github.com/velizarganchev/videoflix-frontend.git
cd videoflix-frontend
npm install
ng serve
```

The app will be at `http://localhost:4200`.  
`.env.example.dev` is already configured for this origin:

- `CORS_ALLOWED_ORIGINS=http://localhost:4200`
- `CSRF_TRUSTED_ORIGINS=http://localhost:4200`

---

## 7. Local Development (with Docker)

You can also run everything locally via Docker (no TLS):

```bash
docker compose up -d --build
```

This starts:

- `web` – Django + Gunicorn
- `rq_worker` – Redis RQ worker with FFmpeg
- `redis`
- `nginx` – HTTP reverse proxy on port 80

Stop everything:

```bash
docker compose down
```

> Note: This setup is mostly to test the containers. For everyday coding,
> `runserver` + local Redis is usually faster and simpler.

---

## 8. Production Deployment (AWS)

This section assumes:

- **EC2** instance (e.g. `c6a.large` or `t3.small` for small demo)
- **RDS PostgreSQL** database
- **S3** bucket for video + thumbnails
- A domain like `api.your-domain.com` pointing to the EC2 instance

### 8.1. Prepare the Server

On the EC2 host:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# re-login
```

Clone the repo:

```bash
git clone https://github.com/velizarganchev/videoflix-backend.git
cd videoflix-backend
```

Copy prod env and fill values:

```bash
cp .env.example.prod .env
nano .env
```

Make sure you set:

- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`
- `DB_*` pointing to RDS
- `AWS_*` pointing to S3
- `USE_S3_MEDIA=True`
- proper email SMTP settings
- secure cookie flags (`JWT_COOKIE_SECURE=True`, etc.)

### 8.2. SSL CA Bundle for RDS

If you use RDS with SSL:

- Download `rds-combined-ca-bundle.pem`
- Place it at project root and keep `DB_SSL_ROOTCERT=/app/rds-combined-ca-bundle.pem` in `.env`

### 8.3. First Docker Run (HTTP only)

Before requesting certificates, run the stack once:

```bash
docker compose up -d --build
```

This will:

- run migrations
- collect static files
- (optionally) create a superuser from env vars
- start web, worker, redis, nginx (HTTP only)

Check health:

- `curl http://YOUR_IP/health/`
- `curl http://YOUR_IP/healthz`

### 8.4. HTTPS with Certbot

Request certificates:

```bash
docker compose run --rm certbot_bootstrap
docker compose restart nginx
```

Nginx now terminates TLS for `https://api.your-domain.com`.

### 8.5. Updating the Backend

On subsequent deployments:

```bash
git pull origin main
docker compose pull web rq_worker
docker compose up -d --force-recreate
```

---

## 9. Security Notes

### 9.1. HttpOnly JWT Cookies

- Access and refresh tokens are stored in **HttpOnly cookies**:
  - `vf_access`
  - `vf_refresh`
- They are not accessible from JavaScript, protecting against XSS.

### 9.2. Refresh Token Flow

- When the access token expires, the frontend interceptor calls a refresh endpoint.
- If refresh succeeds, new cookies are set and the original request is retried.
- If refresh fails (no valid refresh token), the user is logged out.

### 9.3. CORS & CSRF

- CORS allows only the configured frontend origin(s).
- `CORS_ALLOW_CREDENTIALS=True` to send cookies.
- CSRF cookie is secured in production and marked as `SameSite=None` to work with SPA + cookies.

### 9.4. HTTPS

- Nginx terminates TLS using Let’s Encrypt certificates.
- HSTS header (`Strict-Transport-Security`) is enabled for 1 year.

---

## 10. Media Pipeline & Worker Tuning

### 10.1. What Happens on Upload

1. Admin uploads a video file to a `Video` object.
2. `post_save` signal enqueues:
   - 120p, 360p, 720p, 1080p transcode jobs
   - thumbnail generation job
3. Worker performs:
   - Download from S3 (if `USE_S3_MEDIA=True`) or reads from local MEDIA_ROOT
   - FFmpeg transcode
   - Upload back to S3 / local MEDIA_ROOT
4. `Video.converted_files` and `image_file` are updated.
5. `processing_state` is moved from `pending` → `processing` → `ready`.
6. Frontend:
   - shows a spinner while `processing_state` is not `ready`
   - allows playback only when ready
   - can optionally show an error thumb if `processing_state === 'error'`.

### 10.2. Worker Command (recap)

- **Local (without Docker)**:

  ```bash
  python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
  ```

- **Docker**: the `rq_worker` service in `docker-compose.yml` uses the same class.

### 10.3. Performance Notes

- CPU is the main factor for FFmpeg speed.
- For small demos, `t3.small` works but transcoding may take 1–3 minutes for ~70MB.
- For smoother experience during evaluations, a **`c6a.large`** (2 vCPUs, cheaper than `t3.xlarge`)
  significantly speeds up transcoding while staying cost‑effective.

---

## 11. API Reference

A more detailed API reference with example requests/responses is available in:

- `docs/06-api-reference.md`

Short summary of main endpoints:

### Users

- `POST /users/register/`
- `GET  /users/confirm/?uid=...&token=...`
- `POST /users/login/`
- `POST /users/logout/`
- `POST /users/forgot-password/`
- `POST /users/reset-password/`

### Content

- `GET /content/` – list videos
- `POST /content/add-favorite/` – toggle favorites
- `GET /content/video-url/<id>/?quality=360p` – get signed URL for a given quality

### Health

- `GET /health/` – Django app health
- `GET /healthz` – Nginx health

---

## 12. Tests

Run tests locally (recommended with SQLite):

```bash
DEBUG=1 USE_SQLITE_LOCAL=1 pytest -v
```

Specific apps:

```bash
pytest users_app/tests -v
pytest content_app/tests -v
```

---

## 13. Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests and docstrings where appropriate
4. Run tests and linters
5. Open a pull request

---

## 14. Maintainer

**Velizar Ganchev**  
📧 ganchev.veli@gmail.com
