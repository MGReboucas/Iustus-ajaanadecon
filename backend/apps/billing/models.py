import uuid
from django.conf import settings
from django.db import models


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_key = models.CharField(max_length=64, unique=True)
    session_digest = models.CharField(max_length=64)
    amount = models.PositiveIntegerField()
    environment = models.CharField(max_length=12)
    policy_version = models.CharField(max_length=80)
    status = models.CharField(max_length=24, default="CREATING")
    checkout_id = models.CharField(max_length=80, null=True, unique=True)
    payment_url = models.URLField(max_length=1000, blank=True)
    provider_order_id = models.CharField(max_length=80, null=True, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True)
    checked_at = models.DateTimeField(null=True)


class Membership(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)


class PaymentEvent(models.Model):
    # Apenas identificadores autenticados; não persistir o payload financeiro/PII.
    digest = models.CharField(max_length=64, primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    provider_order_id = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    available_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=40, blank=True)
    lease_id = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
