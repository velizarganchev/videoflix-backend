# Local Development Setup

This document explains how to run the Videoflix backend **locally** for development, both:

1. Directly with `manage.py runserver` (recommended for day‑to‑day coding)
2. Via `docker compose` (to simulate the production stack)

---

## 1. Direct Django + Redis + FFmpeg (no Docker)

### 1.1 Requirements

- Python **3.12**
- PostgreSQL or SQLite (SQLite is fine for dev)
- Redis **5+**
- FFmpeg installed and available in your `PATH`
- Git

### 1.2 Clone & create virtualenv

```bash
git clone https://github.com/velizarganchev/videoflix-backend.git
cd videoflix-backend

python -m venv env
source env/bin/activate        # Linux/macOS
# .\env\Scripts\activate    # Windows PowerShell / CMD
```

### 1.3 Install dependencies

```bash
pip install -r requirements.txt
```

### 1.4 Configure `.env` for DEV

Copy the example and adjust only what you need:

```bash
cp .env.example.dev .env
```

Key settings for dev (excerpt):

```env
# CORE / SECURITY (DEV)
DEBUG=True
SECRET_KEY=dev-secret-key-change-me

BACKEND_ORIGIN=http://127.0.0.1:8000
ALLOWED_HOSTS=localhost,127.0.0.1

# FRONTEND (DEV)
CORS_ALLOWED_ORIGINS=http://localhost:4200
CSRF_TRUSTED_ORIGINS=http://localhost:4200

FRONTEND_URL=http://localhost:4200/login
FRONTEND_CONFIRM_URL=http://localhost:4200/confirm
RESET_PASSWORD_URL=http://localhost:4200/reset-password

# COOKIES (DEV)
JWT_COOKIE_SAMESITE=None
JWT_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False

# REDIS / RQ (DEV)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_LOCATION=redis://localhost:6379/0

# EMAIL (DEV)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=dev@example.com

# MEDIA (DEV: LOCAL FILES)
USE_S3_MEDIA=False
MEDIA_URL=/media/
MEDIA_ROOT=/uploads/videos/
```

> In dev, media is stored **locally**, and password reset / confirmation emails are printed to the console.

### 1.5 Database migrations

```bash
python manage.py migrate
```

### 1.6 Create a superuser (optional but recommended)

```bash
python manage.py createsuperuser
```

### 1.7 Start services

#### 1.7.1 Redis

- Either run Redis as a service
- Or start it manually in a terminal:

```bash
redis-server
```

#### 1.7.2 Django dev server

```bash
python manage.py runserver
```

#### 1.7.3 RQ worker

In another terminal (with the venv activated):

```bash
python manage.py rqworker --with-scheduler
```

Now the backend is reachable at **http://127.0.0.1:8000**.

### 1.8 Connect the Angular frontend

In the Angular frontend repo (separate project):

- Ensure `environment.ts` has `baseApiUrl` set to `http://127.0.0.1:8000`
- Run:

```bash
ng serve
```

Your dev stack now is:

- Frontend: `http://localhost:4200`
- Backend API: `http://127.0.0.1:8000`

---

## 2. Local Docker Stack (HTTP only)

You can also start the backend using **docker compose**, which runs:

- Django + Gunicorn
- Redis
- RQ worker
- Nginx (HTTP only, port 80)

### 2.1 Requirements

- Docker
- docker‑compose / Docker Compose plugin

### 2.2 Create `.env`

You can reuse `.env.example.dev`:

```bash
cp .env.example.dev .env
```

> When running under Docker, `REDIS_HOST` should be `redis` and DB settings should match the `docker-compose.yml` file if you enable Postgres in containers.  
> For simple testing you can still point to a remote or local Postgres instance.

### 2.3 Start the stack

```bash
docker compose up -d --build
```

This will:

- build the web image
- run migrations and collectstatic on container start
- start the `web`, `redis`, `rq_worker` and `nginx` services

By default:

- Nginx is exposed on **port 80**
- API should be reachable at: `http://localhost`

### 2.4 Stop the stack

```bash
docker compose down
```

### 2.5 Logs

View logs for web:

```bash
docker compose logs web -f
```

View logs for worker:

```bash
docker compose logs rq_worker -f
```

---

## 3. Switching Between Local Files and S3 (for testing)

Even in local dev you can test the S3 mode by setting in `.env`:

```env
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=eu-central-1
AWS_S3_QUERYSTRING_AUTH=True   # presigned URLs mode
```

If you keep `USE_S3_MEDIA=False`, the project stores everything under `MEDIA_ROOT` (`/uploads/videos/`), which is usually easier during development.
