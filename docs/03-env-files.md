# 03 – Environment Files (.env)

Videoflix Backend relies heavily on environment variables. This document explains the most important ones and how the
two example files are intended to be used.

- `.env.example.dev`  – local development
- `.env.example.prod` – production on EC2 + RDS + S3

---

## 1. Core & Security

```dotenv
DEBUG=...
SECRET_KEY=...
BACKEND_ORIGIN=...
ALLOWED_HOSTS=...
```

- `DEBUG` – `True` only for local development.
- `SECRET_KEY` – long random string; keep it secret.
- `BACKEND_ORIGIN` – base URL of the backend (used in some links).
- `ALLOWED_HOSTS` – comma‑separated hostnames that may serve the site.

---

## 2. CORS & CSRF

```dotenv
CORS_ALLOWED_ORIGINS=...
CSRF_TRUSTED_ORIGINS=...
```

These must match your frontend URLs. Example dev values:

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:4200
CSRF_TRUSTED_ORIGINS=http://localhost:4200
```

For production, use your real domain(s).

---

## 3. Frontend URLs

```dotenv
FRONTEND_URL=...
FRONTEND_CONFIRM_URL=...
RESET_PASSWORD_URL=...
FRONTEND_LOGIN_URL=...
FRONTEND_RESET_PASSWORD_URL=...
```

Used to build links in email templates (confirmation, login redirect, password reset).

---

## 4. Cookies & JWT

```dotenv
JWT_ACCESS_COOKIE_NAME=vf_access
JWT_REFRESH_COOKIE_NAME=vf_refresh
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
```

- In dev, `*_SECURE` flags can be `False` so cookies work over `http://`.  
- In production, they should be `True` and `SameSite=None` for cross‑site SPA usage.

---

## 5. Database

```dotenv
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432
DB_SSL_REQUIRE=True
DB_SSL_ROOTCERT=/app/rds-combined-ca-bundle.pem
```

For local dev you can replace these with SQLite or a local Postgres instance. In production you typically point to RDS and
keep SSL enabled.

---

## 6. Redis / RQ

```dotenv
REDIS_HOST=...
REDIS_PORT=6379
REDIS_DB=0
REDIS_LOCATION=redis://redis:6379/0   # in Docker
```

- In dev: `redis://localhost:6379/0`  
- In Docker: `redis://redis:6379/0` (service name `redis`)

---

## 7. Storage (S3 or Local)

```dotenv
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_REGION_NAME=eu-central-1
AWS_S3_QUERYSTRING_AUTH=True
```

- `USE_S3_MEDIA=False` in dev → local uploads under `uploads/`.
- `USE_S3_MEDIA=True` in prod → videos go to S3.
- When `AWS_S3_QUERYSTRING_AUTH=True` the backend generates **presigned URLs** via `/content/video-url/<id>/`.

---

## 8. Email

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=...
```

Dev example:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

This prints emails to the console instead of sending them.

---

## 9. Django Superuser (Optional)

```dotenv
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

When present, the entrypoint script can auto‑create a superuser on startup (depending on your configuration).

