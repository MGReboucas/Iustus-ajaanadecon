from django.db import transaction
from django.utils import timezone
from .models import Notification, CaseEmail


EVENT_TITLES = {
    "DRAFT_CREATED": "Rascunho da ocorrência criado",
    "DRAFT_UPDATED": "Rascunho da ocorrência atualizado",
    "DOCUMENT_UPLOAD_STARTED": "Envio de documento iniciado no seu caso",
    "DOCUMENT_QUARANTINED": "Documento recebido e aguardando verificação",
    "DOCUMENT_DEMO_RECEIVED": "Documento de demonstração recebido sem verificação",
    "DOCUMENT_AVAILABLE": "Documento verificado e disponível no seu caso",
    "DOCUMENT_REJECTED": "Um documento foi recusado: confira o envio",
    "DOCUMENT_REMOVED": "Documento removido do rascunho",
    "MANDATE_GENERATED": "Procuração gerada no seu caso",
    "LEGAL_DRAFT": "Minuta interna do caso atualizada",
    "INTERNAL_MESSAGE": "Nota interna registrada no caso",
    "LAWYER_CHANGED": "O advogado responsável pelo seu caso foi atualizado",
    "MESSAGE": "Você recebeu uma nova mensagem no seu atendimento",
    "TASK_REMINDER": "Lembrete: há um compromisso do seu caso nas próximas 24 horas ou pendente",
    "TASK_OVERDUE": "Um compromisso do seu caso está atrasado e precisa de atenção",
    "UNASSIGNED": "Nova ocorrência aguardando advogado responsável",
    "PROPOSAL_PUBLISHED": "Uma proposta de atendimento está disponível",
    "PROPOSAL_ACCEPTED": "O cliente aceitou a proposta de atendimento",
    "PROPOSAL_DECLINED": "O cliente recusou a proposta de atendimento",
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


# Only milestones and communications in the actual case handling trigger email.
# Technical events remain in the timeline/dashboard, without email delivery.
CASE_EMAIL_KINDS = frozenset({
    "SUBMITTED", "ASSIGNED", "LAWYER_CHANGED", "UNASSIGNED", "MESSAGE",
    "TRIAGE_STARTED", "TRIAGE_DECISION", "INFORMATION_REQUESTED",
    "INFORMATION_RESPONDED", "INFORMATION_RESOLVED", "PROPOSAL_PUBLISHED",
    "PROPOSAL_ACCEPTED", "PROPOSAL_DECLINED", "LEGAL_START", "LEGAL_SIGN",
    "LEGAL_RETURN_MANDATE", "LEGAL_VERIFY", "LEGAL_PUBLISH", "LEGAL_FILE",
    "LEGAL_TASK", "LEGAL_RESCHEDULE", "LEGAL_COMPLETE", "LEGAL_UPDATE",
    "LEGAL_CLOSE", "TASK_REMINDER", "TASK_OVERDUE",
})


def notify_event(event, item):
    title = EVENT_TITLES.get(event.action, "Nova movimentação registrada no seu caso")
    if event.action == "ASSIGNED":
        recipients = [item.lawyer_id]
        create_notice(recipient_id=item.owner_id, source_key=f"assignment:{event.pk}", case=item,
                      kind="LAWYER_CHANGED", title=EVENT_TITLES["LAWYER_CHANGED"])
    elif not event.public:
        recipients = [item.lawyer_id]
    elif item.state == "RASCUNHO" or event.action.startswith("DRAFT_"):
        recipients = [item.owner_id]
    elif event.action.startswith("DOCUMENT_"):
        # The uploader also needs the asynchronous validation result.
        recipients = [item.owner_id, item.lawyer_id]
    elif event.action in ("INFORMATION_RESPONDED", "LEGAL_SIGN", "PROPOSAL_ACCEPTED", "PROPOSAL_DECLINED"):
        recipients = [item.lawyer_id]
    else:
        recipient_id = item.owner_id
        if event.actor_id == item.owner_id and event.action != "SUBMITTED":
            recipient_id = item.lawyer_id or item.owner_id
        recipients = [recipient_id]
    for recipient_id in set(filter(None, recipients)):
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
    if created and kind in CASE_EMAIL_KINDS:
        CaseEmail.objects.create(notification=notice, available_at=timezone.now(),
                                 reminder_task=task, reminder_due_at=task.due_at if task else None)
    return notice
