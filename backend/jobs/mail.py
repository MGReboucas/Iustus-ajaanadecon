import logging
import uuid
from datetime import timedelta

from jobs.branded_mail import build_message
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.identity.models import IdentityEmail
from apps.identity.security import decrypt


def deliver_one():
    now = timezone.now()
    lease = uuid.uuid4()
    with transaction.atomic():
        item = (IdentityEmail.objects.select_for_update(skip_locked=True)
                .filter(sent_at__isnull=True, available_at__lte=now, attempts__lt=5)
                .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now))
                .order_by("created_at").first())
        if not item:
            return False
        item.lease_until = now + timedelta(minutes=5)
        item.lease_id = lease
        item.attempts += 1
        item.save(update_fields=["lease_until", "lease_id", "attempts"])
    # Efeito externo fora da transação. Entrega é at-least-once; token é de uso único.
    try:
        count = build_message(item.subject, decrypt(item.encrypted_body), [item.recipient]).send(fail_silently=False)
        if count != 1:
            raise RuntimeError("MailNotAccepted")
    except Exception as exc:
        logging.getLogger("jobs.mail").error("Identity email delivery failed: %s", type(exc).__name__,
            extra={"status_code": getattr(exc, "http_status", None) or "-"})
        IdentityEmail.objects.filter(pk=item.pk, lease_id=lease).update(
            lease_until=None, lease_id=None, last_error=type(exc).__name__[:40],
            available_at=timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** item.attempts)),
        )
    else:
        IdentityEmail.objects.filter(pk=item.pk, lease_id=lease).update(
            sent_at=timezone.now(), lease_until=None, lease_id=None, last_error="", encrypted_body="",
        )
    return True
