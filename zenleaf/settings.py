"""Django settings for the ZenLeaf Tea Lounge demo.

Every value that differs between machines, and every secret, is read from environment variables.
For local use they live in a `.env` file next to manage.py (created by `python bootstrap.py`,
never committed). See `.env.example` for the full list.
"""
import secrets
import sys
import warnings
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .env import env_bool, env_int, env_list, env_str, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent
load_env_file(BASE_DIR / ".env")

RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"

SECRET_KEY = env_str("DJANGO_SECRET_KEY")
if SECRET_KEY.startswith("change-me"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY still has the placeholder value from .env.example. Run `python bootstrap.py`, "
        "or set it to a long random value."
    )
if not SECRET_KEY:
    if RUNNING_TESTS:
        SECRET_KEY = secrets.token_urlsafe(50)  # throwaway key, only for the test run
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. Run `python bootstrap.py`, or copy .env.example to .env "
            "and set DJANGO_SECRET_KEY to a long random value."
        )

DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "lounge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "zenleaf.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "zenleaf.urls"
WSGI_APPLICATION = "zenleaf.wsgi.application"

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
                "lounge.context_processors.site",
                "lounge.context_processors.staff",
            ],
        },
    },
]

# --- Database: one SQLite file on the server's disk -------------------------------------------
# Relative paths are resolved from the project folder. The folder is created if it is missing.
_db_path = Path(env_str("ZENLEAF_DB_PATH", "data/zenleaf.sqlite3"))
if not _db_path.is_absolute():
    _db_path = BASE_DIR / _db_path
_db_path.parent.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = _db_path

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_PATH,
        "OPTIONS": {
            # WAL lets the site keep reading while a write is in progress; busy_timeout makes a
            # second writer wait briefly instead of failing straight away.
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentication (staff area) ---------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
if RUNNING_TESTS:
    # Tests create throwaway accounts; a fast hasher keeps the suite quick. Never used when serving the site.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
LOGIN_URL = "staff:login"
LOGIN_REDIRECT_URL = "staff:dashboard"
LOGIN_MAX_ATTEMPTS = env_int("ZENLEAF_LOGIN_MAX_ATTEMPTS", 5)
LOGIN_LOCKOUT_MINUTES = env_int("ZENLEAF_LOGIN_LOCKOUT_MINUTES", 15)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Turn these on only when the site is served over HTTPS (a real deployment).
_https = env_bool("DJANGO_HTTPS", False)
SESSION_COOKIE_SECURE = _https
CSRF_COOKIE_SECURE = _https
SECURE_SSL_REDIRECT = _https
SECURE_HSTS_SECONDS = 3600 if _https else 0
if env_bool("DJANGO_BEHIND_PROXY", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "zenleaf"}}

# --- Locale -----------------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env_str("ZENLEAF_TIME_ZONE", "Asia/Dhaka")
USE_I18N = True
USE_TZ = True

# --- Static files (served by WhiteNoise, also when DEBUG is off) -------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # filled by `collectstatic` for a deployment
WHITENOISE_USE_FINDERS = True          # serve straight from the app folders; collectstatic is optional locally
WHITENOISE_AUTOREFRESH = DEBUG
# Locally STATIC_ROOT usually doesn't exist yet, which is fine because of WHITENOISE_USE_FINDERS.
# (WhiteNoise warns about the missing folder; that message is silenced here.)
warnings.filterwarnings("ignore", message="No directory at: ", category=UserWarning)

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    # Expected 4xx responses in the test suite would otherwise fill the output.
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR" if RUNNING_TESTS else "WARNING"}},
}

# --- ZenLeaf demo settings ----------------------------------------------------------------------
ZENLEAF = {
    "CURRENCY_SYMBOL": env_str("ZENLEAF_CURRENCY_SYMBOL", "৳"),
    # Reservation requests: the hours and limits the demo accepts. They are settings, not promises.
    "OPENING_TIME": env_str("ZENLEAF_OPENING_TIME", "10:00"),
    "LAST_SEATING": env_str("ZENLEAF_LAST_SEATING", "20:00"),
    "SLOT_MINUTES": env_int("ZENLEAF_SLOT_MINUTES", 30),
    "MAX_PARTY_SIZE": env_int("ZENLEAF_MAX_PARTY_SIZE", 8),
    "BOOKING_DAYS_AHEAD": env_int("ZENLEAF_BOOKING_DAYS_AHEAD", 60),
    "MIN_NOTICE_MINUTES": env_int("ZENLEAF_MIN_NOTICE_MINUTES", 60),
    "MAX_ITEM_QUANTITY": 20,
    "BACKUP_DIR": env_str("ZENLEAF_BACKUP_DIR", "backups"),
}
