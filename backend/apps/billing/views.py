import hashlib
import json
import re
from datetime import timedelta
from uuid import UUID
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.identity.models import User
from apps.identity.views import PublicView, IdentityView
from apps.identity.mobile import MobileView
from apps.identity.serializers import AcceptInviteSerializer, EmailSerializer
from apps.identity.services import locked_token, consume, validate_new_password, audit
from apps.identity.security import IdentityError, digest, encrypt
from integrations.pagbank.client import create_card_order, card_public_key, verify_signature
from .models import Order, PaymentEvent
from .services import active_memberships, send_access, reconcile
from .checkout import CheckoutInput, MercadoPagoCheckoutInput, canonical, fingerprint, check_identity
from .provider import available, environment
from . import mercadopago


class CardKeyView(PublicView):
    def get(self, request):
        self.public_limit(request, "card-key", limit=30)
        if settings.BILLING_PROVIDER == "mercadopago":
            if not available():
                raise IdentityError("BILLING_UNAVAILABLE", "Pagamento ainda indisponível.", 503)
            return Response({"publicKey": settings.MERCADOPAGO_PUBLIC_KEY})
        return Response({"publicKey": card_public_key()})


class PlanView(PublicView):
    def get(self, request):
        return Response({"amount": settings.MEMBERSHIP_PRICE_CENTS, "installments": settings.MEMBERSHIP_INSTALLMENTS,
            "planVersion": settings.MEMBERSHIP_PLAN_VERSION, "available": available(), "provider": settings.BILLING_PROVIDER,
            "automaticRenewal": False,
            "sandbox": environment() == "sandbox", "policyVersion": settings.REGISTRATION_POLICY_VERSION})


class CheckoutView(PublicView):
    def post(self, request):
        self.public_limit(request, "checkout", limit=20)
        if settings.BILLING_PROVIDER == "mercadopago":
            data = self.data(request, MercadoPagoCheckoutInput)
            key = request.headers.get("Idempotency-Key", "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
                raise IdentityError("IDEMPOTENCY_REQUIRED", "Atualize a página e tente novamente.")
            if not request.session.session_key:
                request.session.create()
            order = mercadopago.start_order(data, digest(request.session.session_key), key)
            request.session["checkout_order"] = str(order.pk)
            request.session.save()
            order = mercadopago.send_order(order.pk, data["card"])
            return Response({"status": order.status}, status=201)
        data = self.data(request, CheckoutInput)
        if not data["accepted"]:
            raise IdentityError("ACCEPTANCE_REQUIRED", "Confirme as condições da adesão.", 422)
        if not settings.BILLING_ENABLED:
            raise IdentityError("BILLING_UNAVAILABLE", "A adesão online ainda não está disponível.", 503)
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
            raise IdentityError("IDEMPOTENCY_REQUIRED", "Atualize a página e tente novamente.")
        if not request.session.session_key:
            request.session.create()
        session_digest = digest(request.session.session_key)
        customer = data["customer"]
        check_identity(customer, settings.PAGBANK_ENVIRONMENT)
        payload_digest = fingerprint(canonical(data))
        reference = digest(session_digest + key)
        if Order.objects.filter(session_digest=session_digest, environment=settings.PAGBANK_ENVIRONMENT, status__in=["CREATING", "WAITING"]).exclude(request_key=reference).exists():
            raise IdentityError("PAYMENT_PENDING", "Existe um pagamento em conferência. Aguarde a confirmação antes de iniciar outro.", 409)
        # Persistir referência e sessão antes da chamada externa, inclusive em timeouts.
        order, _ = Order.objects.get_or_create(request_key=digest(session_digest + key), defaults={
            "session_digest": session_digest, "amount": settings.MEMBERSHIP_PRICE_CENTS,
            "installments": settings.MEMBERSHIP_INSTALLMENTS, "plan_version": settings.MEMBERSHIP_PLAN_VERSION,
            "environment": settings.PAGBANK_ENVIRONMENT, "policy_version": settings.REGISTRATION_POLICY_VERSION,
            "encrypted_customer": encrypt(canonical(customer)), "payload_digest": payload_digest})
        if order.payload_digest != payload_digest or order.environment != settings.PAGBANK_ENVIRONMENT:
            raise IdentityError("CHECKOUT_CHANGED", "Os dados desta tentativa não podem ser alterados enquanto o pagamento está em conferência.", 409)
        request.session["checkout_order"] = str(order.pk)
        request.session.save()
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if not order.provider_order_id:
                # Não arriscar uma cobrança duplicada fora da janela de repetição local.
                if order.created_at < timezone.now() - timedelta(hours=1):
                    raise IdentityError("PAYMENT_REVIEW_REQUIRED", "Esta tentativa precisa de conferência. Entre em contato com a associação antes de pagar novamente.", 409)
                order.provider_order_id = create_card_order(order, customer, data["card"])
                order.status = "WAITING"
                order.save()
                PaymentEvent.objects.get_or_create(digest=digest("checkout:" + str(order.pk)), defaults={
                    "order": order, "provider_order_id": order.provider_order_id, "available_at": timezone.now()})
        return Response({"status": order.status}, status=201)

    def get(self, request):
        order = Order.objects.filter(pk=request.session.get("checkout_order")).first()
        if not order or order.session_digest != digest(request.session.session_key or ""):
            raise Http404
        # Uma consulta autenticada confirma o pagamento mesmo se o webhook atrasar.
        if (order.provider_order_id or order.provider == "mercadopago") and order.status in ("CREATING", "WAITING"):
            self.public_limit(request, "checkout-status", limit=120)
            due = timezone.now() - timedelta(seconds=15)
            claimed = Order.objects.filter(pk=order.pk).filter(Q(checked_at__isnull=True) | Q(checked_at__lt=due)).update(checked_at=timezone.now())
            if claimed:
                try:
                    order = reconcile(order.pk, order.provider_order_id)
                except IdentityError:
                    order.refresh_from_db()  # Surface durable review states to the browser.
        return Response({"status": order.status})


class ResetSandboxCheckoutView(PublicView):
    def post(self, request):
        if request.data != {"confirm": True}:
            raise IdentityError("INVALID_INPUT", "Confirme o encerramento do teste.", 422)
        order = Order.objects.filter(pk=request.session.get("checkout_order")).first()
        if not order or order.session_digest != digest(request.session.session_key or ""):
            raise Http404
        mercadopago.archive_sandbox_order(order.pk, digest(request.session.session_key or ""))
        request.session.pop("checkout_order", None)
        return Response({"reset": True})


class ActivateView(PublicView):
    def post(self, request):
        self.public_limit(request, "member-activate", limit=20)
        data = self.data(request, AcceptInviteSerializer)
        with transaction.atomic():
            token = locked_token(data["token"], "MEMBER", "client")
            user = User.objects.select_for_update().get(pk=token.user_id)
            if user.role != "CLIENT" or not user.is_active or user.auth_version != token.auth_version or not active_memberships(user).exists():
                raise IdentityError("INVALID_TOKEN", "Link indisponível ou associação inativa.", 422)
            validate_new_password(data["password"], user)
            user.set_password(data["password"])
            user.first_name = data["name"]
            user.email_verified_at = timezone.now()
            user.accepted_policy_version = settings.REGISTRATION_POLICY_VERSION
            user.auth_version += 1
            user.save()
            consume(token)
            audit(user, "membership.activated", "client")
        return Response(status=204)


class ResendAccessView(PublicView):
    def post(self, request):
        data = self.data(request, EmailSerializer)
        self.public_limit(request, "member-resend", data["email"], limit=3)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=data["email"], role="CLIENT", is_active=True).first()
            if user and active_memberships(user).exists():
                send_access(user)
        return Response({"message": "Se houver pagamento confirmado para este e-mail, enviaremos as instruções de acesso."}, status=202)


class WebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.body
        if not settings.BILLING_ENABLED or not verify_signature(raw, request.headers.get("x-payload-signature", "")):
            raise IdentityError("INVALID_SIGNATURE", "Notificação não autenticada.", 403)
        try:
            payload = json.loads(raw)
            identifier = payload["id"]
            reference = UUID(payload["reference_id"])
            if not isinstance(identifier, str):
                raise ValueError()
            order = Order.objects.filter(pk=reference, environment=settings.PAGBANK_ENVIRONMENT).first()
        except (ValueError, KeyError, TypeError, AttributeError):
            raise IdentityError("INVALID_EVENT", "Notificação inválida.")
        if not order:
            return Response(status=204)
        if re.fullmatch(r"ORDE_[A-Za-z0-9-]+", identifier):
            PaymentEvent.objects.get_or_create(digest=hashlib.sha256(raw).hexdigest(), defaults={
                "order": order, "provider_order_id": identifier, "available_at": timezone.now()})
        elif identifier == order.checkout_id and payload.get("status") == "EXPIRED":
            Order.objects.filter(pk=order.pk, status="WAITING").update(status="EXPIRED")
        return Response(status=204)


class MercadoPagoWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        from integrations.mercadopago import orders as client
        identifier = request.query_params.get("data.id", "")
        if not client.verify_signature(identifier, request.headers.get("x-request-id", ""), request.headers.get("x-signature", "")):
            raise IdentityError("INVALID_SIGNATURE", "Notificação não autenticada.", 403)
        payload = request.data
        if not isinstance(payload, dict) or payload.get("type") != ("order" if identifier.startswith("ORD") else "payment") or not isinstance(payload.get("data"), dict) or str(payload["data"].get("id")) != identifier:
            raise IdentityError("INVALID_EVENT", "Notificação inválida.")
        snapshot = client.payment(identifier)
        try:
            reference = UUID(snapshot.get("external_reference", ""))
        except (ValueError, TypeError, AttributeError):
            return Response({"received": True})
        order = Order.objects.filter(pk=reference, provider="mercadopago", environment=environment("mercadopago")).first()
        if order:
            client.validate_payment(order, snapshot, mercadopago.decode(order.subscription.encrypted_instrument))
            PaymentEvent.objects.get_or_create(digest=digest("mp-webhook:" + identifier + ":" + request.headers["x-request-id"]),
                defaults={"order": order, "provider_order_id": identifier, "available_at": timezone.now()})
        return Response({"received": True})



class SubscriptionView(IdentityView):
    def get(self, request):
        if request.user.role != "CLIENT":
            raise IdentityError("FORBIDDEN", "Disponível para associados.", 403)
        return Response(mercadopago.subscription_data(request.user))

    def post(self, request):
        if request.user.role != "CLIENT":
            raise IdentityError("FORBIDDEN", "Disponível para associados.", 403)
        if request.data != {"cancelRenewal": True}:
            raise IdentityError("INVALID_INPUT", "Confirme o cancelamento da próxima renovação.", 422)
        return Response(mercadopago.cancel_renewal(request.user))


class MobileSubscriptionView(MobileView):
    get = SubscriptionView.get
    post = SubscriptionView.post
