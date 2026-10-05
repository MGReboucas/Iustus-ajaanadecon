"""Consulta uma identidade sintética na base E2E isolada, nunca no banco real."""
import os
import sys
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.e2e"
import django
django.setup()
from django.conf import settings
from apps.identity.models import User
db = settings.DATABASES["default"]
if not settings.DEBUG or db["NAME"] != root / ".local" / "iustus_e2e.sqlite3":
    raise SystemExit("Apenas SQLite E2E isolado.")
user = User.objects.get(pk=sys.argv[1], role="LAWYER", email__startswith="e2e-", email__endswith="@example.test")
print(json.dumps({"email": user.email}))
