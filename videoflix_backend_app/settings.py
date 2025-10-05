from pathlib import Path
import os
import environ

# -----------------------------
# Base & env
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# -----------------------------
# Core / security
# -----------------------------
SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "api.videoflix-velizar-ganchev-backend.com",
        "videoflix.velizar-ganchev.com",
    ],
)

# зад reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------
# Apps
# -----------------------------
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

# debug toolbar само в DEBUG
if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

AUTH_USER_MODEL = "users_app.UserProfile"

# -----------------------------
# Middleware
# -----------------------------
MIDDLEWARE = [
    "middleware.range_requests.RangeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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

# -----------------------------
# URLconf / Templates / WSGI
# -----------------------------
ROOT_URLCONF = "videoflix_backend_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# -----------------------------
# RQ (Redis queues)
# -----------------------------
RQ_QUEUES = {
    "default": {
        "HOST": env("REDIS_HOST", default="redis"),
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 360,
    },
}

# -----------------------------
# Cache (Redis)
# -----------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "videoflix",
    }
}

# -----------------------------
# Database (PostgreSQL) с опционален SSL
# -----------------------------
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

# --- Local dev override: SQLite вместо Postgres ---
if DEBUG and env.bool("USE_SQLITE_LOCAL", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------
# Password validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------
# i18n / TZ
# -----------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# -----------------------------
# Static / Media
# -----------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "uploads")  # локално; на PROD ползваме S3

# -----------------------------
# DRF
# -----------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

CACHE_TTL = int(60 * 15)

# -----------------------------
# CORS / CSRF
# -----------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:4200",
        "https://videoflix-velizar-ganchev.com",
        "https://videoflix.velizar-ganchev.com",
        "https://api.videoflix-velizar-ganchev-backend.com",
    ],
)

CSRF_TRUSTED_ORIGINS = [
    "https://videoflix-velizar-ganchev.com",
    "https://videoflix.velizar-ganchev.com",
    "https://api.videoflix-velizar-ganchev-backend.com",
]

# -----------------------------
# Email
# -----------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env.str("EMAIL_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_PASSWORD")
DEFAULT_FROM_EMAIL = env.str("EMAIL_USER")

# -----------------------------
# App URLs (за имейли/фронтенд)
# -----------------------------
FRONTEND_RESET_PASSWORD_URL = env.str("RESET_PASSWORD_URL")
FRONTEND_LOGIN_URL = env.str("FRONTEND_URL")
BACKEND_URL = env.str("URL")

# -----------------------------
# S3 media (опционално)
# -----------------------------
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)

if USE_S3_MEDIA:
    INSTALLED_APPS.append("storages")
    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME", default="eu-central-1")
    AWS_S3_QUERYSTRING_AUTH = env.bool(
        "AWS_S3_QUERYSTRING_AUTH", default=False)

    # Media през S3
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # По-сигурни и кеширани обекти
    AWS_DEFAULT_ACL = None                 # не слагаме object ACL по подразбиране
    AWS_S3_FILE_OVERWRITE = False          # не презаписвай при едно и също име
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "public, max-age=31536000, immutable"
    }

    MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/"

# -----------------------------
# Production hardening
# -----------------------------
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
