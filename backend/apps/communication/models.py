import uuid

from django.conf import settings
from django.db import models


class Message(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Mensagem ao caso"
        INTERNAL = "INTERNAL", "Nota interna"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField()
    visibility = models.CharField(max_length=10, choices=Visibility.choices)
    client_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "author", "client_id"], name="message_retry_unique")]
        indexes = [models.Index(fields=["case", "visibility", "-created_at"])]


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT)
    source_key = models.CharField(max_length=80)
    kind = models.CharField(max_length=32)
    title = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["recipient", "source_key"], name="notification_source_unique")]
        indexes = [models.Index(fields=["recipient", "read_at", "-created_at"])]
