# 02 – Production Setup on AWS

This document describes a typical production deployment of Videoflix Backend on AWS using Docker Compose.

---

## 1. AWS Components

A minimal setup uses:

- **EC2 instance** – host for the Docker stack (Ubuntu recommended)
- **RDS Postgres** – managed PostgreSQL database
- **S3 bucket** – media storage for videos + thumbnails
- **Route 53** (optional) – DNS for `api.your-domain.com`
- **IAM roles / users** – access to S3 (and optionally parameter store / secrets manager)

---

## 2. Prepare the EC2 Host

1. Create an EC2 (e.g. `t3.small` for testing, `c6a.large` or similar for heavier transcoding).  
2. Open ports:
   - 22 (SSH) – your IP only
   - 80, 443 – public
3. SSH into the instance and install Docker + docker compose plugin.

Copy your project (or clone from a private repo) to the server.

---

## 3. Production Environment (.env)

On the server, create `.env` from the production example:

```bash
cp .env.example.prod .env
```

Fill in:

- `BACKEND_ORIGIN=https://api.your-domain.com`
- `ALLOWED_HOSTS=api.your-domain.com,your-frontend-domain.com`
- `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` for your frontend
- Database values for RDS: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- TLS/SSL options for Postgres if needed (`DB_SSL_REQUIRE`, `DB_SSL_ROOTCERT`)
- Redis settings: `REDIS_LOCATION=redis://redis:6379/0`
- S3: `USE_S3_MEDIA=True`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`
- Cookie flags (`JWT_*`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_SECURE=True`)

---

## 4. Bring Up the Stack

```bash
docker compose pull web rq_worker redis nginx certbot_bootstrap
docker compose up -d --build
```

Services:

- `web` – Gunicorn + Django app
- `rq_worker` – RQ worker using `videoflix_backend_app.simple_worker.SimpleWorker`
- `redis` – Redis broker
- `nginx` – reverse proxy + HTTP/HTTPS
- `certbot_bootstrap` – one‑off helper for HTTPS

### 4.1 TLS Certificates

First run (once):

```bash
docker compose run --rm certbot_bootstrap
docker compose restart nginx
```

Certificates are stored in the mounted `/etc/letsencrypt` volume and renewed automatically by the Certbot service (if configured).

---

## 5. RQ Dashboard and Monitoring

In production, the Django‑RQ dashboard is reachable at:

- `https://api.your-domain.com/django-rq/`

You can inspect:

- Queues and job status  
- Failed jobs and tracebacks (useful for debugging FFmpeg problems)  
- Worker heartbeats

Docker logs are also useful:

```bash
docker compose logs -f web
docker compose logs -f rq_worker
docker compose logs -f nginx
```

---

## 6. Scaling & Instance Type

For video transcoding it's helpful to use a compute‑optimized instance with more CPU and RAM than a tiny free‑tier host.

- For light demo/testing: `t3.small` or `t3.medium` may be enough.  
- For smoother transcoding: `c6a.large` (2 vCPU, 4 GiB) or similar gives noticeably better performance at reasonable cost.

You can change the instance type from the EC2 console without reinstalling the stack (stop instance → change type → start).

---

## 7. Backups

- Use RDS automated backups or manual snapshots for the database.
- Version or lifecycle‑manage the S3 bucket (for cost control).  
- Keep a copy of `.env` and your Docker images / source code in a private Git repo.
