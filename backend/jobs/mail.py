import logging
import re
import uuid
from datetime import timedelta

from jobs.branded_mail import build_message
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.identity.models import ActionToken, IdentityEmail, User
from apps.identity.security import decrypt, digest


def action_is_current(body, recipient):
    """Check queued links too: a resend may have invalidated them while offline."""
    match = re.search(r"#(verify|reset|invite|member)=([^\s]+)", body)
    if not match:
        return True
    token = ActionToken.objects.select_related("user", "created_by").filter(
        digest=digest(match[2]), purpose=match[1].upper(), email=recipient,
    ).first()
    if not token or token.consumed_at or token.expires_at <= timezone.now():
        return False
    user = token.user
    if not user or not user.is_active or user.email != recipient or user.auth_version != token.auth_version:
        return False
    if token.purpose == "INVITE":
        if user.email_verified_at or user.has_usable_password():
            return False
        inviter = token.created_by
        return ((user.role == User.Role.ADMIN and inviter is None)
                or (user.role == User.Role.LAWYER and inviter is not None
                    and inviter.is_active and inviter.role == User.Role.ADMIN))
    return True


def deliver_one():
    now = timezone.now()
    lease = uuid.uuid4()
    with transaction.atomic():
        item = (IdentityEmail.objects.select_for_update(skip_locked=True)
                .filter(sent_at__isnull=True, cancelled_at__isnull=True, available_at__lte=now, attempts__lt=5)
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
        body = decrypt(item.encrypted_body)
        if not action_is_current(body, item.recipient):
            IdentityEmail.objects.filter(pk=item.pk, lease_id=lease).update(
                cancelled_at=timezone.now(), lease_until=None, lease_id=None,
                last_error="StaleActionToken", encrypted_body="",
            )
            return True
        count = build_message(item.subject, body, [item.recipient]).send(fail_silently=False)
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
