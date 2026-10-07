"""Validação e vínculo do comprador do checkout transparente."""
import hashlib
import hmac
import json
import re
from django.conf import settings
from django.db.models import Q
from rest_framework import serializers
from apps.identity.models import User
from apps.identity.security import IdentityError
from apps.identity.serializers import StrictSerializer
from .models import BillingIdentity


def fingerprint(value):
    return hmac.new(settings.IDENTITY_ENCRYPTION_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cpf(value):
    value = re.sub(r"[.\s-]", "", value)
    if not re.fullmatch(r"[0-9]{11}", value) or len(set(value)) == 1:
        raise serializers.ValidationError("Informe um CPF válido.")
    for size in (9, 10):
        digit = (sum(int(value[i]) * (size + 1 - i) for i in range(size)) * 10 % 11) % 10
        if int(value[size]) != digit:
            raise serializers.ValidationError("Informe um CPF válido.")
    return value


class CustomerInput(StrictSerializer):
    name = serializers.CharField(min_length=3, max_length=120)
    email = serializers.EmailField(max_length=254)
    cpf = serializers.CharField(max_length=18)
    phone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_cpf(self, value):
        return cpf(value)

    def validate_phone(self, value):
        value = re.sub(r"[()\s-]", "", value)
        if not re.fullmatch(r"[1-9][0-9]9[0-9]{8}", value):
            raise serializers.ValidationError("Informe o celular com DDD, com 11 dígitos.")
        return value


class CardInput(StrictSerializer):
    encrypted = serializers.RegexField(r"^[A-Za-z0-9+/=]+$", min_length=100, max_length=4096, trim_whitespace=False)
    holderName = serializers.CharField(min_length=3, max_length=120)
    holderCpf = serializers.CharField(max_length=18)

    def validate_holderCpf(self, value):
        return cpf(value)


class CheckoutInput(StrictSerializer):
    accepted = serializers.BooleanField()
    customer = CustomerInput()
    card = CardInput()


def check_identity(customer, environment):
    """Não permitir trocar o e-mail/CPF de uma identidade já vinculada."""
    cpf_digest = fingerprint("cpf:" + customer["cpf"])
    rows = BillingIdentity.objects.filter(environment=environment).filter(
        Q(cpf_digest=cpf_digest) | Q(user__email=customer["email"]))
    if any(row.cpf_digest != cpf_digest or row.user.email != customer["email"] for row in rows.select_related("user")):
        raise IdentityError("BUYER_REVIEW_REQUIRED", "Confira o e-mail e CPF do associado. Se já possui cadastro, use os mesmos dados ou entre em contato com a associação.", 422)
    user = User.objects.filter(email=customer["email"]).first()
    if user and (user.role != "CLIENT" or not user.is_active):
        raise IdentityError("BUYER_REVIEW_REQUIRED", "O cadastro precisa de conferência pela associação.", 422)
    return cpf_digest
