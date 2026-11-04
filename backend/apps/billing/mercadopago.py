"""Ciclo anual: cada renovação é uma compra integral em 10 parcelas."""
import json
import re
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from apps.identity.models import User
from apps.identity.security import IdentityError, encrypt, decrypt, digest
from apps.identity.services import audit
from integrations.mercadopago import orders as client
from .checkout import canonical, check_identity, fingerprint
from .models import Order, Subscription, Membership, BillingIdentity, PaymentEvent
from .provider import available, environment


def decode(value):
    return json.loads(decrypt(value))


def start_order(data, session_digest, key):
    if not available() or settings.BILLING_PROVIDER != "mercadopago":
        raise IdentityError("BILLING_UNAVAILABLE", "Pagamento ainda indisponível.", 503)
    if not data["accepted"] or data["automaticRenewal"]:
        raise IdentityError("ACCEPTANCE_REQUIRED", "Confirme a compra anual sem renovação automática.", 422)
    reference = digest(session_digest + key)
    payload_digest = fingerprint(canonical(data))
    existing = Order.objects.filter(request_key=reference).first()
    if existing:
        if existing.provider != "mercadopago" or existing.environment != environment() or existing.payload_digest != payload_digest:
            raise IdentityError("CHECKOUT_CHANGED", "Esta tentativa já foi registrada com outros dados.", 409)
        return existing
    if (data["planVersion"] != settings.MEMBERSHIP_PLAN_VERSION or data["policyVersion"] != settings.REGISTRATION_POLICY_VERSION
            or data["card"]["installments"] != settings.MEMBERSHIP_INSTALLMENTS):
        raise IdentityError("PLAN_CHANGED", "Atualize a página para conferir as condições da adesão.", 409)
    buyer = check_identity(data["customer"], environment())
    if Order.objects.filter(session_digest=session_digest, environment=environment(), status__in=["CREATING", "WAITING"]).exclude(request_key=reference).exists():
        raise IdentityError("PAYMENT_PENDING", "Aguarde a confirmação do pagamento anterior.", 409)
    try:
        with transaction.atomic():
            subscription = Subscription.objects.create(environment=environment(), buyer_digest=buyer,
                amount=settings.MEMBERSHIP_PRICE_CENTS, installments=settings.MEMBERSHIP_INSTALLMENTS,
                plan_version=settings.MEMBERSHIP_PLAN_VERSION, policy_version=settings.REGISTRATION_POLICY_VERSION,
                encrypted_customer=encrypt(canonical(data["customer"])))
            return Order.objects.create(request_key=reference, session_digest=session_digest,
                provider="mercadopago", subscription=subscription, amount=subscription.amount,
                installments=subscription.installments, plan_version=subscription.plan_version,
                environment=subscription.environment, policy_version=subscription.policy_version,
                encrypted_customer=subscription.encrypted_customer, payload_digest=payload_digest)
    except IntegrityError as exc:
        existing = Order.objects.filter(request_key=reference, payload_digest=payload_digest).first()
        if existing:
            return existing
        raise IdentityError("SUBSCRIPTION_EXISTS", "Já existe uma assinatura ou pagamento em conferência para este CPF. Entre na sua conta para acompanhar.", 409) from exc


def send_order(order_id, card=None):
    if not available():
        raise IdentityError("BILLING_UNAVAILABLE", "Pagamento ainda indisponível.", 503)
    original = Order.objects.get(pk=order_id)
    if original.cycle:
        # Never send a scheduled renewal, including events queued before removal.
        if not original.provider_order_id:
            original.status, original.encrypted_payment_payload = "CANCELED", ""
            original.save(update_fields=["status", "encrypted_payment_payload"])
        return original
    # Ordem de bloqueio constante: assinatura, pedido. Cancelamento usa a mesma assinatura.
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=original.subscription_id)
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.provider_order_id or order.status != "CREATING":
            return order
        if subscription.canceled_at:
            order.status = "CANCELED"
            order.encrypted_payment_payload = ""
            order.save()
            return order
        if order.environment != environment() or order.provider != "mercadopago":
            raise IdentityError("PAYMENT_MISMATCH", "Ambiente de pagamento divergente.", 409)
        if not subscription.encrypted_instrument:
            if not card:
                return order  # Cartão inicial permanece apenas na memória do navegador.
            instrument = client.prepare_instrument(decode(order.encrypted_customer), card, subscription.pk)
            subscription.encrypted_instrument = encrypt(canonical(instrument))
            subscription.save(update_fields=["encrypted_instrument"])
        if not order.encrypted_payment_payload:
            payload = client.payment_payload(order, subscription, decode(subscription.encrypted_instrument), card)
            order.encrypted_payment_payload = encrypt(canonical(payload))
            order.payment_started_at = timezone.now()
            order.save(update_fields=["encrypted_payment_payload", "payment_started_at"])
    # O payload cifrado é durável ANTES da cobrança: reenvio conserva token e chave.
    failure = None
    stale = False
    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=original.subscription_id)
        attempt = Order.objects.select_for_update().get(pk=order_id)
        if (attempt.status == "CREATING" and not attempt.provider_order_id and attempt.payment_started_at
                and attempt.payment_started_at < timezone.now() - timedelta(hours=23)):
            if not sub.canceled_at:
                sub.status = "REVIEW"
                sub.save(update_fields=["status"])
            attempt.status, attempt.encrypted_payment_payload = "REVIEW", ""
            attempt.save(update_fields=["status", "encrypted_payment_payload"])
            stale = True
    if stale:
        raise IdentityError("PAYMENT_REVIEW_REQUIRED", "Pagamento em conferência. Não inicie outra cobrança.", 409)
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=original.subscription_id)
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.provider_order_id or order.status != "CREATING":
            return order
        if subscription.canceled_at:
            order.status = "CANCELED"
            order.encrypted_payment_payload = ""
            order.save()
            return order
        if order.payment_started_at < timezone.now() - timedelta(hours=23):
            subscription.status = "REVIEW"
            subscription.save(update_fields=["status"])
            raise IdentityError("PAYMENT_REVIEW_REQUIRED", "Pagamento em conferência. Não inicie outra cobrança.", 409)
        PaymentEvent.objects.get_or_create(digest=digest("mp-send:" + str(order.pk)), defaults={
            "order": order, "provider_order_id": "", "available_at": timezone.now()})
        try:
            payload = decode(order.encrypted_payment_payload)
            if payload.get("type") != "online" or any("stored_credential" in tx or "automatic_payments" in tx for tx in payload.get("transactions", {}).get("payments", [])):
                raise IdentityError("PAYMENT_REVIEW_REQUIRED", "Tentativa anterior exige conferência antes da migração.", 409)
            result = client.create_order(payload, order.pk)
            payment_id = client.identifier(result.get("id"))
            if not re.fullmatch(client.ORDER_ID, payment_id) or result.get("external_reference") != str(order.pk):
                raise IdentityError("INVALID_PAYMENT", "Pagamento em conferência.", 502)
            order.provider_order_id, order.status = payment_id, "WAITING"
            order.encrypted_payment_payload = ""
            order.save()
        except IdentityError as exc:
            failure = exc  # Commit do evento mesmo quando a resposta externa se perde.
    if failure:
        raise failure
    return order


def reconcile_payment(order_id, provider_id=""):
    from .services import send_access
    candidate = Order.objects.select_related("subscription").get(pk=order_id)
    if candidate.environment != environment("mercadopago"):
        raise IdentityError("PAYMENT_MISMATCH", "Ambiente divergente.", 422)
    if not provider_id:
        provider_id = candidate.provider_order_id
    if not provider_id:
        candidate = send_order(order_id)
        provider_id = candidate.provider_order_id
        if not provider_id:
            return candidate
    snapshot = client.payment(provider_id)
    if str(snapshot.get("id")) != str(provider_id):
        raise IdentityError("PAYMENT_MISMATCH", "Identificador divergente.", 422)
    instrument = decode(candidate.subscription.encrypted_instrument)
    client.validate_payment(candidate, snapshot, instrument)
    state = snapshot.get("status")
    refunded = state in ("refunded", "charged_back") or client.cents(snapshot.get("transaction_amount_refunded", 0)) > 0
    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(pk=candidate.subscription_id)
        order = Order.objects.select_for_update().get(pk=order_id)
        if order.provider_order_id and order.provider_order_id != str(provider_id):
            raise IdentityError("PAYMENT_MISMATCH", "Pedido já vinculado a outro pagamento.", 422)
        order.provider_order_id = str(provider_id)
        order.encrypted_payment_payload = ""
        order.checked_at = timezone.now()
        if refunded:
            order.status = "REVOKED" if order.paid_at else "CANCELED"
            Membership.objects.filter(order=order, revoked_at__isnull=True).update(revoked_at=timezone.now())
            sub.status, sub.canceled_at = "CANCELED", sub.canceled_at or timezone.now()
        elif state == "approved" and order.status not in ("PAID", "REVOKED"):
            customer = decode(order.encrypted_customer)
            cpf_digest = check_identity(customer, order.environment)
            user, created = User.objects.get_or_create(email=customer["email"], defaults={"first_name": customer["name"]})
            user = User.objects.select_for_update().get(pk=user.pk)
            if user.role != "CLIENT" or not user.is_active:
                raise IdentityError("BUYER_REVIEW_REQUIRED", "Cadastro em conferência.", 422)
            identity, _ = BillingIdentity.objects.get_or_create(user=user, environment=order.environment,
                defaults={"cpf_digest": cpf_digest, "encrypted_cpf": encrypt(customer["cpf"])})
            if identity.cpf_digest != cpf_digest:
                raise IdentityError("BUYER_MISMATCH", "Cadastro divergente.", 422)
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            paid_at = parse_datetime(snapshot.get("date_approved") or "")
            if not paid_at or timezone.is_naive(paid_at) or paid_at > timezone.now() + timedelta(minutes=5):
                raise IdentityError("INVALID_PAYMENT_DATE", "Data de pagamento inválida.", 422)
            latest = Membership.objects.filter(user=user, revoked_at__isnull=True,
                order__environment=order.environment).aggregate(end=Max("expires_at"))["end"]
            start = max(paid_at, latest) if latest else paid_at
            membership = Membership.objects.create(order=order, user=user, starts_at=start, expires_at=start + relativedelta(years=1))
            order.user, order.paid_at, order.status = user, paid_at, "PAID"
            sub.user, sub.next_charge_at, sub.last_cycle = user, None, order.cycle
            sub.status, sub.canceled_at = "COMPLETED", sub.canceled_at or timezone.now()
            send_access(user)
            audit(user, "membership.paid", "client", orderId=str(order.pk))
        elif order.status not in ("PAID", "REVOKED"):
            order.status = {"rejected": "DECLINED", "cancelled": "CANCELED"}.get(state, "WAITING")
            if order.status in ("DECLINED", "CANCELED"):
                sub.status = "PAST_DUE" if order.cycle else "CANCELED"
                if not order.cycle:
                    sub.canceled_at = timezone.now()
        order.save()
        sub.save()
    return order


def subscription_data(user):
    return {"subscription": None}


def cancel_renewal(user):
    with transaction.atomic():
        for sub in Subscription.objects.select_for_update().filter(user=user, environment=environment("mercadopago"), canceled_at__isnull=True):
            sub.canceled_at, sub.status = timezone.now(), "CANCELED"
            sub.save(update_fields=["canceled_at", "status"])
            audit(user, "membership.renewal_canceled", "client", subscriptionId=str(sub.pk))
    return subscription_data(user)


def renew_due():
    # Automatic billing removed by product decision, irrespective of old flags.
    return False
