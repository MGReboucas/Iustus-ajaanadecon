import uuid
from django.conf import settings
from django.db import models


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_key = models.CharField(max_length=64, unique=True)
    session_digest = models.CharField(max_length=64)
    amount = models.PositiveIntegerField()
    installments = models.PositiveSmallIntegerField(default=12)
    plan_version = models.CharField(max_length=80, default="annual-legacy-v1")
    provider = models.CharField(max_length=20, default="pagbank")
    subscription = models.ForeignKey("Subscription", null=True, on_delete=models.PROTECT)
    cycle = models.PositiveIntegerField(default=0)
    encrypted_payment_payload = models.TextField(blank=True)
    payment_started_at = models.DateTimeField(null=True)
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
    # Identidade do comprador protegida; nunca armazenar PAN, CVV ou cartão criptografado.
    encrypted_customer = models.TextField(blank=True)
    payload_digest = models.CharField(max_length=64, blank=True)


class Membership(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)


class BillingIdentity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    environment = models.CharField(max_length=12)
    cpf_digest = models.CharField(max_length=64)
    encrypted_cpf = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["environment", "cpf_digest"], name="billing_unique_cpf"),
            models.UniqueConstraint(fields=["environment", "user"], name="billing_unique_user"),
        ]


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


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    environment = models.CharField(max_length=12)
    buyer_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=24, default="PENDING")
    amount = models.PositiveIntegerField()
    installments = models.PositiveSmallIntegerField()
    plan_version = models.CharField(max_length=80)
    policy_version = models.CharField(max_length=80)
    accepted_at = models.DateTimeField(auto_now_add=True)
    canceled_at = models.DateTimeField(null=True)
    next_charge_at = models.DateTimeField(null=True)
    encrypted_customer = models.TextField()
    # Apenas referências do cofre MP; nunca PAN/CVV. Protegidas em repouso.
    encrypted_instrument = models.TextField(blank=True)
    last_cycle = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["environment", "buyer_digest"],
            condition=models.Q(status__in=["PENDING", "ACTIVE", "PAST_DUE", "REVIEW"]),
            name="billing_one_live_subscription")]
