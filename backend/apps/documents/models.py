import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Document(models.Model):
    """Anexo compartilhado do caso. Minutas internas pertencem ao futuro módulo jurídico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="documents")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class DocumentVersion(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "UPLOADING", "Aguardando envio"
        QUARANTINED = "QUARANTINED", "Aguardando verificação"
        SCANNING = "SCANNING", "Em verificação"
        AVAILABLE = "AVAILABLE", "Disponível"
        REJECTED = "REJECTED", "Arquivo recusado"
        ERROR = "ERROR", "Verificação indisponível"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    filename = models.CharField(max_length=180)
    declared_mime = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    object_key = models.CharField(max_length=64, unique=True)
    sha256 = models.CharField(max_length=64, blank=True)
    detected_mime = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADING)
    uploaded_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    lease_id = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "number"], name="document_version_number_unique"),
            models.CheckConstraint(condition=models.Q(number__gte=1), name="document_version_positive"),
            models.CheckConstraint(condition=models.Q(size_bytes__gte=1, size_bytes__lte=20 * 1024 * 1024), name="document_size_limit"),
        ]
        indexes = [models.Index(fields=["status", "available_at"])]


class RequestAttachment(models.Model):
    request = models.ForeignKey("cases.InformationRequest", on_delete=models.PROTECT, related_name="attachments")
    version = models.ForeignKey(DocumentVersion, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "version"], name="request_attachment_unique")]
