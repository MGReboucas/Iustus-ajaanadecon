"""Desenvolvimento em loopback; não usar este módulo em produção."""
from .base import *  # noqa: F403
from .base import BASE_DIR, env

CASE_LOCAL_TEST_ACCESS = True
env.read_env(BASE_DIR / ".env")
BILLING_ENABLED = env.bool("BILLING_ENABLED", default=False)
PAGBANK_ENVIRONMENT = env("PAGBANK_ENVIRONMENT", default="sandbox")
PAGBANK_API_TOKEN = env("PAGBANK_API_TOKEN", default="")
PAGBANK_WEBHOOK_PUBLIC_KEY = env("PAGBANK_WEBHOOK_PUBLIC_KEY", default="")
SECRET_KEY = env("DJANGO_SECRET_KEY")
IDENTITY_ENCRYPTION_KEY = env("IDENTITY_ENCRYPTION_KEY")
IUSTUS_PROXY_SECRET = env("IUSTUS_PROXY_SECRET")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
DATABASES = {
    "default": env.db(
        default="postgresql://iustus:iustus-local-only@127.0.0.1:5432/iustus"
    )
}
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR.parent / ".local" / "mail"
PORTAL_ORIGINS = {"team": env("IUSTUS_PUBLIC_ORIGIN", default="http://localhost:3000").rstrip("/")}
IDENTITY_SHARED_PORTAL = True
PORTAL_ORIGINS["client"] = PORTAL_ORIGINS["team"]
IUSTUS_INITIAL_ADMIN_EMAIL = env("IUSTUS_INITIAL_ADMIN_EMAIL", default="")
# HTTP de desenvolvimento: não usar prefixo __Host- sem HTTPS.
SESSION_COOKIE_NAME = "iustus_local_session"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
DOCUMENT_LOCAL_STORAGE_ENABLED = True
DOCUMENT_STORAGE_ROOT = BASE_DIR.parent / ".local" / "documents"
DOCUMENT_SCANNER_HOST = env("DOCUMENT_SCANNER_HOST", default="127.0.0.1")
DOCUMENT_SCANNER_PORT = env.int("DOCUMENT_SCANNER_PORT", default=3310)
