"""Transactional notices: durable deduplication and current-state checks."""
import json
from datetime import timedelta

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from apps.identity.models import IdentityEmail, User
from apps.identity.security import decrypt, encrypt


def enqueue_notice(*, key, recipient, subject, body, context, path="/acessar"):
    validate_email(recipient)
    origin = getattr(settings, "EMAIL_PUBLIC_ORIGIN", settings.PORTAL_ORIGINS["client"])
    return IdentityEmail.objects.get_or_create(source_key=key, defaults={
        "recipient": recipient, "subject": subject,
        "encrypted_body": encrypt(body + "\n\nAcesse a Iustus:\n" + origin + path),
        "available_at": timezone.now(), "context": context,
    })


def notify_payment(order):
    messages = {
        "DECLINED": ("Pagamento não aprovado", "O pagamento da sua associação não foi aprovado. Volte ao site para conferir as opções de adesão antes de iniciar uma nova tentativa."),
        "CANCELED": ("Pagamento cancelado", "O pagamento da sua associação foi cancelado. Volte ao site para conferir as opções de adesão."),
        "REVOKED": ("Atualização do pagamento da associação", "Registramos uma reversão no pagamento da associação. Consulte a situação do acesso no painel. Seus casos anteriores continuam disponíveis."),
    }
    if order.status not in messages:
        return
    # Use the checkout identity, never an unverified webhook recipient.
    recipient = order.user.email if order.user_id else (
        json.loads(decrypt(order.encrypted_customer)).get("email", "") if order.encrypted_customer else "")
    if not recipient:
        return
    try:
        validate_email(recipient)
    except ValidationError:
        return
    subject, body = messages[order.status]
    enqueue_notice(key=f"payment:{order.pk}:{order.status}", recipient=recipient,
        subject="Iustus: " + subject, body=body,
        context={"kind": "PAYMENT", "order_id": str(order.pk), "status": order.status},
        path="/acessar" if order.user_id else "/")


def notify_privacy(item):
    answered = item.status == "ANSWERED"
    enqueue_notice(key=f"privacy:{item.pk}:{item.status}", recipient=item.owner.email,
        subject="Iustus: " + ("resposta à solicitação de privacidade" if answered else "solicitação de privacidade recebida"),
        body=("Sua solicitação de privacidade foi respondida. A resposta está disponível na sua conta."
              if answered else "Recebemos sua solicitação de privacidade. Você pode acompanhar a análise na sua conta."),
        context={"kind": "PRIVACY", "user_id": str(item.owner_id)})


def schedule_membership_notices():
    from apps.billing.models import Membership
    from apps.billing.provider import environment
    now = timezone.now()
    # The longest paid coverage prevents expiry warnings after a renewal.
    rows = Membership.objects.filter(revoked_at__isnull=True, order__status="PAID",
        order__environment=environment(), order__provider=settings.BILLING_PROVIDER,
        user__is_active=True).values("user_id").annotate(end=Max("expires_at"))
    for row in rows.filter(end__lte=now + timedelta(days=7), end__gte=now - timedelta(days=7)).iterator():
        user = User.objects.get(pk=row["user_id"])
        expired = row["end"] <= now
        kind = "MEMBERSHIP_EXPIRED" if expired else "MEMBERSHIP_EXPIRING"
        enqueue_notice(key=f"membership:{user.pk}:{row['end'].isoformat()}:{kind}",
            recipient=user.email, subject="Iustus: " + ("associação vencida" if expired else "associação próxima do vencimento"),
            body=("O período da sua associação terminou. Para enviar novas ocorrências, consulte as opções de nova adesão. Seus casos anteriores continuam disponíveis."
                  if expired else "Sua associação vence nos próximos sete dias. Consulte a validade e as opções de nova adesão na sua conta. Não há renovação automática."),
            context={"kind": kind, "user_id": str(user.pk), "expires_at": row["end"].isoformat()})


def notice_is_current(item):
    from apps.billing.models import Order, Membership
    from apps.billing.provider import environment
    from apps.billing.services import active_memberships
    context = item.context
    kind = context.get("kind")
    # Also protect pre-migration activation notices already in the queue.
    if not kind and item.subject == "Iustus: associação ativada":
        kind = "MEMBERSHIP_ACTIVE"
    user = None
    if context.get("user_id") or kind == "MEMBERSHIP_ACTIVE":
        user = User.objects.filter(email=item.recipient, is_active=True)
        if context.get("user_id"):
            user = user.filter(pk=context["user_id"])
        user = user.first()
        if user is None:
            return False
    if kind == "MEMBERSHIP_ACTIVE":
        return active_memberships(user).exists()
    if kind == "PAYMENT":
        order = Order.objects.filter(pk=context["order_id"], status=context["status"]).first()
        if not order or order.environment != environment(order.provider):
            return False
        if order.user_id:
            return order.user.is_active and order.user.email == item.recipient
        return bool(order.encrypted_customer and json.loads(decrypt(order.encrypted_customer)).get("email") == item.recipient)
    if kind in ("MEMBERSHIP_EXPIRED", "MEMBERSHIP_EXPIRING"):
        end = Membership.objects.filter(user=user, revoked_at__isnull=True, order__status="PAID",
            order__environment=environment(), order__provider=settings.BILLING_PROVIDER).aggregate(end=Max("expires_at"))["end"]
        if not end or end.isoformat() != context["expires_at"]:
            return False
        now = timezone.now()
        return (end <= now if kind == "MEMBERSHIP_EXPIRED" else now < end <= now + timedelta(days=7))
    return True
