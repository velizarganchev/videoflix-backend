# 05 – Deployment Guide (Docker)

This guide focuses on everyday Docker commands and a typical workflow for updating Videoflix Backend in production.

---

## 1. First Deployment

1. Provision an EC2 instance and install Docker + docker-compose-plugin.  
2. Clone or copy the repository to `/srv/videoflix-backend` (or similar).  
3. Create `.env` from `.env.example.prod` and fill in all required values.  
4. Run:

   ```bash
   docker compose pull web rq_worker redis nginx certbot_bootstrap
   docker compose up -d --build
   ```

5. Obtain certificates (once):

   ```bash
   docker compose run --rm certbot_bootstrap
   docker compose restart nginx
   ```

---

## 2. Updating the Application

### 2.1 Build or Pull New Image

Either build on the server:

```bash
docker compose build web rq_worker
```

or push new images from CI to a registry (GCR/ECR/Docker Hub) and then pull them on the server:

```bash
docker compose pull web rq_worker
```

### 2.2 Apply Migrations and Restart

A simple approach is:

```bash
docker compose run --rm web python manage.py migrate
docker compose up -d --force-recreate web rq_worker
```

This ensures the DB schema is up to date and both the app and worker use the new code.

---

## 3. Logs and Debugging

```bash
docker compose logs -f web
docker compose logs -f rq_worker
docker compose logs -f nginx
```

For FFmpeg or RQ issues, check:

- `rq_worker` logs  
- Django‑RQ dashboard at `/django-rq/` for failed jobs

---

## 4. Maintenance Tasks

- **Create superuser (production):**

  ```bash
  docker compose run --rm web python manage.py createsuperuser
  ```

- **Check health endpoints:**

  - App health: `https://api.your-domain.com/health/`  
  - Nginx health: `https://api.your-domain.com/healthz`

- **Backup DB:** use RDS snapshots or `pg_dump` against the RDS endpoint.

---

## 5. Zero‑Downtime Considerations (Optional)

For more advanced setups you can:

- Use rolling updates with two EC2 instances behind a load balancer.  
- Run multiple `web` containers (scale out Gunicorn workers).  
- Move Redis into a managed service (ElastiCache) for higher availability.

These optimizations are not required for the course project but are natural next steps for a production SaaS.
