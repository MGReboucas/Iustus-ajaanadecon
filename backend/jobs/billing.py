import uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.billing.models import PaymentEvent
from apps.billing.services import reconcile


def process_payment():
    now, lease = timezone.now(), uuid.uuid4()
    events = PaymentEvent.objects.all()
    if not settings.BILLING_ENABLED:
        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            return False
        # Desligar novas vendas não impede conferir pagamentos já enviados/estornos.
        events = events.filter(order__provider="mercadopago").exclude(provider_order_id="", order__provider_order_id__isnull=True)
    with transaction.atomic():
        event = events.select_for_update(skip_locked=True).filter(processed_at__isnull=True,
            attempts__lt=10, available_at__lte=now).filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now)).order_by("created_at").first()
        if not event:
            return False
        event.lease_id, event.lease_until = lease, now + timedelta(minutes=2)
        event.attempts += 1
        event.save()
    try:
        order = reconcile(event.order_id, event.provider_order_id)
    except Exception as exc:
        PaymentEvent.objects.filter(pk=event.pk, lease_id=lease).update(lease_id=None, lease_until=None,
            last_error=getattr(exc, "identity_code", type(exc).__name__)[:40], available_at=now + timedelta(seconds=min(3600, 30 * 2 ** event.attempts)))
    else:
        PaymentEvent.objects.filter(pk=event.pk, lease_id=lease).update(lease_id=None, lease_until=None,
            processed_at=None if order.status in ("WAITING", "CREATING") else timezone.now(), last_error="",
            available_at=now + timedelta(seconds=min(3600, 30 * 2 ** event.attempts)))
    return True
