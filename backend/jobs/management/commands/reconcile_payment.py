import re
from django.core.management.base import BaseCommand, CommandError
from apps.billing.models import Order, PaymentEvent
from apps.billing.services import reconcile
from django.utils import timezone


class Command(BaseCommand):
    help = "Reconcilia um pedido com consulta autenticada ao PagBank; nunca aprova manualmente."

    def add_arguments(self, parser):
        parser.add_argument("order_id")
        parser.add_argument("provider_order_id")

    def handle(self, *args, **options):
        provider_id = options["provider_order_id"]
        if not re.fullmatch(r"ORDE_[A-Za-z0-9-]+", provider_id):
            raise CommandError("Informe o identificador ORDE_ do PagBank.")
        try:
            order = Order.objects.get(pk=options["order_id"])
            order = reconcile(order.pk, provider_id)
        except Exception as exc:
            raise CommandError(getattr(exc, "identity_code", type(exc).__name__)) from exc
        PaymentEvent.objects.filter(order=order, provider_order_id=provider_id, processed_at__isnull=True).update(processed_at=timezone.now(), last_error="")
        self.stdout.write(f"Pedido {order.pk}: {order.status}")
