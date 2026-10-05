from django.db import transaction
from django.utils import timezone
from .models import Notification, CaseEmail


EVENT_TITLES = {
    "SUBMITTED": "Recebemos sua ocorrência para análise",
    "LEGAL_START": "Procuração disponível para assinatura",
    "LEGAL_SIGN": "Procuração devolvida para conferência",
    "LEGAL_RETURN_MANDATE": "A procuração precisa de um ajuste",
    "LEGAL_VERIFY": "Preparação do atendimento iniciada",
    "LEGAL_PUBLISH": "Uma peça está disponível no seu caso",
    "LEGAL_FILE": "Protocolo registrado no seu caso",
    "LEGAL_TASK": "Novo compromisso no seu caso",
    "LEGAL_RESCHEDULE": "Um compromisso foi remarcado",
    "LEGAL_COMPLETE": "Uma etapa do seu caso foi concluída",
    "LEGAL_UPDATE": "Nova movimentação no seu caso",
    "LEGAL_CLOSE": "Atendimento encerrado: consulte o resultado",
    "ASSIGNED": "Um caso foi atribuído a você",
    "TRIAGE_STARTED": "A triagem do seu caso começou",
    "TRIAGE_DECISION": "A triagem do seu caso foi concluída",
    "INFORMATION_REQUESTED": "Seu caso precisa de um complemento",
    "INFORMATION_RESPONDED": "O cliente respondeu ao complemento",
    "INFORMATION_RESOLVED": "O complemento do seu caso foi conferido",
}


def notify_event(event, item):
    title = EVENT_TITLES.get(event.action)
    if not title:
        return
    recipient_id = item.lawyer_id if event.action in ("ASSIGNED", "INFORMATION_RESPONDED", "LEGAL_SIGN") else item.owner_id
    if recipient_id and (recipient_id != event.actor_id or event.action == "SUBMITTED"):
        create_notice(recipient_id=recipient_id, source_key=f"event:{event.pk}", case=item, kind=event.action, title=title)


def visible_notifications(user):
    # Revalidar a atribuição também nos avisos antigos, inclusive na marcação de leitura.
    from apps.cases.services import accessible
    return Notification.objects.filter(recipient=user, case__in=accessible(user, administrative=user.role == "ADMIN"))


def notification_data(item):
    return {"id": str(item.pk), "caseId": str(item.case_id), "reference": str(item.case_id)[:8].upper(),
            "kind": item.kind, "title": item.title, "createdAt": item.created_at.isoformat(),
            "readAt": item.read_at.isoformat() if item.read_at else None}


def message_data(item):
    return {"id": str(item.pk), "text": item.text, "visibility": item.visibility,
            "authorId": str(item.author_id), "authorName": item.author.first_name,
            "createdAt": item.created_at.isoformat()}


@transaction.atomic
def create_notice(*, recipient_id, source_key, case, kind, title, task=None):
    notice, created = Notification.objects.get_or_create(recipient_id=recipient_id, source_key=source_key,
                                                       defaults={"case": case, "kind": kind, "title": title})
    if created:
        CaseEmail.objects.create(notification=notice, available_at=timezone.now(),
                                 reminder_task=task, reminder_due_at=task.due_at if task else None)
    return notice
