"""Fixtures locais, restritas ao banco iustus_e2e e contas sintéticas e2e-*.

Chamado pelo runner; nunca publicar como endpoint nem executar em produção.
"""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.e2e"
import django
django.setup()

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from apps.identity.models import IdentityEmail, User
from apps.identity.security import decrypt

action = sys.argv[1]
db = settings.DATABASES["default"]
sqlite = db["ENGINE"] == "django.db.backends.sqlite3"
expected_name = ROOT / ".local" / "iustus_e2e.sqlite3" if sqlite else "iustus_e2e"
if db["NAME"] != expected_name or not settings.DEBUG:
    raise SystemExit("Fixtures só são permitidas no banco isolado iustus_e2e.")
if not sqlite and db["HOST"] not in ("localhost", "127.0.0.1", "::1"):
    raise SystemExit("Fixtures exigem PostgreSQL local. Não use a URL do banco de produção.")

if action == "prepare":
    if not sqlite:
        import psycopg
        with psycopg.connect(dbname="postgres", user=db["USER"], password=db["PASSWORD"], host=db["HOST"], port=db["PORT"], autocommit=True) as connection:
            if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("iustus_e2e",)).fetchone():
                connection.execute("CREATE DATABASE iustus_e2e")
    call_command("migrate", interactive=False, verbosity=0)
    print("Banco E2E preparado.")
else:
    email = sys.argv[2]
    if not re.fullmatch(r"e2e-[a-z0-9-]+@example\.test", email):
        raise SystemExit("Fixture aceita somente endereços sintéticos e2e-*@example.test.")
    if action in ("admin", "lawyer", "client"):
        names = {"admin": "Admin Teste", "lawyer": "Advogado Teste", "client": "Cliente Teste"}
        user = User.objects.create_user(email, "Synthetic-Browser-Passphrase-938!", first_name=names[action], role=action.upper(), email_verified_at=timezone.now())
        print(json.dumps({"id": str(user.pk)}))
    elif action == "case-grant":
        from datetime import timedelta
        from apps.cases.models import LocalCaseAccess
        user = User.objects.get(email=email, role="CLIENT")
        LocalCaseAccess.objects.update_or_create(user=user, defaults={"expires_at": timezone.now() + timedelta(days=1), "reason": "Jornada sintética de navegador"})
        print(json.dumps({"granted": True}))
    elif action == "document-scan-fixture":
        # Apenas o runner isolado substitui o scanner. Não existe bypass na aplicação.
        from unittest.mock import patch
        from apps.documents.models import DocumentVersion
        from jobs.documents import scan_one
        user = User.objects.get(email=email, role="CLIENT")
        with patch("jobs.documents.scan", return_value=True):
            # O banco e diretório são exclusivos de E2E; nenhuma fila local é tocada.
            for _ in range(DocumentVersion.objects.filter(status="QUARANTINED").count()):
                scan_one()
        print(json.dumps({"available": DocumentVersion.objects.filter(uploaded_by=user, status="AVAILABLE").count()}))
    elif action == "mail":
        item = IdentityEmail.objects.filter(recipient=email).latest("created_at")
        print(json.dumps({"body": decrypt(item.encrypted_body)}))
    else:
        raise SystemExit("Ação desconhecida.")
