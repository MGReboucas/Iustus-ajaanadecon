from django.conf import settings
from django.http import Http404
from django.utils import timezone

from apps.identity.models import User
from apps.identity.security import IdentityError
from .models import Case, CaseEvent, LocalCaseAccess, ServiceAccess


def accessible(user, administrative=False):
    query = Case.objects.all()
    if user.role == User.Role.CLIENT:
        return query.filter(owner=user)
    if user.role == User.Role.LAWYER:
        return query.filter(lawyer=user).exclude(state=Case.State.DRAFT)
    if user.role == User.Role.ADMIN and administrative:
        return query.exclude(state=Case.State.DRAFT)
    return query.none()


def get_case(user, case_id, *, locked=False, administrative=False):
    query = accessible(user, administrative)
    if locked:
        query = query.select_for_update()
    item = query.filter(pk=case_id).first()
    if not item:
        raise Http404
    return item


def expect_version(item, value):
    if item.version != value:
        raise IdentityError("VERSION_CONFLICT", "O caso foi atualizado. Reabra os dados antes de tentar novamente.", 409)


def expect_state(item, *states):
    if item.state not in states:
        raise IdentityError("INVALID_TRANSITION", "Esta ação não está disponível no estado atual do caso.", 409)


def record(item, user, action, reason="", public=True, **metadata):
    from apps.communication.services import notify_event
    event = CaseEvent.objects.create(case=item, actor=user, action=action, state=item.state,
                             version=item.version, reason=reason, public=public, metadata=metadata)
    notify_event(event, item)


def changed(item, user, action, reason="", public=True, **metadata):
    item.version += 1
    item.save()
    record(item, user, action, reason, public, **metadata)


def edit_draft(item, data):
    if "occurredOn" in data:
        item.occurred_on = data["occurredOn"]
    for name in ("title", "description", "category"):
        if name in data:
            setattr(item, name, data[name])
    if "scopeAcknowledged" in data:
        item.scope_acknowledged = data["scopeAcknowledged"]


def submission_access(user):
    from apps.billing.services import membership_data
    membership = membership_data(user)
    if membership["active"]:
        return {"canSubmit": True, "mode": "MEMBERSHIP", "expiresAt": membership["expiresAt"], "message": "Associação ativa. Cadastre uma ocorrência para análise dos advogados."}
    if settings.MEMBERSHIP_REQUIRED:
        return {"canSubmit": False, "mode": "INACTIVE", "message": "É necessário ter uma associação ativa para enviar novas ocorrências. Seus casos anteriores continuam disponíveis."}
    if ServiceAccess.objects.filter(user=user, enabled=True, expires_at__gt=timezone.now()).exists():
        return {"canSubmit": True, "mode": "ADMINISTRATIVE", "message": "Atendimento liberado pelo escritório. Você pode enviar seu caso para triagem."}
    # Fail closed. Futuro adaptador financeiro deve substituir esta capacidade explícita.
    allowed = bool(settings.CASE_LOCAL_TEST_ACCESS and LocalCaseAccess.objects.filter(
        user=user, expires_at__gt=timezone.now()).exists())
    return {"canSubmit": allowed, "mode": "LOCAL_TEST" if settings.CASE_LOCAL_TEST_ACCESS else "UNAVAILABLE",
            "message": "Liberação local de testes ativa; não representa assinatura." if allowed else
            "Aguarde a liberação de atendimento pelo escritório. Você pode salvar rascunhos."}


def case_data(item, *, administrative=False, detail=False):
    result = {"id": str(item.pk), "reference": str(item.pk)[:8].upper(), "category": item.category,
              "categoryLabel": item.get_category_display(), "state": item.state, "stateLabel": item.get_state_display(),
              "version": item.version, "lawyerId": str(item.lawyer_id) if item.lawyer_id else None,
              "createdAt": item.created_at.isoformat(), "submittedAt": item.submitted_at.isoformat() if item.submitted_at else None}
    if not administrative:
        result["title"] = item.title
        if detail:
            result.update(description=item.description, scopeAcknowledged=item.scope_acknowledged,
                          occurredOn=item.occurred_on.isoformat() if item.occurred_on else None)
    return result


def assign_automatically(item):
    """Chamado na transação de submissão. Locks ordenados serializam a distribuição."""
    from django.db.models import Count
    eligible = User.objects.filter(role="LAWYER", is_active=True, email_verified_at__isnull=False)
    if settings.IDENTITY_MFA_REQUIRED:
        eligible = eligible.filter(mfadevice__confirmed_at__isnull=False)
    lawyers = list(eligible.order_by("pk").select_for_update(of=("self",)))
    if not lawyers:
        return False
    counts = dict(Case.objects.filter(lawyer__in=lawyers).exclude(state__in=[Case.State.CLOSED, Case.State.REJECTED]).values("lawyer_id").annotate(total=Count("id")).values_list("lawyer_id", "total"))
    item.lawyer = min(lawyers, key=lambda lawyer: (counts.get(lawyer.pk, 0), str(lawyer.pk)))
    changed(item, item.owner, "ASSIGNED", "Distribuição automática pela associação.", public=False, lawyerId=str(item.lawyer_id))
    return True
