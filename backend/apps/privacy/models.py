import uuid
from django.db import models
class PrivacyRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey("identity.User", on_delete=models.PROTECT)
    kind = models.CharField(max_length=16, choices=[("ACCESS", "Acesso"), ("CORRECTION", "Correção"), ("DELETION", "Exclusão"), ("OTHER", "Outro")])
    description = models.TextField()
    status = models.CharField(max_length=16, default="OPEN")
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True)
    resolved_by = models.ForeignKey("identity.User", null=True, on_delete=models.PROTECT, related_name="privacy_resolutions")
