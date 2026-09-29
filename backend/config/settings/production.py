"""Configuração web: falha ao iniciar se credenciais ou origens estiverem incompletas."""
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env


def required_secret(name, minimum=32):
    value = env(name)
    if len(value) < minimum or value.startswith("test-"):
        raise ImproperlyConfigured(f"{name} precisa de uma chave privada de produção.")
    return value


def https_origin(name):
    value = env(name).rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or parsed.port not in (None, 443)
            or parsed.hostname in ("localhost", "127.0.0.1", "::1") or "*" in parsed.netloc):
        raise ImproperlyConfigured(f"{name} deve ser uma origem HTTPS pública e exata.")
    return value


DEBUG = False
SECRET_KEY = required_secret("DJANGO_SECRET_KEY", 50)
IUSTUS_PROXY_SECRET = required_secret("IUSTUS_PROXY_SECRET")
IDENTITY_ENCRYPTION_KEY = env("IDENTITY_ENCRYPTION_KEY")
try:
    Fernet(IDENTITY_ENCRYPTION_KEY.encode())
except (ValueError, TypeError) as exc:
    raise ImproperlyConfigured("IDENTITY_ENCRYPTION_KEY deve ser uma chave Fernet persistente.") from exc

PORTAL_ORIGINS = {"client": https_origin("IUSTUS_CLIENT_ORIGIN"), "team": https_origin("IUSTUS_TEAM_ORIGIN")}
if urlsplit(PORTAL_ORIGINS["client"]).hostname == urlsplit(PORTAL_ORIGINS["team"]).hostname:
    raise ImproperlyConfigured("Cliente e equipe precisam de hosts distintos.")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS or any(not host or "*" in host or host.startswith(".") or "/" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS exige uma lista de hosts exatos.")
ALLOWED_HOSTS += [urlsplit(origin).hostname for origin in PORTAL_ORIGINS.values()]
CSRF_TRUSTED_ORIGINS = list(PORTAL_ORIGINS.values())

DATABASES = {"default": env.db("DATABASE_URL")}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("A implantação web exige PostgreSQL persistente.")
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"].setdefault("OPTIONS", {}).update(sslmode="require", connect_timeout=10)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

SESSION_COOKIE_NAME = "__Host-iustus_session"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_NAME = "__Host-iustus_csrf"
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_PATH = "/"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
if not all((EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL)):
    raise ImproperlyConfigured("Configure o envio autenticado de e-mail antes de publicar o cadastro.")
REGISTRATION_POLICY_VERSION = env("REGISTRATION_POLICY_VERSION", default="web-evaluation-v1")

# Sem permissões locais de submissão, arquivos temporários ou cobrança automática.
CASE_LOCAL_TEST_ACCESS = False
DOCUMENT_LOCAL_STORAGE_ENABLED = False
