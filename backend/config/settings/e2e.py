"""Jornadas de navegador com banco exclusivo e dados sintéticos."""
from .local import *  # noqa: F403
from .local import DATABASES

DATABASES = {"default": {**DATABASES["default"], "NAME": "iustus_e2e"}}
# Alternativa local para validar a interface quando PostgreSQL não está disponível.
# Os testes de concorrência continuam exigindo PostgreSQL.
if env.bool("IUSTUS_E2E_SQLITE", default=False):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                            "NAME": BASE_DIR.parent / ".local" / "iustus_e2e.sqlite3",
                            "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 20}}}
IDENTITY_RATE_LIMITS_ENABLED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DOCUMENT_STORAGE_ROOT = BASE_DIR.parent / ".local" / "documents-e2e"
MEMBERSHIP_REQUIRED = env.bool("IUSTUS_E2E_ASSOCIATION", default=False)
CASE_AUTO_ASSIGN = MEMBERSHIP_REQUIRED
CASE_INTAKE_REQUIRED = MEMBERSHIP_REQUIRED
BILLING_ENABLED = False  # O runner usa snapshots sintéticos, nunca cobrança real.
