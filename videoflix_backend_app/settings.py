"""
Django settings for Videoflix backend.

- Auto ENV selection via ENV_FILE (.env.dev / .env.prod)
- Auto DB selection → DEBUG=True → SQLite, DEBUG=False → PostgreSQL
- SimpleJWT (cookie-based auth)
- RQ worker + Redis config with auto-switch (localhost ↔ redis)
- CORS/CSRF configured for cookie auth
"""

import os
from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env_file = os.getenv("ENV_FILE", ".env.dev")

if not os.path.isabs(env_file):
    env_file = os.path.join(BASE_DIR, env_file)

if os.path.exists(env_file):
    environ.Env.read_env(env_file)

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env.str("SECRET_KEY", default="dev-secret")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"]
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "django_rq",
    "import_export",
    "rest_framework_simplejwt.token_blacklist",

    "users_app",
    "content_app",
]

if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")


AUTH_USER_MODEL = "users_app.UserProfile"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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

DB_SSL_REQUIRE = env.bool("DB_SSL_REQUIRE", default=False)
DB_SSL_ROOTCERT = env.str("DB_SSL_ROOTCERT", default="")

if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    options = {}
    if DB_SSL_REQUIRE:
        options["sslmode"] = "require"
        if DB_SSL_ROOTCERT:
            options["sslrootcert"] = DB_SSL_ROOTCERT

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST"),
            "PORT": env.int("DB_PORT", default=5432),
            "OPTIONS": options,
        }
    }


REDIS_URL = env.str("REDIS_URL", default="")

if REDIS_URL:
    RQ_QUEUES = {"default": {"URL": REDIS_URL, "DEFAULT_TIMEOUT": 360}}
else:
    RQ_QUEUES = {
        "default": {
            "HOST": env("REDIS_HOST", default=("localhost" if DEBUG else "redis")),
            "PORT": env.int("REDIS_PORT", default=6379),
            "DB": env.int("REDIS_DB", default=0),
            "DEFAULT_TIMEOUT": 360,
        }
    }


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env(
            "REDIS_LOCATION",
            default=(
                "redis://localhost:6379/0" if DEBUG else "redis://redis:6379/0"),
        ),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "videoflix",
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "uploads")

# -----------------------------
# Storage: S3 vs Local
# -----------------------------
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)

# Backend origin for building absolute URLs (only in DEBUG + local media)
if DEBUG and not USE_S3_MEDIA:
    BACKEND_ORIGIN = env("BACKEND_ORIGIN", default="http://127.0.0.1:8000")

# -----------------------------
# Local transcoding settings (FFmpeg)
# -----------------------------
TRANSCODE_LOCALLY = env.bool("TRANSCODE_LOCALLY", default=True)

# Path to FFmpeg binary if not in PATH
FFMPEG_BIN = env.str("FFMPEG_BIN", default="ffmpeg")

if USE_S3_MEDIA:
    INSTALLED_APPS.append("storages")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-central-1")

    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_QUERYSTRING_AUTH = env.bool(
        "AWS_S3_QUERYSTRING_AUTH", default=False)

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "users_app.api.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
    },
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200"]
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200"]
)

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

FRONTEND_LOGIN_URL = env("FRONTEND_URL", default="http://localhost:4200/login")
FRONTEND_CONFIRM_URL = env("FRONTEND_CONFIRM_URL",
                           default="http://localhost:4200/confirm")
FRONTEND_RESET_PASSWORD_URL = env(
    "RESET_PASSWORD_URL", default="http://localhost:4200/reset-password")

JWT_ACCESS_COOKIE_NAME = env("JWT_ACCESS_COOKIE_NAME", default="vf_access")
JWT_REFRESH_COOKIE_NAME = env("JWT_REFRESH_COOKIE_NAME", default="vf_refresh")

JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", default="None")
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=not DEBUG)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

if DEBUG:
    # При теб това трябва да е True, за да вървят cookie-тата през Chrome.
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
else:
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
