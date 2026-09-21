"""Jornadas de navegador com banco exclusivo e dados sintéticos."""
from .local import *  # noqa: F403
from .local import DATABASES

DATABASES = {"default": {**DATABASES["default"], "NAME": "iustus_e2e"}}
IDENTITY_RATE_LIMITS_ENABLED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DOCUMENT_STORAGE_ROOT = BASE_DIR.parent / ".local" / "documents-e2e"
