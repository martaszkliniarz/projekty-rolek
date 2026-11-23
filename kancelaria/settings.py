"""
Ustawienia aplikacji. Wszystko, co różni komputer od serwera w chmurze,
czytane jest ze zmiennych środowiskowych (plik .env — patrz .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _wczytaj_env(plik: Path):
    """Prosty odczyt pliku .env (bez dodatkowych bibliotek)."""
    if plik.exists():
        for linia in plik.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if linia and not linia.startswith("#") and "=" in linia:
                k, v = linia.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_wczytaj_env(BASE_DIR / ".env")


def env_bool(nazwa, domyslnie=False):
    return os.environ.get(nazwa, str(domyslnie)).lower() in ("1", "true", "tak", "yes")


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = os.environ.get("SECRET_KEY") or ("dev-tylko-lokalnie-zmien-mnie" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Ustaw SECRET_KEY w pliku .env (patrz .env.example).")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sprawy",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kancelaria.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "kancelaria.wsgi.application"

DANE_DIR = Path(os.environ.get("DANE_DIR", BASE_DIR / "dane"))
DANE_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DANE_DIR / "kancelaria.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/pliki/"
MEDIA_ROOT = DANE_DIR / "pliki"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "pulpit"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_AGE = 60 * 60 * 10  # 10 godzin

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("HTTPS", True)
    CSRF_COOKIE_SECURE = env_bool("HTTPS", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Kalendarz Google (subskrypcja .ics) ---
KALENDARZ_TOKEN = os.environ.get("KALENDARZ_TOKEN", "")
KALENDARZ_ANONIMOWY = env_bool("KALENDARZ_ANONIMOWY", True)
