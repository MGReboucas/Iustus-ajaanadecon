from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.billing.provider import available
from integrations.mercadopago.orders import request_api
from urllib.error import HTTPError


class Command(BaseCommand):
    help = "Confere configuração Mercado Pago sem cobrar e sem imprimir credenciais."

    def add_arguments(self, parser):
        parser.add_argument("--remote", action="store_true", help="Consulta apenas /users/me para verificar a conta recebedora.")

    def handle(self, *args, **options):
        self.stdout.write(f"Provedor: {settings.BILLING_PROVIDER}; ambiente: {settings.MERCADOPAGO_ENVIRONMENT}")
        names = ["MERCADOPAGO_ACCESS_TOKEN", "MERCADOPAGO_PUBLIC_KEY", "MERCADOPAGO_WEBHOOK_SECRET", "MERCADOPAGO_COLLECTOR_ID",
                 "MERCADOPAGO_INTEREST_FREE_CONFIRMED"]
        missing = [name for name in names if not getattr(settings, name)]
        for name in names:
            self.stdout.write(name + (": configurado" if name not in missing else ": pendente"))
        self.stdout.write("Checkout: " + ("habilitado" if available() else "bloqueado"))
        if options["remote"]:
            try:
                account = request_api("/users/me", configuration_check=True)
            except Exception as exc:
                cause = exc.__cause__
                status = f" (HTTP {cause.code})" if isinstance(cause, HTTPError) else ""
                raise CommandError(getattr(exc, "identity_code", "PROVIDER_UNAVAILABLE") + status) from None
            if ("test_user" in account.get("tags", [])) != (settings.MERCADOPAGO_ENVIRONMENT == "sandbox"):
                raise CommandError("Conta de teste/produção incompatível com MERCADOPAGO_ENVIRONMENT.")
            if str(account.get("id")) != str(settings.MERCADOPAGO_COLLECTOR_ID):
                raise CommandError("Conta recebedora divergente de MERCADOPAGO_COLLECTOR_ID.")
            self.stdout.write("Credencial e conta recebedora conferidas. Isso não comprova homologação do parcelamento.")
        if missing:
            raise CommandError("Há configurações pendentes; nenhuma cobrança realizada.")
