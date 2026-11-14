import sys
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()) + ["backend"]
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# Public address of the website, used in links inside emails
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:8080").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "users",
    "uploads",
    "api",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Everything backend-related lives under /api/, including static files
STATIC_URL = "/api/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email: real SMTP when EMAIL_HOST is set (Mailpit in dev), otherwise printed to the logs
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="web_foundation <noreply@localhost>")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {"auth": "20/min", "upload": "100/hour"},
    # Exactly one proxy (nginx) sits in front: use the client IP it records
    "NUM_PROXIES": 1,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# Uploads
MEDIA_URL = "/api/media/"
MEDIA_ROOT = BASE_DIR / "media"
UPLOAD_MAX_BYTES = 10 * 1024 * 1024
IMAGE_MAX_PIXELS = 40_000_000
IMAGE_MAX_SIDE = 2560
THUMBNAIL_SIDE = 400
MEDIA_SIGNED_URL_SECONDS = config("MEDIA_SIGNED_URL_SECONDS", default=300, cast=int)

# Video
VIDEO_MAX_BYTES = 100 * 1024 * 1024
MEDIA_SIGNED_VIDEO_URL_SECONDS = 3600

# Redis, cache and Celery. Tests use an in-memory cache and run tasks immediately (no Redis needed).
TESTING = sys.argv[1:2] == ["test"]
REDIS_URL = config("REDIS_URL", default="redis://redis:6379")

if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"{REDIS_URL}/1",
        }
    }

CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Security. One switch for the day the site is served over HTTPS (HTTPS_ENABLED in .env.prod).
# Redirecting HTTP to HTTPS is done by nginx, not by Django.
HTTPS_ENABLED = config("HTTPS_ENABLED", default=False, cast=bool)
if HTTPS_ENABLED:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Start low: browsers remember HSTS. Raise to a year once HTTPS has worked for a while.
    SECURE_HSTS_SECONDS = 3600

# Daily cleanup of expired refresh tokens (runs inside the worker, see "-B" in the compose files)
CELERY_BEAT_SCHEDULE = {
    "flush-expired-tokens": {
        "task": "users.tasks.flush_expired_tokens",
        "schedule": 86400.0,
    },
}

CELERY_BEAT_SCHEDULE["requeue-stuck-videos"] = {
    "task": "uploads.tasks.requeue_stuck_videos",
    "schedule": 600.0,
}
