"""Diagnóstico sem cobrança e sem exibir credenciais."""
import base64
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from integrations.pagbank.client import request_api


class Command(BaseCommand):
    help = "Confere configuração PagBank; --fetch-webhook-key consulta a chave sem habilitar pagamentos."

    def add_arguments(self, parser):
        parser.add_argument("--fetch-webhook-key", action="store_true")

    def handle(self, *args, **options):
        origin = settings.PORTAL_ORIGINS.get("client", "")
        parsed = urlsplit(origin)
        public = parsed.scheme == "https" and parsed.hostname not in (None, "localhost", "127.0.0.1", "::1")
        self.stdout.write(f"Ambiente: {settings.PAGBANK_ENVIRONMENT}")
        self.stdout.write(f"Checkout habilitado: {'sim' if settings.BILLING_ENABLED else 'não'}")
        self.stdout.write(f"Token configurado: {'sim' if settings.PAGBANK_API_TOKEN else 'não'}")
        self.stdout.write(f"Origem HTTPS pública: {'sim' if public else 'não'}")
        if public:
            self.stdout.write(f"Webhook: {origin}/api/v1/billing/webhook")
        value = settings.PAGBANK_WEBHOOK_PUBLIC_KEY
        if options["fetch_webhook_key"]:
            if not settings.PAGBANK_API_TOKEN:
                raise CommandError("Configure PAGBANK_API_TOKEN no backend/.env ou no ambiente do backend. Não envie a credencial pelo chat.")
            try:
                value = request_api("/public-keys?type=webhook", configuration_check=True).get("public_key", "")
            except Exception as exc:
                raise CommandError(getattr(exc, "detail", "Falha ao consultar a chave PagBank.")) from exc
        if value:
            try:
                raw = base64.b64decode(value, validate=True)
                key = serialization.load_der_public_key(raw)
                if not isinstance(key, ec.EllipticCurvePublicKey):
                    raise ValueError()
            except (ValueError, TypeError) as exc:
                raise CommandError("A chave recebida/configurada não é uma chave pública ECDSA X.509 válida. Confirme o serviço de notificações habilitado na conta.") from exc
            self.stdout.write("Chave de webhook válida; fingerprint SHA-256: " + hashlib.sha256(raw).hexdigest()[:16])
            if options["fetch_webhook_key"]:
                target = Path(settings.BASE_DIR).parent / ".local" / f"pagbank-{settings.PAGBANK_ENVIRONMENT}-webhook-key.txt"
                target.parent.mkdir(exist_ok=True)
                target.write_text(value + "\n", encoding="utf-8")
                self.stdout.write(f"Chave pública salva em {target}. Configure o conteúdo em PAGBANK_WEBHOOK_PUBLIC_KEY na API e no worker.")
        else:
            self.stdout.write("Chave pública de webhook: ausente")
        self.stdout.write("Nenhum pagamento foi criado. Este diagnóstico não substitui o teste de checkout, notificação e ativação.")
