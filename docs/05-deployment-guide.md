# Deployment & Operations Guide

This document focuses on **day‑to‑day operations** once the Videoflix backend is already set up in development or production.

It covers:

- common Docker commands
- updating code and images
- checking logs
- managing migrations
- troubleshooting

---

## 1. Common Docker Commands

All commands assume you are in the project root, next to `docker-compose.yml`.

### 1.1 Start the stack

```bash
docker compose up -d
```

or with a rebuild:

```bash
docker compose up -d --build
```

### 1.2 Stop the stack

```bash
docker compose down
```

### 1.3 Restart specific service

```bash
docker compose restart web
docker compose restart rq_worker
docker compose restart nginx
```

### 1.4 View logs

```bash
docker compose logs web -f
docker compose logs rq_worker -f
docker compose logs nginx -f
docker compose logs redis -f
```

Use `Ctrl + C` to exit the log tail.

---

## 2. Updating the Application

### 2.1 If you build images locally

1. Pull latest code:

   ```bash
   git pull origin main
   ```

2. Rebuild and restart services:

   ```bash
   docker compose up -d --build
   ```

Migrations and static collection will run automatically on `web` start (via entrypoint).

### 2.2 If you use Docker Hub or another registry

1. Pull latest images:

   ```bash
   docker compose pull web rq_worker
   ```

2. Recreate containers:

   ```bash
   docker compose up -d --force-recreate
   ```

This avoids rebuilding on the server.

---

## 3. Migrations & Database Tasks

Normally, migrations are handled automatically by the entrypoint when `web` starts.

If you ever need to run them manually in the container:

```bash
docker compose exec web python manage.py migrate
```

Or to create a new migration from changed models:

```bash
docker compose exec web python manage.py makemigrations
```

> In production, it is usually better to create migrations locally, commit them, and then deploy, instead of generating them directly on the server.

---

## 4. Superuser Management

To create a superuser manually inside the `web` container:

```bash
docker compose exec web python manage.py createsuperuser
```

You can also set environment variables:

```env
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

and rely on the entrypoint to create the superuser automatically on first run (if implemented that way). Remember to remove or change these values once the initial setup is done.

---

## 5. RQ Worker & FFmpeg Jobs

### 5.1 Checking worker status

Use logs:

```bash
docker compose logs rq_worker -f
```

You should see output such as:

- Worker started
- Jobs being enqueued / dequeued
- Any exceptions during FFmpeg runs

### 5.2 Re‑starting workers

If a worker crashes or you change code related to tasks:

```bash
docker compose restart rq_worker
```

Workers will reconnect to Redis and start processing jobs again.

---

## 6. SSL & Certbot

If you change domains or need to renew certificates manually:

### 6.1 Run certbot bootstrap again

```bash
docker compose run --rm certbot_bootstrap
docker compose restart nginx
```

Certificates are stored in a persistent volume, so they remain across restarts.

For automated renewal, the `certbot` container (if present in the stack) can be scheduled via cron or similar mechanisms.

---

## 7. Health Checks

Use the health endpoints to verify that the service is alive:

- Nginx:  
  `GET https://api.your-domain.com/healthz`

- Django:  
  `GET https://api.your-domain.com/health/`

These can be wired to:

- AWS ALB / NLB health checks
- External uptime monitoring services
- Simple scripts or dashboards

---

## 8. Troubleshooting Checklist

### 8.1 “502 Bad Gateway” / Nginx error

- Check `web` logs:
  ```bash
  docker compose logs web -f
  ```
- Check that Gunicorn is running and listening on the expected port (usually 8000 inside the container).
- Ensure migrations have run successfully; sometimes startup fails due to DB errors.

### 8.2 Video processing never finishes

- Check `rq_worker` logs for tracebacks.
- Confirm FFmpeg is installed and in `PATH` inside the container.
- Verify S3 credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, bucket name).
- Check that `USE_S3_MEDIA` matches your expectation (True/False).

### 8.3 Database connection issues

- Test connectivity from inside the `web` container:

  ```bash
  docker compose exec web ping your-rds-endpoint.amazonaws.com
  ```

- Ensure RDS security group allows connections from the EC2 security group on port 5432.
- Verify `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `.env`.
- If SSL is required, confirm that `DB_SSL_ROOTCERT` points to the mounted CA bundle.

### 8.4 CORS / CSRF problems

- Double‑check:

  ```env
  ALLOWED_HOSTS=...
  CORS_ALLOWED_ORIGINS=...
  CSRF_TRUSTED_ORIGINS=...
  BACKEND_ORIGIN=...
  ```

- All must reflect the **real** HTTPS URLs of your frontend and backend.

### 8.5 Cookies not stored

- Ensure you use `withCredentials: true` in frontend HTTP calls.
- In dev, `JWT_COOKIE_SECURE=False` if you are not on HTTPS.
- In production, always use HTTPS (Secure cookies).

---

## 9. Backups & Disaster Recovery

- **Database (RDS)**  
  - Enable automated backups.
  - Optionally create manual snapshots before major changes.

- **Media (S3)**  
  - Enable versioning and, optionally, replication or lifecycle rules.
  - Consider a separate backup bucket or cross‑region replication for critical data.

- **Configuration**  
  - Keep `docker-compose.yml`, `nginx.conf`, and `.env` copies in a secure password manager or vault.
  - Use Git for code and configuration templates.

---

## 10. Performance Tips

- Use a compute‑optimized instance (e.g. `c6a.large`) if FFmpeg is slow.
- Increase `worker_processes` and `worker_connections` in Nginx for high concurrency.
- Adjust Gunicorn workers based on CPU count (e.g. `workers = 2 * cores + 1`).
- Offload static files to a CDN if needed (S3 + CloudFront).

With these practices, you should be able to operate the Videoflix backend reliably in both testing and production environments.
