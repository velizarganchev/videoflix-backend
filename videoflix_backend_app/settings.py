"""
Django settings for videoflix_backend_app.

This configuration centralizes:
- Environment loading (django-environ)
- Core security and debugging flags
- Installed apps & middleware
- URLs, templates, WSGI
- Redis / RQ / caching
- Database (Postgres; optional SQLite for local dev)
- Auth & password validation
- i18n / timezone
- Static & media (local; optional AWS S3)
- DRF, CORS/CSRF, Email
- Production hardening

Keep secrets and env-specific values in .env or container env vars.
"""

from pathlib import Path
import os
import environ

# ----------------------------------------------------------------------
# 1. Base & Environment
# ----------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    # prefer a project-level .env during local dev
    environ.Env.read_env(env_file)

# ----------------------------------------------------------------------
# 2. Core / Security
# ----------------------------------------------------------------------
SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)  # never True in production

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "api.videoflix-velizar-ganchev-backend.com",
        "videoflix.velizar-ganchev.com",
    ],
)

# If behind a proxy/load balancer, allow HTTPS detection
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ----------------------------------------------------------------------
# 3. Applications
# ----------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_rq",
    "import_export",

    "users_app",
    "content_app",
]

if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

AUTH_USER_MODEL = "users_app.UserProfile"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------------------------------------------------
# 4. Middleware
# ----------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "middleware.range_requests.RangeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1"]

# ----------------------------------------------------------------------
# 5. URLs / Templates / WSGI
# ----------------------------------------------------------------------
ROOT_URLCONF = "videoflix_backend_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "videoflix_backend_app.wsgi.application"

# ----------------------------------------------------------------------
# 6. Redis / RQ / Caching
# ----------------------------------------------------------------------
RQ_QUEUES = {
    "default": {
        "HOST": env("REDIS_HOST", default="redis"),
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 360,
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_LOCATION", default="redis://redis:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "videoflix",
    }
}

# ----------------------------------------------------------------------
# 7. Database
# ----------------------------------------------------------------------
DB_SSL_REQUIRE = env.bool("DB_SSL_REQUIRE", default=False)
DB_SSL_ROOTCERT = env.str("DB_SSL_ROOTCERT", default="")

_db_options = {}
if DB_SSL_REQUIRE:
    _db_options["sslmode"] = "require"
    if DB_SSL_ROOTCERT:
        _db_options["sslrootcert"] = DB_SSL_ROOTCERT

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
        "OPTIONS": _db_options,
    }
}

if DEBUG and env.bool("USE_SQLITE_LOCAL", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ----------------------------------------------------------------------
# 8. Authentication & Password Validation
# ----------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------------------------------------------------
# 9. Localization (i18n / Time zone)
# ----------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# ----------------------------------------------------------------------
# 10. Static & Media
# ----------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "uploads")  # local; PROD can use S3

# ----------------------------------------------------------------------
# 11. REST Framework
# ----------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

CACHE_TTL = int(60 * 15)

# ----------------------------------------------------------------------
# 12. CORS / CSRF
# ----------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:4200",
        "https://videoflix.velizar-ganchev.com",
        "https://api.videoflix-velizar-ganchev-backend.com",
    ],
)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "https://videoflix.velizar-ganchev.com",
        "https://api.videoflix-velizar-ganchev-backend.com",
    ]
)

# ----------------------------------------------------------------------
# 13. Email
# ----------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env.str("EMAIL_HOST_USER")

FRONTEND_RESET_PASSWORD_URL = env.str("RESET_PASSWORD_URL")
FRONTEND_LOGIN_URL = env.str("FRONTEND_URL")
BACKEND_URL = env.str("URL")

# ----------------------------------------------------------------------
# 14. AWS S3 Media Storage
# ----------------------------------------------------------------------
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)

if USE_S3_MEDIA:
    INSTALLED_APPS.append("storages")
    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME", default="eu-central-1")
    AWS_S3_QUERYSTRING_AUTH = env.bool(
        "AWS_S3_QUERYSTRING_AUTH", default=False)

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "public, max-age=31536000, immutable"}

    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

# ----------------------------------------------------------------------
# 15. Production Hardening
# ----------------------------------------------------------------------
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ----------------------------------------------------------------------
# 16. Logging (basic)
# ----------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ----------------------------------------------------------------------
# 17. Testing Overrides
# ----------------------------------------------------------------------
if "PYTEST_CURRENT_TEST" in os.environ:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache"
        }
    }
# ----------------------------------------------------------------------

# End of settings.py — extend via environment variables or local_settings.py
