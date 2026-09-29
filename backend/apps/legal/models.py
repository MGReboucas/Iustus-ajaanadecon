import uuid
from django.db import models

class LegalWork(models.Model):
    case = models.OneToOneField("cases.Case", on_delete=models.PROTECT, related_name="legal_work")
    scope = models.TextField(blank=True)
    client_position = models.CharField(max_length=12, blank=True)
    process_number = models.CharField(max_length=100, blank=True)
    authority = models.CharField(max_length=200, blank=True)
    mandate = models.ForeignKey("documents.DocumentVersion", null=True, on_delete=models.PROTECT, related_name="mandate_work")
    signed_mandate = models.ForeignKey("documents.DocumentVersion", null=True, on_delete=models.PROTECT, related_name="signed_work")
    draft = models.TextField(blank=True)
    published_text = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True)
    protocol = models.CharField(max_length=200, blank=True)
    receipt = models.ForeignKey("documents.DocumentVersion", null=True, on_delete=models.PROTECT, related_name="protocol_work")
    updated_at = models.DateTimeField(auto_now=True)

class LegalTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="legal_tasks")
    kind = models.CharField(max_length=12, choices=[("DEADLINE", "Prazo"), ("HEARING", "Audiência"), ("STAGE", "Etapa")])
    title = models.CharField(max_length=200)
    due_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True)
    outcome = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
