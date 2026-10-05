import uuid

from django.conf import settings
from django.db import models


class Case(models.Model):
    class Category(models.TextChoices):
        TRAFFIC = "TRAFFIC", "Multas de trânsito"
        CONTRACTS = "CONTRACTS", "Contratos civis"
        COLLECTION = "COLLECTION", "Cobranças e dívidas"
        LIABILITY = "LIABILITY", "Responsabilidade civil"
        CONSUMER = "CONSUMER", "Relações de consumo"
        PROPERTY = "PROPERTY", "Imobiliário, posse e propriedade"
        CIVIL_OTHER = "CIVIL_OTHER", "Demais matérias civis"

    class State(models.TextChoices):
        DRAFT = "RASCUNHO", "Rascunho"
        SUBMITTED = "SUBMETIDO", "Enviado para distribuição"
        TRIAGE = "EM_TRIAGEM", "Em triagem"
        WAITING = "AGUARDANDO_CLIENTE", "Aguardando complemento"
        ACCEPTED = "ACEITO", "Aceito na triagem"
        REJECTED = "RECUSADO", "Recusado"
        MANDATE = "AGUARDANDO_PROCURACAO", "Aguardando procuração"
        PREPARING = "EM_PREPARACAO", "Em preparação"
        TRACKING = "EM_ACOMPANHAMENTO", "Em acompanhamento"
        CLOSED = "ENCERRADO", "Encerrado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_cases")
    lawyer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="assigned_cases")
    title = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    occurred_on = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    scope_acknowledged = models.BooleanField(default=False)
    state = models.CharField(max_length=24, choices=State.choices, default=State.DRAFT)
    version = models.PositiveIntegerField(default=1)
    submission_key = models.CharField(max_length=64, blank=True)
    submission_version = models.PositiveIntegerField(null=True)
    submitted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "-created_at"]), models.Index(fields=["lawyer", "state"])]
        constraints = [models.CheckConstraint(condition=models.Q(version__gte=1), name="case_positive_version")]


class CaseEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    state = models.CharField(max_length=24)
    version = models.PositiveIntegerField()
    # Motivo administrativo é privado; decisões e solicitações são públicas ao titular.
    public = models.BooleanField(default=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "version"], name="case_event_version_unique")]


class InformationRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.PROTECT, related_name="information_requests")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    description = models.TextField()
    response = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)


class LocalCaseAccess(models.Model):
    """Liberação de testes; nunca representa assinatura ou pagamento confirmado."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=240)
    updated_at = models.DateTimeField(auto_now=True)


class ServiceAccess(models.Model):
    """Autorização administrativa de atendimento, independente de pagamento."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_grants")
    enabled = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=240)
    updated_at = models.DateTimeField(auto_now=True)
