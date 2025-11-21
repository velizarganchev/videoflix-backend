# VideoFlix Backend

[🌍 Live API](https://api.videoflix-velizar-ganchev-backend.com)

## Overview
VideoFlix Backend is a production‑ready Django 5 + DRF backend for a video‑streaming platform.  
It provides authentication, email workflows, video management, S3‑based media storage, background processing (FFmpeg + Redis RQ), and a complete Docker/Nginx/Certbot deployment stack.

A separate Angular 18 frontend can be found here:  
👉 **https://github.com/velizarganchev/videoflix-frontend**

---

## Features

### 🔐 Authentication
- Registration with email confirmation  
- Login / Logout using secure HttpOnly cookies  
- Password reset (email link)  
- User profile + favorites list

### 🎬 Video API
- List all videos (cached)
- Toggle favorites
- Return playback URL:
  - Local media → `/media/...`
  - S3 media → public or presigned URLs

### 🖼 Media Processing
- FFmpeg transcoding (120p/360p/720p/1080p)
- Automatic thumbnail generation
- Background workers using Redis RQ
- Local or S3 storage

### ⚙️ DevOps & Performance
- Nginx reverse proxy + HTTPS (Certbot)
- Health endpoints
- Dockerized orchestration (web, redis, worker, nginx)
- Automatic migrations, collectstatic, superuser bootstrap

---

## Project Structure

```
videoflix_backend_app/    # Settings, URLs, WSGI, middleware
users_app/                # Authentication, profiles, email flows
content_app/              # Video model, API, tasks, S3 helpers
middleware/               # Range request middleware
static/ staticfiles/      # Built static assets
uploads/                  # Local media (dev)
backend.entrypoint.sh     # Entry for web/worker containers
docker-compose.yml
Dockerfile
nginx.conf
```

---

## Environment Configuration

Two example environment files are provided:

- `.env.example.dev` → local development (local media, console email, SQLite/Postgres)
- `.env.example.prod` → production (S3, HTTPS, RDS, secure cookies)

Copy the one you need:
```bash
cp .env.example.dev .env
# or
cp .env.example.prod .env
```

---

## Local Development (without Docker)

### Requirements
- Python 3.12
- Redis 5+
- PostgreSQL OR SQLite
- FFmpeg installed

### Steps

```bash
# Create venv
python -m venv env
source env/bin/activate   # or ./env/Scripts/activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example.dev .env
# edit values if needed

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

Local media files: `/uploads/videos/`  
Local static: `/static/`

---

## Local Development (with Docker)

```bash
docker compose up -d --build
```

This starts:
- web (Gunicorn)
- rq_worker
- redis
- nginx (HTTP only unless certificates are added)

Stop:
```bash
docker compose down
```

---

## Production Deployment

The production stack includes:
- Gunicorn (web)
- Redis + RQ workers
- Nginx (reverse proxy + TLS)
- Certbot (auto renewal)
- AWS S3 (media)
- AWS RDS or any PostgreSQL

### Steps

```bash
# Prepare env
cp .env.example.prod .env
# fill secrets

# Pull latest backend image
docker compose pull web rq_worker

# Restart stack
docker compose up -d --force-recreate
```

### First-time HTTPS certificate:
```bash
docker compose run --rm certbot_bootstrap
docker compose restart nginx
```

---

## Running FFmpeg Tasks & Worker

Worker automatically starts via:

```bash
docker compose up -d rq_worker
```

It processes:
- Video transcoding  
- Thumbnail generation  
- Cleanup tasks on delete  

---

## API Endpoints

### Users
- `POST /users/register/`
- `POST /users/login/`
- `POST /users/logout/`
- `POST /users/forgot-password/`
- `POST /users/reset-password/`
- `GET  /users/confirm/?uid=...&token=...`

### Content
- `GET /content/` — list videos
- `POST /content/add-favorite/`
- `GET /content/video-url/<id>/?quality=360p`

### Health
- `/health/` (app)
- `/healthz` (nginx)

---

## Tests

```bash
DEBUG=1 USE_SQLITE_LOCAL=1 pytest -v
```

Run only users:
```bash
pytest users_app/tests -v
```

Run only videos:
```bash
pytest content_app/tests -v
```

---

## Contributing
1. Fork  
2. Create feature branch  
3. Write clean code + docstrings  
4. Submit PR

---

## Maintainer
**Velizar Ganchev**  
Email: ganchev.veli@gmail.com

