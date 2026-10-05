from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.identity.models import User, IdentityEmail
from apps.identity.security import IdentityError, encrypt
from apps.identity.services import issue_token, audit
from integrations.pagbank.client import request_api
from .models import Order, Membership


def active_memberships(user):
    now = timezone.now()
    return Membership.objects.filter(user=user, starts_at__lte=now, expires_at__gt=now,
        revoked_at__isnull=True, order__environment=settings.PAGBANK_ENVIRONMENT, order__status="PAID")


def membership_data(user):
    row = active_memberships(user).order_by("-expires_at").first()
    return {"active": bool(row), "expiresAt": row.expires_at.isoformat() if row else None}


def send_access(user):
    if not user.has_usable_password() or not user.email_verified_at:
        issue_token("MEMBER", user.email, "client", user)
    else:
        IdentityEmail.objects.create(recipient=user.email, subject="Iustus: associação ativada", available_at=timezone.now(),
            encrypted_body=encrypt("Seu pagamento foi confirmado e sua associação está ativa. Entre com sua conta para cadastrar ocorrências e acompanhar seus casos.\n\n" + settings.PORTAL_ORIGINS["client"] + "/acessar"))


def reconcile(order_id, provider_id):
    # Consultar estado atual autenticado evita replays de um webhook PAID após estorno.
    snapshot = request_api("/orders/" + provider_id)
    if snapshot.get("id") != provider_id or snapshot.get("reference_id") != str(order_id):
        raise IdentityError("PAYMENT_MISMATCH", "Pagamento não corresponde ao pedido.", 422)
    candidate = Order.objects.get(pk=order_id)
    items = snapshot.get("items", [])
    if len(items) != 1 or items[0].get("reference_id") != "iustus-associacao-anual" or items[0].get("quantity") != 1 or items[0].get("unit_amount") != candidate.amount:
        raise IdentityError("PAYMENT_AMOUNT_MISMATCH", "Valor do pedido não corresponde à adesão.", 422)
    charges = snapshot.get("charges", [])
    # Um pedido deve ter um pagamento integral; pagamentos divididos não fazem parte deste plano.
    paid = [c for c in charges if c.get("status") == "PAID" and c.get("amount", {}).get("currency") == "BRL"
            and c.get("amount", {}).get("value", 0) >= candidate.amount
            and c.get("amount", {}).get("summary", {}).get("paid", 0) >= candidate.amount
            and not c.get("amount", {}).get("summary", {}).get("refunded", 0)]
    refunded = any(c.get("amount", {}).get("summary", {}).get("refunded", 0) or c.get("status") in ("CANCELED", "REFUNDED", "CHARGEBACK") for c in charges)
    customer = snapshot.get("customer", {})
    email = str(customer.get("email", "")).strip().lower()
    if paid:
        try:
            validate_email(email)
            if len(email) > 254 or not str(customer.get("name", "")).strip():
                raise ValidationError("InvalidCustomer")
        except ValidationError as exc:
            raise IdentityError("INVALID_BUYER", "Dados do associado inválidos.", 422) from exc
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.environment != settings.PAGBANK_ENVIRONMENT or (order.provider_order_id and order.provider_order_id != provider_id):
            raise IdentityError("PAYMENT_MISMATCH", "Ambiente ou pagamento incompatível.", 422)
        order.provider_order_id = provider_id
        order.checked_at = timezone.now()
        if paid and order.status not in ("PAID", "REVOKED"):
            user, created = User.objects.get_or_create(email=email, defaults={"first_name": str(customer["name"])[:150]})
            user = User.objects.select_for_update().get(pk=user.pk)
            if user.role != "CLIENT" or not user.is_active:
                raise IdentityError("BUYER_REVIEW_REQUIRED", "O cadastro precisa de conferência pela associação.", 422)
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            paid_at = parse_datetime(paid[0].get("paid_at", ""))
            if not paid_at or timezone.is_naive(paid_at) or paid_at > timezone.now() + timedelta(minutes=5):
                raise IdentityError("INVALID_PAYMENT_DATE", "Data de pagamento inválida.", 422)
            latest = Membership.objects.filter(user=user, revoked_at__isnull=True, order__environment=order.environment).aggregate(end=Max("expires_at"))["end"]
            start = max(paid_at, latest) if latest else paid_at
            order.user, order.paid_at, order.status = user, paid_at, "PAID"
            Membership.objects.create(order=order, user=user, starts_at=start, expires_at=start + relativedelta(years=1))
            send_access(user)
            audit(user, "membership.paid", "client", orderId=str(order.pk))
        elif not paid and refunded:
            order.status = "REVOKED" if order.paid_at else "CANCELED"
            Membership.objects.filter(order=order, revoked_at__isnull=True).update(revoked_at=timezone.now())
            if order.user_id:
                audit(order.user, "membership.revoked", "client", orderId=str(order.pk))
        elif order.status not in ("PAID", "REVOKED"):
            order.status = "DECLINED" if charges and all(c.get("status") == "DECLINED" for c in charges) else "WAITING"
        order.save()
    return order
