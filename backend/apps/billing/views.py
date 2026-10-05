import hashlib
import json
import re
from uuid import UUID
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.identity.models import User
from apps.identity.views import PublicView
from apps.identity.serializers import StrictSerializer, AcceptInviteSerializer, EmailSerializer
from apps.identity.services import locked_token, consume, validate_new_password, audit
from apps.identity.security import IdentityError, digest
from integrations.pagbank.client import create_checkout, verify_signature
from .models import Order, PaymentEvent
from .services import active_memberships, send_access


class CheckoutInput(StrictSerializer):
    accepted = serializers.BooleanField()


class PlanView(PublicView):
    def get(self, request):
        return Response({"amount": settings.MEMBERSHIP_PRICE_CENTS, "available": settings.BILLING_ENABLED,
            "sandbox": settings.PAGBANK_ENVIRONMENT == "sandbox", "policyVersion": settings.REGISTRATION_POLICY_VERSION})


class CheckoutView(PublicView):
    def post(self, request):
        self.public_limit(request, "checkout", limit=20)
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
        # Persistir a referência antes da chamada externa para repetir com a mesma chave.
        order, _ = Order.objects.get_or_create(request_key=digest(session_digest + key), defaults={
            "session_digest": session_digest, "amount": settings.MEMBERSHIP_PRICE_CENTS,
            "environment": settings.PAGBANK_ENVIRONMENT, "policy_version": settings.REGISTRATION_POLICY_VERSION})
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if not order.checkout_id:
                order.checkout_id, order.payment_url = create_checkout(order)
                order.status = "WAITING"
                order.save()
        request.session["checkout_order"] = str(order.pk)
        return Response({"paymentUrl": order.payment_url, "status": order.status}, status=201)

    def get(self, request):
        order = Order.objects.filter(pk=request.session.get("checkout_order")).first()
        if not order or order.session_digest != digest(request.session.session_key or ""):
            raise Http404
        return Response({"status": order.status})


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
