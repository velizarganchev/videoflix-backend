# Environment Files (.env.example.dev and .env.example.prod)

The project provides **two** example environment files:

- `.env.example.dev`  → for **local development**
- `.env.example.prod` → for **production**

You should **never commit** your real `.env` file. Always copy one of the examples and edit it locally or on the server.

---

## 1. `.env.example.dev` (Development)

Used for:

- running `manage.py runserver`
- local Docker development
- typically **local media**, **console email backend**, and relaxed cookie settings

Example (simplified, grouped by concern):

```env
# ===========================
# CORE / SECURITY (DEV)
# ===========================
DEBUG=True
SECRET_KEY=dev-secret-key-change-me

BACKEND_ORIGIN=http://127.0.0.1:8000
ALLOWED_HOSTS=localhost,127.0.0.1

# ===========================
# FRONTEND (DEV)
# ===========================
CORS_ALLOWED_ORIGINS=http://localhost:4200
CSRF_TRUSTED_ORIGINS=http://localhost:4200

FRONTEND_URL=http://localhost:4200/login
FRONTEND_CONFIRM_URL=http://localhost:4200/confirm
RESET_PASSWORD_URL=http://localhost:4200/reset-password

# ===========================
# COOKIES (DEV)
# ===========================
JWT_COOKIE_SAMESITE=None
JWT_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False

# ===========================
# REDIS / RQ (DEV)
# ===========================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_LOCATION=redis://localhost:6379/0

# ===========================
# EMAIL (DEV)
# ===========================
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=dev@example.com

# ===========================
# MEDIA (DEV: LOCAL FILES)
# ===========================
USE_S3_MEDIA=False
MEDIA_URL=/media/
MEDIA_ROOT=/uploads/videos/
```

### 1.1 Field‑by‑field explanation (DEV)

- `DEBUG=True`  
  Enables Django debug mode (tracebacks in browser, extra logging). **Never** use in production.

- `SECRET_KEY`  
  Secret for cryptographic signing. In dev it can be static, but in prod it **must** be long, random and secret.

- `BACKEND_ORIGIN`  
  Base URL under which the backend is served. Used for some redirects / absolute URL building.

- `ALLOWED_HOSTS`  
  Hostnames Django will serve. For dev: `localhost`, `127.0.0.1`.

- `CORS_ALLOWED_ORIGINS`  
  Origins allowed for cross‑site requests (Angular dev server).

- `CSRF_TRUSTED_ORIGINS`  
  Origins trusted for CSRF cookies, usually the same as your frontend origin.

- `FRONTEND_URL`, `FRONTEND_CONFIRM_URL`, `RESET_PASSWORD_URL`  
  URLs used when building email links for login redirect, email confirmation and password reset in the frontend app.

- `JWT_COOKIE_*`, `CSRF_COOKIE_*`, `SESSION_COOKIE_*`  
  Cookie security flags. In dev we typically have **insecure** cookies (`Secure=False`) and `SameSite=None` for easier local testing.

- `REDIS_*`  
  Host/port for Redis. In dev, Redis often runs on `localhost:6379`.

- `EMAIL_BACKEND`  
  `django.core.mail.backends.console.EmailBackend` prints all emails to the console instead of sending them. Very convenient for development.

- `USE_S3_MEDIA=False`, `MEDIA_URL`, `MEDIA_ROOT`  
  Use local filesystem storage under `MEDIA_ROOT`. Files are served via Django’s media view in development.

---

## 2. `.env.example.prod` (Production)

Used for:

- EC2 + Docker deployment
- real database (RDS)
- S3 storage
- SMTP or another real email backend
- secure cookies

Example (simplified):

```env
# ===========================
# CORE / SECURITY (PROD)
# ===========================
DEBUG=False
SECRET_KEY=your-production-secret-key
BACKEND_ORIGIN=https://api.your-domain.com

# ===========================
# HOSTS & CORS (PROD)
# ===========================
ALLOWED_HOSTS=api.your-domain.com,your-frontend-domain.com
CSRF_TRUSTED_ORIGINS=https://api.your-domain.com,https://your-frontend-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
CORS_ALLOW_CREDENTIALS=True

# ===========================
# FRONTEND URLs (PROD)
# ===========================
FRONTEND_URL=https://your-frontend-domain.com/login
FRONTEND_CONFIRM_URL=https://your-frontend-domain.com/confirm
RESET_PASSWORD_URL=https://your-frontend-domain.com/reset-password

# ===========================
# COOKIES (PROD)
# ===========================
JWT_ACCESS_COOKIE_NAME=vf_access
JWT_REFRESH_COOKIE_NAME=vf_refresh
JWT_COOKIE_SECURE=True
JWT_COOKIE_SAMESITE=None

CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True

# ===========================
# EMAIL (PROD)
# ===========================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# ===========================
# DATABASE (PROD)
# ===========================
DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=your-db-host.aws.com
DB_PORT=5432
DB_SSL_REQUIRE=True
DB_SSL_ROOTCERT=/app/rds-combined-ca-bundle.pem

# ===========================
# REDIS / RQ (PROD)
# ===========================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_LOCATION=redis://redis:6379/0

# ===========================
# STORAGE (AWS S3)
# ===========================
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=eu-central-1
AWS_S3_QUERYSTRING_AUTH=True

# ===========================
# DJANGO SUPERUSER (OPTIONAL)
# ===========================
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

### 2.1 Field‑by‑field (differences vs DEV)

- `DEBUG=False`  
  Mandatory in production. Disables debug information in error pages.

- `BACKEND_ORIGIN=https://api.your-domain.com`  
  Must match your public backend URL.

- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`  
  Must match **real domains** used in production, including the frontend and backend hostnames.

- `JWT_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_SECURE=True`  
  Ensures cookies are **only** sent over HTTPS. Requires TLS termination at Nginx or a load balancer.

- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`  
  Real SMTP backend. You can swap this with any SMTP provider or backend you prefer.

- `DB_*`  
  RDS connection details. `DB_SSL_REQUIRE=True` and `DB_SSL_ROOTCERT` enable SSL connection to RDS using AWS’s CA bundle mounted into the container.

- `REDIS_HOST=redis`  
  When running inside Docker, Redis is reachable by its **service name** in the Compose network.

- `USE_S3_MEDIA=True`  
  Enables S3 storage for videos and thumbnails in production.

- `AWS_S3_QUERYSTRING_AUTH=True`  
  Forces **presigned URLs** (private objects) instead of public URLs.

- `DJANGO_SUPERUSER_*` (optional)  
  If set, the entrypoint can automatically create a superuser on the first run. You can also comment these out and manage users manually.

---

## 3. Patterns & Tips

- Always keep **two `.env` files**:
  - One for local dev (on your laptop)
  - One for each production / staging environment (on servers)
- Never commit real secrets to Git; `.env.example.*` should contain **safe placeholders only**.
- When something behaves differently between DEV and PROD, first compare:
  - `DEBUG`
  - `ALLOWED_HOSTS`
  - `CORS_*` and `CSRF_*`
  - `USE_S3_MEDIA` and `AWS_*`
  - Cookie security flags

---

## 4. Choosing Modes per Environment

Typical pattern:

- **DEV**  
  - Local media via `USE_S3_MEDIA=False`  
  - Console email backend  
  - Cookie security disabled  
  - Redis local or in Docker

- **STAGING / PROD**  
  - S3 media via `USE_S3_MEDIA=True`  
  - Real SMTP backend  
  - Secure cookies, TLS via Nginx  
  - Redis in Docker + RQ workers

Adjust the example files to your hosting and copy them to `.env` before starting the stack.
