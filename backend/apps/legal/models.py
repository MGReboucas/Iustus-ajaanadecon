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


class MandateTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey("identity.User", on_delete=models.PROTECT)
    family = models.UUIDField(default=uuid.uuid4)
    number = models.PositiveIntegerField()
    name = models.CharField(max_length=160)
    body = models.TextField()
    sha256 = models.CharField(max_length=64)
    approved_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["family", "number"], name="mandate_template_version_unique")]


class GeneratedMandate(models.Model):
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="generated_mandates")
    template = models.ForeignKey(MandateTemplate, on_delete=models.PROTECT)
    version = models.OneToOneField("documents.DocumentVersion", on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    fields = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "number"], name="mandate_generation_number_unique")]


class CaseExport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT)
    requested_by = models.ForeignKey("identity.User", on_delete=models.PROTECT)
    case_version = models.PositiveIntegerField()
    object_key = models.CharField(max_length=32, unique=True)
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    purged_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ServiceProposal(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey("cases.Case", on_delete=models.PROTECT, related_name="service_proposals")
    number = models.PositiveIntegerField()
    author = models.ForeignKey("identity.User", on_delete=models.PROTECT, related_name="authored_proposals")
    scope = models.TextField()
    fee_cents = models.PositiveBigIntegerField()
    expenses = models.TextField()
    payment_terms = models.TextField()
    valid_until = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    decided_by = models.ForeignKey("identity.User", null=True, on_delete=models.PROTECT, related_name="decided_proposals")
    decided_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["case", "number"], name="proposal_case_number_unique"),
            models.UniqueConstraint(fields=["case"], condition=models.Q(status="OPEN"), name="proposal_one_open_per_case"),
            models.CheckConstraint(condition=models.Q(number__gte=1), name="proposal_positive_number"),
            models.CheckConstraint(condition=(
                models.Q(status__in=["OPEN", "SUPERSEDED"], decided_by__isnull=True, decided_at__isnull=True)
                | models.Q(status__in=["ACCEPTED", "DECLINED"], decided_by__isnull=False, decided_at__isnull=False)
            ), name="proposal_decision_consistent"),
        ]
