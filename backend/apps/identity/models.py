import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email or not email.strip():
            raise ValueError("E-mail obrigatório.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superusuário exige is_staff e is_superuser.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Identidade; role é a fonte de papel do produto, independente do Django Admin."""

    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Cliente"
        LAWYER = "LAWYER", "Advogado"
        ADMIN = "ADMIN", "Administrador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    auth_version = models.PositiveIntegerField(default=1)
    case_email_enabled = models.BooleanField(default=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CLIENT)
    accepted_policy_version = models.CharField(max_length=80, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="identity_user_email_ci_unique")
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class ActionToken(models.Model):
    class Purpose(models.TextChoices):
        VERIFY = "VERIFY"
        RESET = "RESET"
        INVITE = "INVITE"

    digest = models.CharField(max_length=64, primary_key=True)
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    email = models.EmailField()
    portal = models.CharField(max_length=10)
    auth_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="issued_tokens")
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MFADevice(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    encrypted_secret = models.TextField()
    confirmed_at = models.DateTimeField(null=True)
    last_counter = models.BigIntegerField(default=-1)
    recovery_hashes = models.JSONField(default=list)


class RateLimitBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


class IdentityEmail(models.Model):
    """Fila durável de identidade. Corpo criptografado; lease permite retomada."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.EmailField()
    subject = models.CharField(max_length=160)
    encrypted_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    available_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True)
    lease_id = models.UUIDField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=40, blank=True)


class IdentityAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    portal = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    # Apenas códigos/versões. Nunca senha, token, OTP, segredo ou corpo de e-mail.
    metadata = models.JSONField(default=dict)
