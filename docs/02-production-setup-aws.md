# Production Setup on AWS (EC2 + RDS + S3)

This document describes how to deploy the Videoflix backend in a **production**‑like environment on AWS, using:

- EC2 (for Docker / Nginx / Gunicorn / RQ / Redis)
- RDS (PostgreSQL)
- S3 (video + thumbnails)
- Let’s Encrypt (HTTPS via Certbot + Nginx)

The guide assumes basic familiarity with AWS and Linux servers.

---

## 1. High‑Level Architecture

```text
[ User Browser ]
        |
        v   HTTPS (443)
[ Nginx on EC2 ]
        |
        v   proxy_pass
[ Gunicorn (Django) container ]  <-->  [ Redis container ]  <-->  [ RQ Worker container ]
        |                                     |
        | ORM                                 | Background jobs
        v                                     v
[ PostgreSQL (RDS) ]                    [ AWS S3 (videos & thumbnails) ]
```

All services except the database and S3 run on a single EC2 instance using **docker compose**.

---

## 2. AWS Resources

### 2.1 EC2 Instance

- OS: Ubuntu LTS (22.04+)
- Instance type (examples):
  - For demo / light usage: `t3.small`
  - For smoother FFmpeg transcoding: `c6a.large` (or similar compute‑optimized)
- Storage: e.g. 30–50 GB gp3 (depending on local media retention)
- Security Group:
  - Allow SSH (22) from your IP
  - Allow HTTP (80) from `0.0.0.0/0`
  - Allow HTTPS (443) from `0.0.0.0/0`

### 2.2 RDS (PostgreSQL)

- Engine: PostgreSQL 14+
- Multi‑AZ: optional for demo, recommended for real production
- Allocate storage according to expected usage (20–50 GB is fine to start)
- Security Group:
  - Allow inbound from EC2 security group on port **5432**
- Make sure to **note**:
  - DB name
  - DB user
  - DB password
  - DB endpoint host
- SSL: RDS provides its own CA bundle; we mount and use it in the container.

### 2.3 S3 Bucket

- Create a bucket for media files, e.g. `videoflix-media-prod`
- Region: e.g. `eu-central-1`
- By default, we use **private objects** + **presigned URLs**. No public ACL is required.
- Keep bucket versioning & lifecycle rules as desired.

### 2.4 IAM Credentials / Role

You can either:

- Use an **IAM user** with programmatic access and store its key/secret in `.env`, or
- Attach an **IAM role** to the EC2 instance and use role‑based access.

Minimal S3 permissions (policy snippet):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

Replace `your-bucket-name` with your actual bucket.

---

## 3. Preparing the EC2 Instance

SSH into the EC2 instance, update packages and install Docker.

### 3.1 Install Docker & Docker Compose

```bash
# update packages
sudo apt update && sudo apt upgrade -y

# install docker
sudo apt install -y docker.io docker-compose-plugin

# enable & start docker
sudo systemctl enable docker
sudo systemctl start docker

# add current user to docker group (optional)
sudo usermod -aG docker $USER
# then log out and back in
```

### 3.2 Clone the Repository

```bash
git clone https://github.com/velizarganchev/videoflix-backend.git
cd videoflix-backend
```

If you host your images on Docker Hub or another registry, you might not need to rebuild on the server; you can simply `docker compose pull`.

---

## 4. Environment Configuration (.env for PROD)

Copy the provided production example and edit it:

```bash
cp .env.example.prod .env
nano .env
```

A typical `.env` for production (simplified) looks like:

```env
# CORE / SECURITY (PROD)
DEBUG=False
SECRET_KEY=your-production-secret-key
BACKEND_ORIGIN=https://api.your-domain.com

# HOSTS & CORS (PROD)
ALLOWED_HOSTS=api.your-domain.com,your-frontend-domain.com
CSRF_TRUSTED_ORIGINS=https://api.your-domain.com,https://your-frontend-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
CORS_ALLOW_CREDENTIALS=True

# FRONTEND URLs (PROD)
FRONTEND_URL=https://your-frontend-domain.com/login
FRONTEND_CONFIRM_URL=https://your-frontend-domain.com/confirm
RESET_PASSWORD_URL=https://your-frontend-domain.com/reset-password

# COOKIES (PROD)
JWT_ACCESS_COOKIE_NAME=vf_access
JWT_REFRESH_COOKIE_NAME=vf_refresh
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None

CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True

# EMAIL (PROD)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# DATABASE (PROD)
DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432
DB_SSL_REQUIRE=True
DB_SSL_ROOTCERT=/app/rds-combined-ca-bundle.pem

# REDIS / RQ (PROD)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_LOCATION=redis://redis:6379/0

# STORAGE (AWS S3)
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=eu-central-1
AWS_S3_QUERYSTRING_AUTH=True

# DJANGO SUPERUSER (OPTIONAL)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

A line‑by‑line explanation is provided in `docs/03-env-files.md`.

---

## 5. Starting the Stack in Production Mode

The provided `docker-compose.yml` is prepared for production use with Nginx and Certbot.

### 5.1 First start (HTTP only)

Before you have TLS certificates, you can start everything via:

```bash
docker compose up -d --build
```

What happens:

- `web` container:
  - runs Django checks
  - applies migrations
  - collects static files
  - starts Gunicorn on port 8000
- `redis` container: Redis server
- `rq_worker` container: RQ worker process
- `nginx` container: reverse proxy
  - serves `/static/` from `/app/staticfiles/`
  - proxies `/` to `web:8000`
  - exposes ports `80` and `443` (443 will fail until certs are present)

### 5.2 Obtaining a Let’s Encrypt Certificate

Make sure your domain (e.g. `api.your-domain.com`) points to the EC2 public IP.

Run the bootstrap Certbot container:

```bash
docker compose run --rm certbot_bootstrap
```

It will:

- Request certificates from Let’s Encrypt
- Store them in a shared volume (usually under `/etc/letsencrypt` in the container)

Then restart nginx:

```bash
docker compose restart nginx
```

Now Nginx listens on **443** with a real TLS certificate and redirects HTTP → HTTPS.

### 5.3 Checking Health

- Nginx health: `https://api.your-domain.com/healthz`
- Django health: `https://api.your-domain.com/health/`

---

## 6. Updating the Application

When you push a new version (via Git or Docker image), you can update with:

```bash
git pull origin main      # or 'docker compose pull web rq_worker'
docker compose up -d --force-recreate
```

The `web` container will again:

- run migrations
- collect static files
- start Gunicorn

Workers will reconnect to Redis and continue processing jobs.

---

## 7. Logs & Monitoring

### 7.1 Web (Django / Gunicorn)

```bash
docker compose logs web -f
```

### 7.2 Worker (FFmpeg / RQ jobs)

```bash
docker compose logs rq_worker -f
```

You’ll see:

- when jobs are enqueued (from signals)
- FFmpeg conversions starting/completing
- thumbnail generation
- any errors or tracebacks

### 7.3 Redis

```bash
docker compose logs redis -f
```

### 7.4 Nginx

```bash
docker compose logs nginx -f
```

---

## 8. S3 Presigned URLs vs Public Objects

By default, Videoflix uses S3 with **presigned URLs** for playback:

```env
USE_S3_MEDIA=True
AWS_S3_QUERYSTRING_AUTH=True
```

The `/content/video-url/<id>/` endpoint signs a URL for the requested quality and returns:

```json
{ "url": "https://s3.amazonaws.com/your-bucket/path/to/file.mp4?X-Amz-Expires=..." }
```

If you prefer fully public files (no signing, no expiry), you can:

1. Set `AWS_S3_QUERYSTRING_AUTH=False`
2. Configure your bucket policy to allow public `GET`
3. Adjust any CDN / caching in front of S3 if desired

However, for **most production setups**, using **private objects + presigned URLs** is recommended, and that is what this backend is implemented and tested with.

---

## 9. Scaling Considerations

- Use a compute‑optimized instance type (e.g. `c6a.large`) if FFmpeg jobs are slow.
- If traffic grows:
  - Move Redis to a separate instance / ElastiCache
  - Use multiple `rq_worker` containers
  - Consider a load balancer in front of multiple EC2 instances running the stack

---

## 10. Backups

- RDS can be configured with automated backups + snapshots.
- S3 is durable by design, but you can enable versioning and lifecycle rules.
- For configuration, you should keep:
  - Git repository
  - `.env` (securely, not in Git)
  - Any additional scripts or infra code
