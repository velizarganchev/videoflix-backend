# 01 – Local Development Setup

This guide explains how to run **Videoflix Backend** locally for development, together with the Angular frontend.

---

## 1. Requirements

- Python 3.12
- Node 20+ and Angular CLI 18 (for the frontend)
- Redis 5+ running locally
- PostgreSQL or SQLite
- FFmpeg installed and on your `PATH`

---

## 2. Clone and Install

```bash
git clone https://github.com/velizarganchev/videoflix-backend.git
cd videoflix-backend

python -m venv env
source env/bin/activate        # Windows: .\env\Scripts\activate

pip install -r requirements.txt
```

---

## 3. Environment (.env)

For development you **do not** use Docker. Instead, configure Django via `.env`:

```bash
cp .env.example.dev .env
```

The dev template is tuned for:

- `DEBUG=True`
- `BACKEND_ORIGIN=http://127.0.0.1:8000`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `CORS_ALLOWED_ORIGINS=http://localhost:4200`
- `USE_S3_MEDIA=False` (local uploads under `uploads/`)
- `REDIS_LOCATION=redis://localhost:6379/0`
- Console email backend

Adjust DB settings if you want to use Postgres instead of SQLite.

---

## 4. Run Migrations and Server

```bash
python manage.py migrate
python manage.py createsuperuser  # optional, for Django admin
python manage.py runserver
```

The API will be available at http://127.0.0.1:8000.

Django admin lives at http://127.0.0.1:8000/admin/. Use it to upload videos.

---

## 5. Start Redis and RQ Worker

Make sure Redis is running locally (e.g. on Windows via WSL, or as a service). Then start the worker in a second terminal:

```bash
source env/bin/activate        # if not already active
python manage.py rqworker --worker-class videoflix_backend_app.simple_worker.SimpleWorker
```

This worker processes:

- Video transcoding (FFmpeg)
- Thumbnail generation
- Background email sending in production‑like setups

Monitor queues via Django‑RQ:

- http://127.0.0.1:8000/django-rq/

---

## 6. Frontend (Angular)

Clone the frontend separately:

```bash
git clone https://github.com/velizarganchev/videoflix-frontend.git
cd videoflix-frontend
npm install
ng serve
```

By default the dev frontend runs on http://localhost:4200 and talks to the backend at http://127.0.0.1:8000.

Make sure the dev `.env` in the backend and the Angular environment files use matching URLs and CORS origins.

---

## 7. Typical Dev Flow

- Run Redis
- Start Django (`runserver`)
- Start RQ worker (`rqworker ... SimpleWorker`)
- Start Angular (`ng serve`)
- Upload a video via Django admin
- Watch transcoding jobs and thumbnails appear in `/django-rq/`
