"""Dedicated production mail process on the operator's computer; no web server."""
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import BASE_DIR, env

env.read_env(BASE_DIR / ".env")
# base.py is imported before .env is read; reload the selectors used by notices.
BILLING_PROVIDER = env("BILLING_PROVIDER", default="mercadopago")
MERCADOPAGO_ENVIRONMENT = env("MERCADOPAGO_ENVIRONMENT", default="sandbox")
PAGBANK_ENVIRONMENT = env("PAGBANK_ENVIRONMENT", default="sandbox")
DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
IDENTITY_ENCRYPTION_KEY = env("IDENTITY_ENCRYPTION_KEY")
try:
    Fernet(IDENTITY_ENCRYPTION_KEY.encode())
except (ValueError, TypeError):
    raise ImproperlyConfigured("Use the production IDENTITY_ENCRYPTION_KEY.") from None
DATABASES = {"default": env.db("DATABASE_URL")}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("The mail worker requires the production PostgreSQL database.")
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"].setdefault("OPTIONS", {}).update(sslmode="require", connect_timeout=10)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
origin = env("IUSTUS_PUBLIC_ORIGIN", default="https://iustus.app").rstrip("/")
parsed = urlsplit(origin)
if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
    raise ImproperlyConfigured("Use the exact HTTPS origin of the production site.")
PORTAL_ORIGINS = {"client": origin, "team": origin}
IDENTITY_SHARED_PORTAL = True
EMAIL_PROVIDER = "smtp"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
if EMAIL_PORT not in (465, 587):
    raise ImproperlyConfigured("Use SMTP TLS on port 465 or 587.")
EMAIL_USE_TLS = EMAIL_PORT == 587
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_TIMEOUT = 20
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"Iustus <{EMAIL_HOST_USER}>")
if not all((EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, SECRET_KEY)):
    raise ImproperlyConfigured("Configure SMTP credentials and DJANGO_SECRET_KEY.")
BILLING_ENABLED = False
DOCUMENT_STORAGE_BACKEND = "disabled"
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"safe": {"()": "config.safe_logging.SafeExceptionFormatter"}},
    "handlers": {"safe": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "loggers": {"jobs.mail": {"handlers": ["safe"], "level": "ERROR", "propagate": False}},
}
