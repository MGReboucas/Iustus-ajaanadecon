"""Configuração comum; esta fundação não publica fluxos de negócio."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()

DEBUG = False
ALLOWED_HOSTS = []
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "apps.identity",
    "apps.billing",
    "apps.cases",
    "apps.documents",
    "apps.legal",
    "apps.communication",
    "apps.administration",
    "apps.privacy",
    "apps.audit",
    "jobs",
]
MIDDLEWARE = [
    "apps.identity.middleware.PortalMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.identity.middleware.SessionBoundaryMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTH_USER_MODEL = "identity.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.identity.errors.identity_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
CSRF_FAILURE_VIEW = "apps.identity.middleware.csrf_failure"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144
IDENTITY_RATE_LIMITS_ENABLED = True
IDENTITY_IDLE_SECONDS = {"client": 7200, "team": 1800}
IDENTITY_SESSION_SECONDS = {"client": 86400, "team": 43200}
DEFAULT_FROM_EMAIL = "Iustus <no-reply@localhost>"
# Sem settings produtivos: políticas locais são explicitamente de teste.
REGISTRATION_POLICY_VERSION = "development-v1"
CASE_LOCAL_TEST_ACCESS = False
DOCUMENT_LOCAL_STORAGE_ENABLED = False
DOCUMENT_STORAGE_ROOT = None
DOCUMENT_SCANNER_HOST = "127.0.0.1"
DOCUMENT_SCANNER_PORT = 3310
DOCUMENT_SCANNER_TIMEOUT = 30

DOCUMENT_STORAGE_BACKEND = "local"
DOCUMENT_S3_BUCKET = ""
DOCUMENT_S3_ENDPOINT = ""
DOCUMENT_S3_REGION = "us-east-1"
DOCUMENT_S3_PREFIX = "iustus/objects"
DOCUMENT_S3_ACCESS_KEY = ""
DOCUMENT_S3_SECRET_KEY = ""
DOCUMENT_S3_ADDRESSING_STYLE = "auto"

# Ativar somente após homologar o bucket, CORS e gravação condicional.
DOCUMENT_DIRECT_UPLOAD_ENABLED = False

# Pode ser desativado explicitamente em ambientes de teste assistido.
IDENTITY_MFA_REQUIRED = env.bool("IDENTITY_MFA_REQUIRED", default=True)

IDENTITY_SHARED_PORTAL = False

# Cobrança permanece desativada até configurar e homologar o provedor.
BILLING_ENABLED = env.bool("BILLING_ENABLED", default=False)
PAGBANK_ENVIRONMENT = env("PAGBANK_ENVIRONMENT", default="sandbox")
PAGBANK_API_TOKEN = env("PAGBANK_API_TOKEN", default="")
PAGBANK_WEBHOOK_PUBLIC_KEY = env("PAGBANK_WEBHOOK_PUBLIC_KEY", default="")
MEMBERSHIP_PRICE_CENTS = 95880
MEMBERSHIP_REQUIRED = True
CASE_AUTO_ASSIGN = True
CASE_INTAKE_REQUIRED = True
