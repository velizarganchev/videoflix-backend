# VideoFlix Backend

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache%20%2B%20RQ-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-Custom-lightgrey.svg)](#license)

A production-ready Django + Django REST Framework backend for a video streaming platform. It provides user auth and email workflows, content management, S3-backed media storage with optional signed URLs, background video processing via RQ workers (FFmpeg), Redis caching, and a Dockerized deployment stack fronted by Nginx and Certbot.


## Features

- Authentication & Users
  - Token-based auth (DRF TokenAuthentication)
  - Registration with email confirmation
  - Login/Logout, password reset (email link)
  - User profile with favorites (ManyToMany to videos)

- Video Content API
  - List videos, retrieve single video
  - Toggle favorites per user
  - Get video playback URL
    - Local storage: direct URL under `/media/`
    - S3 storage: public or pre-signed URL

- Media & Processing
  - Image and video stored in S3 (when enabled)
  - Background tasks using RQ/Redis
  - FFmpeg-based transcoding helpers (120p/360p/720p/1080p)
  - Auto-thumbnail generation on create (via MoviePy) when possible

- Performance & Ops
  - Redis-backed cache with per-view caching
  - Health endpoints: `/health` (app), `/healthz` (nginx)
  - Admin, django-import-export, (optional) debug toolbar

- Dockerized Deployment
  - Services: web (Gunicorn), rq_worker, redis, nginx, certbot
  - Automatic migrations, collectstatic, and superuser bootstrap
  - HTTPS with Let’s Encrypt via Certbot (volumes for cert persistence)


## Technologies

- Python 3.12, Django 5.1, Django REST Framework 3.15
- Redis 5+ (cache + RQ queues)
- RQ workers for background jobs
- FFmpeg, MoviePy for video handling
- PostgreSQL (prod) / SQLite (optional local dev)
- Nginx as reverse proxy + TLS termination (Certbot)
- AWS S3 (django-storages) for media (optional)
- Docker & docker-compose for orchestration


## Project structure (high level)

- `videoflix_backend_app/` – settings, URLs, WSGI, simple RQ worker
- `users_app/` – custom `UserProfile`, auth flows, email tasks
- `content_app/` – `Video` model, API, S3 helpers, video tasks
- `middleware/` – range requests middleware for media
- `static/`, `staticfiles/`, `uploads/` – static & media structure
- `backend.entrypoint.sh` – DB migrate, collectstatic, start web/worker
- `docker-compose.yml`, `Dockerfile`, `nginx.conf` – deployment stack


## Configuration

Environment variables are read via `django-environ` and `.env`. Common settings:

- Core
  - `SECRET_KEY`
  - `DEBUG` (true/false)
  - `ALLOWED_HOSTS` (CSV)

- Database (PostgreSQL)
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - `USE_SQLITE_LOCAL` (true/false) – optional for local dev when `DEBUG=true`

- Redis / Cache / RQ
  - `REDIS_HOST` (default `redis` in Docker)
  - `REDIS_LOCATION` (default `redis://redis:6379/0`)

- CORS / CSRF
  - `CORS_ALLOWED_ORIGINS` (CSV)
  - `CSRF_TRUSTED_ORIGINS` (CSV)

- Email
  - `EMAIL_BACKEND` (default SMTP)
  - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`
  - `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
  - `DEFAULT_FROM_EMAIL`
  - `RESET_PASSWORD_URL` (frontend route)
  - `FRONTEND_URL` (login redirect)
  - `URL` (backend base URL)

- S3 Media (optional)
  - `USE_S3_MEDIA` (true/false)
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - `AWS_STORAGE_BUCKET_NAME`
  - `AWS_S3_REGION_NAME` (e.g. `eu-central-1`)
  - `AWS_S3_QUERYSTRING_AUTH` (false for public URLs, true for signed)

- Bootstrap (Docker)
  - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL`

> Note (Windows local dev): make sure your Redis server is v5+ if you run it locally. Alternatively, run everything via Docker.


## Installation (Local, without Docker)

Prerequisites: Python 3.12, PostgreSQL (or SQLite), Redis 5+

```bash
# 1) Create and activate venv
python -m venv env
./env/Scripts/activate  # Windows

# 2) Install deps
pip install -r requirements.txt

# 3) Configure environment
copy NUL .env  # create an empty .env on Windows, then fill variables

# Minimal .env example (edit values):
# SECRET_KEY=change-me
# DEBUG=true
# ALLOWED_HOSTS=localhost,127.0.0.1
# USE_SQLITE_LOCAL=true
# EMAIL_HOST_USER=your@email
# EMAIL_HOST_PASSWORD=your-app-password
# RESET_PASSWORD_URL=http://localhost:4200/reset-password
# FRONTEND_URL=http://localhost:4200/login
# URL=http://localhost:8000

# 4) Migrate & run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Media (local): served from `/media/` mapped to `uploads/`. Static files: `/static/`.


## Usage

Base URLs (see `videoflix_backend_app/urls.py`):
- Root: `GET /` → "Welcome to VideoFlix API!"
- Health: `GET /health/`
- Admin: `/admin/`
- RQ dashboard: `/django-rq/`
- Users API: `/users/`
  - `POST /users/register/` – register (inactive) and send confirmation email
  - `GET /users/confirm/?uid=...&token=...` – activate account, redirects to frontend
  - `POST /users/login/` – returns user profile with token
  - `POST /users/logout/` – revoke token (auth required)
  - `POST /users/forgot-password/` – send reset link (generic response)
  - `POST /users/reset-password/` – set new password
  - `GET /users/profiles/`, `GET /users/profile/<id>/` – profile listing/details
- Content API: `/content/`
  - `GET /content/` – list videos (auth required)
  - `GET /content/<id>/` – video details
  - `POST /content/add-favorite/` – toggle favorite `{ video_id }`
  - `GET /content/video-url/<id>/?quality=360p` – return S3 or local URL for playback

Authentication: include `Authorization: Token <token>` header for protected endpoints.


## Docker Deployment

The stack includes: web (Gunicorn), rq_worker, redis, nginx, certbot.

```bash
# 1) Prepare .env (see Configuration section)
copy NUL .env  # Windows, then edit with your values

# 2) Bring up stack
docker compose up -d --build

# 3) (Optional) Bootstrap TLS cert once
# docker compose run --rm certbot_bootstrap

# 4) Check
# - https://your-domain/.well-known/acme-challenge/ (for cert challenges)
# - https://your-domain/health (Django)
# - https://your-domain/ (proxied by nginx)
```

Nginx serves static at `/static/` and proxies app to the `web` service on port 8000. Media in production is expected to be on S3 when `USE_S3_MEDIA=true`. If you prefer local media behind Nginx, add the `/media/` alias to `nginx.conf` (already present in sample configs).


## Contributing

- Fork the repo and create a feature branch
- Follow existing code style and add docstrings where helpful
- Open a PR with a clear description of the change and rationale


## License

Specify your license here (MIT recommended). If you add a `LICENSE` file, update this section and badge accordingly.


## Contact

- Maintainer: Velizar Ganchev
- Email: ganchev.veli@gmail.com
- API Host (prod): https://api.videoflix-velizar-ganchev-backend.com
