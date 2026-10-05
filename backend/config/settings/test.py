"""Testes unitários da fundação, sem .env, rede ou banco de desenvolvimento."""
from .base import *  # noqa: F403

SECRET_KEY = "test-only-not-a-deployment-secret"
ALLOWED_HOSTS = ["testserver", "localhost"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
IDENTITY_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
IUSTUS_PROXY_SECRET = "test-proxy-only"
PORTAL_ORIGINS = {"client": "http://localhost:3000", "team": "http://127.0.0.1:3000"}
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
IDENTITY_RATE_LIMITS_ENABLED = False
# Suites legadas continuam exercitando as liberações assistidas; a nova jornada
# tem testes próprios com todas as regras comerciais ligadas.
MEMBERSHIP_REQUIRED = False
CASE_AUTO_ASSIGN = False
CASE_INTAKE_REQUIRED = False
