"""
Django settings for core project.
Django 5.0.1
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# =============================================================================
# BASE CONFIG
# =============================================================================
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "*"]

# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# For development, you can use:
CORS_ALLOW_ALL_ORIGINS = True  # Not recommended for production




# =============================================================================
# APPLICATION DEFINITION
# =============================================================================
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",
    "django_celery_results",
    "rest_framework_simplejwt.token_blacklist",

    # Local apps
    "accounts",
    "youtube",
    "downloader",
]

AUTH_USER_MODEL = "accounts.User"

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "downloader.middleware.PerformanceMonitoringMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# CSRF Configuration
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_HTTPONLY = False  # JavaScript needs to read this
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False  # Set True in production with HTTPS
CSRF_USE_SESSIONS = False

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',  # Critical for CSRF
    'x-requested-with',
]



# =============================================================================
# URLS / WSGI
# =============================================================================
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

# =============================================================================
# TEMPLATES
# =============================================================================
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

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# =============================================================================
# DATABASE (PostgreSQL)
# =============================================================================
# ---------------------------------------------------------------------------
# DATABASE — SQLite by default (zero setup), PostgreSQL via env vars
# To use Postgres: set DB_ENGINE=django.db.backends.postgresql in your .env
# ---------------------------------------------------------------------------
_db_engine = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")

if _db_engine == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": _db_engine,
            "NAME": os.getenv("DB_NAME", "ydm_db"),
            "USER": os.getenv("DB_USER", "ydm_user"),
            "PASSWORD": os.getenv("DB_PASSWORD", "yourpassword"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA
# =============================================================================
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
   'DEFAULT_AUTHENTICATION_CLASSES': (
        'accounts.authenticate.CookieJWTAuthentication',  # Your custom class
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# =============================================================================
# SIMPLE JWT
# =============================================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_DOMAIN': None,
    'AUTH_COOKIE_SECURE': False,  # Set True in production with HTTPS
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}
# =============================================================================
# EMAIL CONFIG
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = f"YMD <{EMAIL_HOST_USER}>"

# =============================================================================
# GOOGLE / YOUTUBE
# =============================================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# =============================================================================
# REDIS / CACHE
# =============================================================================
REDIS_URL = os.getenv("REDIS_URL", "")

# Redis cache when REDIS_URL set, else fast in-memory cache (local dev)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }

# =============================================================================
# CELERY
# =============================================================================

# Broker settings (use your existing CELERY_BROKER_URL)
CELERY_BROKER_URL = REDIS_URL if REDIS_URL else "memory://"

# ✨ CRITICAL: Disable result backend completely
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True  # Global default

# ✨ Serialization optimization (JSON faster than pickle)
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_COMPRESSION = 'gzip'

# ✨ Ensure async execution
CELERY_TASK_ALWAYS_EAGER = not bool(REDIS_URL)  # Sync mode when no Redis

# ✨ Broker transport optimization
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # 1 hour for long downloads
    'fanout_prefix': True,
    'fanout_patterns': True,
}

# ✨ Connection pooling
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# ✨ Worker optimization
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task per worker
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart worker after 1000 tasks


# =============================================================================
# LOGGING (CRITICAL FOR DOWNLOADER)
# =============================================================================
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "downloader.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "downloader": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}

# =============================================================================
# CREATE REQUIRED DIRECTORIES
# =============================================================================
(BASE_DIR / "media" / "downloads").mkdir(parents=True, exist_ok=True)
