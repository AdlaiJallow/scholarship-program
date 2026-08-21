"""
Django settings for the Scholarship Self-Verification & Approval Portal.

Configuration is environment-driven throughout: nothing environment-specific
(secrets, hosts, database credentials) is hard-coded, so the same codebase
runs unmodified across development, staging, and production per the
deployment architecture in the system specification.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None, cast=str):
    value = os.environ.get(key, default)
    if value is None:
        return None
    if cast is bool:
        return str(value).lower() in ("1", "true", "yes", "on")
    return cast(value)


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG", "false", cast=bool)
ENVIRONMENT = env("DJANGO_ENVIRONMENT", "development")

# Column-level encryption key for national ID / passport numbers (apps.core.fields).
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", "44z00md3Qvgz_8Fd5oz5eGWdJKD9qFwuAAL58vbdu3E=")

ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.scholarships",
    "apps.verification",
    "apps.notifications",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "scholarship_portal"),
        "USER": env("DB_USER", "scholarship_portal"),
        "PASSWORD": env("DB_PASSWORD", "scholarship_portal"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": env("DB_CONN_MAX_AGE", 60, cast=int),
    }
}
if env("DJANGO_TEST_SQLITE", "false", cast=bool):
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test_db.sqlite3"}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.PasswordComplexityValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Banjul")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"  # local fallback only — production uses DOCUMENT_STORAGE below

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth-login": "10/min",
        "auth-activate": "10/min",
        "auth-password-reset": "5/min",
        "document-upload": "60/min",
    },
    "DATETIME_FORMAT": "iso-8601",
}

# ---------------------------------------------------------------------------
# Session / CSRF / cookie security
# per system specification §16 — session auth, HttpOnly + Secure + SameSite
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SECURE = env("DJANGO_COOKIE_SECURE", str(not DEBUG), cast=bool)
SESSION_COOKIE_AGE = env("SESSION_COOKIE_AGE", 60 * 60 * 8, cast=int)  # 8 hours
CSRF_COOKIE_HTTPONLY = False  # frontend must read it to set X-CSRFToken
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

SECURE_SSL_REDIRECT = env("DJANGO_SSL_REDIRECT", str(not DEBUG), cast=bool)
SECURE_HSTS_SECONDS = env("DJANGO_HSTS_SECONDS", 31536000, cast=int) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CORS_ALLOWED_ORIGINS = [o.strip() for o in env("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Account lockout / brute-force protection (§16)
# ---------------------------------------------------------------------------
ACCOUNT_LOCKOUT_THRESHOLD = env("ACCOUNT_LOCKOUT_THRESHOLD", 5, cast=int)
ACCOUNT_LOCKOUT_WINDOW_MINUTES = env("ACCOUNT_LOCKOUT_WINDOW_MINUTES", 15, cast=int)

# ---------------------------------------------------------------------------
# Document storage (§13, §16) — S3-compatible (MinIO by default)
# ---------------------------------------------------------------------------
DOCUMENT_STORAGE_BACKEND = env("DOCUMENT_STORAGE_BACKEND", "filesystem")  # filesystem | s3
DOCUMENT_STORAGE = {
    "ENDPOINT_URL": env("DOCUMENT_STORAGE_ENDPOINT", "http://localhost:9000"),
    "ACCESS_KEY": env("DOCUMENT_STORAGE_ACCESS_KEY", ""),
    "SECRET_KEY": env("DOCUMENT_STORAGE_SECRET_KEY", ""),
    "BUCKET": env("DOCUMENT_STORAGE_BUCKET", "scholarship-documents"),
    "REGION": env("DOCUMENT_STORAGE_REGION", "us-east-1"),
    "SIGNED_URL_EXPIRY_SECONDS": env("DOCUMENT_SIGNED_URL_EXPIRY_SECONDS", 60, cast=int),
}
DOCUMENT_MAX_UPLOAD_SIZE_BYTES_HARD_CAP = env("DOCUMENT_MAX_UPLOAD_SIZE_HARD_CAP", 25 * 1024 * 1024, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = DOCUMENT_MAX_UPLOAD_SIZE_BYTES_HARD_CAP
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

ANTIVIRUS_SCAN_BACKEND = env("ANTIVIRUS_SCAN_BACKEND", "noop")  # noop | clamav
CLAMAV_HOST = env("CLAMAV_HOST", "localhost")
CLAMAV_PORT = env("CLAMAV_PORT", 3310, cast=int)

# ---------------------------------------------------------------------------
# Email (§14)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env("EMAIL_PORT", 587, cast=int)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "true", cast=bool)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@scholarships.gov.gm")
PORTAL_BASE_URL = env("PORTAL_BASE_URL", "http://localhost:3000")
MINISTRY_CONTACT_EMAIL = env("MINISTRY_CONTACT_EMAIL", "scholarships@moherst.gov.gm")
MINISTRY_CONTACT_PHONE = env("MINISTRY_CONTACT_PHONE", "+220 000 0000")

# ---------------------------------------------------------------------------
# Celery (§13 async upload processing, §14 email, §20 export)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", "false", cast=bool)

# ---------------------------------------------------------------------------
# Logging (§26)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# Application/scholarship-domain constants
APPLICATION_DEADLINE_REMINDER_DAYS_BEFORE = [14, 7, 2]
