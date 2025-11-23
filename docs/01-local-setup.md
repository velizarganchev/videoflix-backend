# 01 – Local setup (development)

This document explains how to run the **Videoflix backend** on your local machine and connect it to the Angular frontend.

You can either:

1. Use the **Docker dev stack** (recommended), or
2. Run the backend directly via a Python virtual environment.

The examples below assume a UNIX‑like shell; on Windows adapt the activation commands accordingly.

---

## 1. Prerequisites

- Python 3.12+ (only needed for the virtualenv option)
- Docker & Docker Compose
- Git
- Node.js + npm (for the Angular frontend)
- FFmpeg (only required if you run everything outside Docker; the dev stack already includes it)

---

## 2. Clone repositories

Clone the backend:

```bash
git clone https://github.com/velizarganchev/videoflix-backend.git
cd videoflix-backend
```

Clone the frontend (in a separate folder):

```bash
git clone https://github.com/velizarganchev/videoflix-frontend.git
```

The frontend repository contains its own README with more details, but we assume the standard Angular dev setup (`ng serve`).

---

## 3. Environment file for development

In the backend folder create your dev `.env`:

```bash
cp .env.example.dev .env
```

Key values for local work:

```env
DEBUG=True

# Backend origin used for building confirmation links
BACKEND_ORIGIN=http://127.0.0.1:8000

# Where to redirect after successful confirmation / reset
FRONTEND_LOGIN_URL=http://localhost:4200/login
FRONTEND_RESET_PASSWORD_URL=http://localhost:4200/reset-password

# Redis / RQ
USE_REDIS=True         # required for Docker dev stack
REDIS_HOST=redis
REDIS_PORT=6379

# Media storage
USE_S3_MEDIA=False     # local filesystem for dev
```

Email settings:

- If you keep the default console backend, emails are printed to the backend logs.
- If you want to test with a real provider (e.g. Gmail SMTP), configure the `EMAIL_*` variables here. See `docs/03-env-files.md` for examples.

---

## 4. Option A – Docker dev stack (recommended)

This option mirrors the production architecture (web + worker + Redis) but uses Django’s development server with auto‑reload.

### 4.1 Start the stack

From the backend folder:

```bash
docker compose -f docker-compose.dev.yml up --build
```

On subsequent runs you can usually omit `--build`:

```bash
docker compose -f docker-compose.dev.yml up
```

Services started:

- `videoflix_web_dev` – Django dev server on `http://0.0.0.0:8000`
- `videoflix_rq_worker_dev` – RQ worker for video processing + emails
- `videoflix_redis_dev` – Redis instance

Django will automatically apply migrations and ensure a default dev superuser (usually `admin` / `admin`, see `settings.py` / docs).

You can now open:

- `http://127.0.0.1:8000/admin/` – Django admin
- `http://127.0.0.1:8000/users/` – user‑related API endpoints (DRF browsable API)
- `http://127.0.0.1:8000/content/` – content API

### 4.2 Start the Angular frontend

In the frontend folder:

```bash
cd videoflix-frontend
npm install
ng serve
```

Angular dev server runs on `http://localhost:4200` and is configured to call the API at `http://127.0.0.1:8000` (via environment files and HTTP interceptors).

### 4.3 Email flows in dev

When you register a user from the frontend:

1. Backend creates an inactive user.
2. A short‑lived access token is generated and embedded in a confirmation URL.
3. Depending on your `.env`:
   - With console backend – the email (including HTML) appears in the **web container logs**.
   - With real SMTP – the message is sent to your inbox.

The confirmation endpoint checks the token and user ID, activates the user and then redirects to `FRONTEND_LOGIN_URL`. The same approach is used for password reset (`FRONTEND_RESET_PASSWORD_URL`).

If a link ever causes a 400 error in the DRF browsable API, open it directly in the browser – the redirect view returns a plain HTTP redirect, not a JSON response.

---

## 5. Option B – Run directly via virtualenv

If you prefer to run everything on your host machine without Docker:

### 5.1 Create and activate virtualenv

```bash
python -m venv env
source env/bin/activate          # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 5.2 Configure `.env`

Create `.env` from `.env.example.dev` and set:

```env
DEBUG=True
USE_REDIS=False          # unless you have a local Redis server
USE_S3_MEDIA=False
```

If you do **not** use Redis locally, background jobs (transcoding, thumbnails, emails) need to be triggered manually or disabled – the main FFmpeg pipeline is primarily optimised for RQ workers.

### 5.3 Apply migrations and runserver

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 5.4 (Optional) Start RQ worker

If you have Redis running locally and set `USE_REDIS=True`:

```bash
python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
```

This matches what the Docker worker container does.

---

## 6. Troubleshooting

- **Container builds are slow** – the first build installs all Python dependencies and FFmpeg. Subsequent builds reuse layers; use `docker compose -f docker-compose.dev.yml build web rq_worker` to rebuild only backend images.
- **Emails not visible in logs** – check if you switched from console backend to a real SMTP backend; in that case inspect your mailbox instead of the console.
- **CORS / cookie issues** – ensure the frontend dev domain (`http://localhost:4200`) is allowed in `CORS_ALLOWED_ORIGINS` and that you access it over the same scheme as configured (HTTP vs HTTPS).
- **Videos not transcoding** – verify that `USE_REDIS=True`, Redis is running and the worker container has started without errors.

For anything more related to production and deployment, continue with `02-production-setup-aws.md` and `05-deployment-guide.md`.
