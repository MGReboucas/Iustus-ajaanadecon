from django.conf import settings
from django.http import Http404
from django.utils import timezone

from apps.identity.models import User
from apps.identity.security import IdentityError
from .models import Case, CaseEvent, LocalCaseAccess


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
    for name in ("title", "description", "category"):
        if name in data:
            setattr(item, name, data[name])
    if "scopeAcknowledged" in data:
        item.scope_acknowledged = data["scopeAcknowledged"]


def submission_access(user):
    # Fail closed. Futuro adaptador financeiro deve substituir esta capacidade explícita.
    allowed = bool(settings.CASE_LOCAL_TEST_ACCESS and LocalCaseAccess.objects.filter(
        user=user, expires_at__gt=timezone.now()).exists())
    return {"canSubmit": allowed, "mode": "LOCAL_TEST" if settings.CASE_LOCAL_TEST_ACCESS else "UNAVAILABLE",
            "message": "Liberação local de testes ativa; não representa assinatura." if allowed else
            "Envio indisponível: a assinatura ainda não está integrada. Você pode salvar rascunhos."}


def case_data(item, *, administrative=False, detail=False):
    result = {"id": str(item.pk), "reference": str(item.pk)[:8].upper(), "category": item.category,
              "categoryLabel": item.get_category_display(), "state": item.state, "stateLabel": item.get_state_display(),
              "version": item.version, "lawyerId": str(item.lawyer_id) if item.lawyer_id else None,
              "createdAt": item.created_at.isoformat(), "submittedAt": item.submitted_at.isoformat() if item.submitted_at else None}
    if not administrative:
        result["title"] = item.title
        if detail:
            result.update(description=item.description, scopeAcknowledged=item.scope_acknowledged)
    return result
