import os
import secrets
import subprocess
import sys

from cryptography.fernet import Fernet
from django.test import SimpleTestCase
from django.conf import settings


class ProductionSettingsTests(SimpleTestCase):
    def run_settings(self, **overrides):
        values = {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "IUSTUS_PROXY_SECRET": secrets.token_urlsafe(48),
            "IDENTITY_ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "IUSTUS_PUBLIC_ORIGIN": "https://app.example.test",
            "DJANGO_ALLOWED_HOSTS": "backend.example.test",
            "DATABASE_URL": "postgresql://synthetic:synthetic@db.example.test/iustus",
            "EMAIL_HOST": "smtp.example.test", "EMAIL_HOST_USER": "synthetic",
            "EMAIL_HOST_PASSWORD": "synthetic", "DEFAULT_FROM_EMAIL": "Iustus <test@example.test>",
        }
        values.update(overrides)
        return subprocess.run([sys.executable, "manage.py", "check", "--deploy", "--fail-level", "ERROR"],
            cwd=settings.BASE_DIR, env={**os.environ, **values}, capture_output=True, text=True, timeout=30)

    def test_production_passes_checks_with_only_deliberate_hsts_rollout_warnings(self):
        result = self.run_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        import re
        self.assertEqual(set(re.findall(r"security\.W\d+", result.stderr)), {"security.W005", "security.W021"})

    def test_insecure_or_invalid_public_origins_are_rejected(self):
        for value in ("http://client.example.test", "https://client.example.test/path", "https://*.example.test", "https://localhost"):
            with self.subTest(value=value):
                self.assertNotEqual(self.run_settings(IUSTUS_PUBLIC_ORIGIN=value).returncode, 0)

    def test_wildcard_hosts_ephemeral_database_and_missing_mail_are_rejected(self):
        for overrides in ({"DJANGO_ALLOWED_HOSTS": "*"}, {"DATABASE_URL": "sqlite:///:memory:"},
                          {"EMAIL_HOST_PASSWORD": ""}, {"IUSTUS_PROXY_SECRET": "test-proxy-only"},
                          {"IDENTITY_ENCRYPTION_KEY": "invalid"}):
            with self.subTest(overrides=list(overrides)):
                self.assertNotEqual(self.run_settings(**overrides).returncode, 0)

    def test_direct_upload_requires_s3(self):
        self.assertNotEqual(self.run_settings(DOCUMENT_STORAGE_BACKEND="disabled",
                                             DOCUMENT_DIRECT_UPLOAD_ENABLED="true").returncode, 0)

    def test_s3_direct_configuration_passes_without_contacting_external_services(self):
        result = self.run_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_S3_BUCKET="synthetic-private",
            DOCUMENT_SCANNER_HOST="scanner.internal", DOCUMENT_DIRECT_UPLOAD_ENABLED="true")
        self.assertEqual(result.returncode, 0, result.stderr)
