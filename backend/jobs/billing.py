import uuid
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.billing.models import PaymentEvent
from apps.billing.services import reconcile


def process_payment():
    now, lease = timezone.now(), uuid.uuid4()
    with transaction.atomic():
        event = PaymentEvent.objects.select_for_update(skip_locked=True).filter(processed_at__isnull=True,
            attempts__lt=10, available_at__lte=now).filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now)).order_by("created_at").first()
        if not event:
            return False
        event.lease_id, event.lease_until = lease, now + timedelta(minutes=2)
        event.attempts += 1
        event.save()
    try:
        reconcile(event.order_id, event.provider_order_id)
    except Exception as exc:
        PaymentEvent.objects.filter(pk=event.pk, lease_id=lease).update(lease_id=None, lease_until=None,
            last_error=getattr(exc, "identity_code", type(exc).__name__)[:40], available_at=now + timedelta(seconds=min(3600, 30 * 2 ** event.attempts)))
    else:
        PaymentEvent.objects.filter(pk=event.pk, lease_id=lease).update(lease_id=None, lease_until=None,
            processed_at=timezone.now(), last_error="")
    return True
