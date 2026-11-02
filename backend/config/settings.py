import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def _load_env() -> None:
    """Pembaca .env sederhana tanpa dependency tambahan."""
    for candidate in (BASE_DIR / ".env", PROJECT_ROOT / ".env"):
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-ytmp3-scrapper-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") not in ("0", "false", "False")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------- #
# PostgreSQL
# ---------------------------------------------------------------- #
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "ytmp3_scrapper"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {"connect_timeout": 5},
    }
}

LANGUAGE_CODE = "id-id"
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

# ---------------------------------------------------------------- #
# konfigurasi aplikasi
# ---------------------------------------------------------------- #
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR") or (PROJECT_ROOT / "downloads"))
PREFERENCES_FILE = PROJECT_ROOT / "data" / "preferences.json"
BIN_DIR = PROJECT_ROOT / "bin"
YTDLP_BIN = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
MAX_RESULTS = 5
MAX_CONCURRENT_JOBS = 2

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)
