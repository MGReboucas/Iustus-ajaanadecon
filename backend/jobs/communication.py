import hashlib
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.cases.models import Case
from apps.cases.services import accessible
from apps.communication.models import CaseEmail
from apps.communication.services import create_notice
from apps.legal.models import LegalTask


def deliver_case_email():
    now, lease = timezone.now(), uuid.uuid4()
    with transaction.atomic():
        item = (CaseEmail.objects.select_for_update(skip_locked=True)
                .filter(sent_at__isnull=True, cancelled_at__isnull=True, available_at__lte=now, attempts__lt=5)
                .filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now)).order_by("created_at").first())
        if not item:
            return False
        item.lease_id, item.lease_until = lease, now+timedelta(minutes=5)
        item.attempts += 1
        item.save(update_fields=["lease_id", "lease_until", "attempts"])
    notice = item.notification
    user = notice.recipient
    # Nenhuma mensagem é enviada após revogação conhecida ou opt-out.
    portal = "client" if user.role == "CLIENT" else "team"
    allowed = portal in settings.PORTAL_ORIGINS and user.is_active and user.email_verified_at and user.case_email_enabled and accessible(user).filter(pk=notice.case_id).exists()
    if notice.kind == "TASK_REMINDER":
        allowed = allowed and LegalTask.objects.filter(pk=item.reminder_task_id, case_id=notice.case_id, due_at=item.reminder_due_at, completed_at__isnull=True,
            due_at__lte=timezone.now()+timedelta(hours=24)).exclude(case__state__in=[Case.State.CLOSED, Case.State.REJECTED]).exists()
    if not allowed:
        CaseEmail.objects.filter(pk=item.pk, lease_id=lease).update(cancelled_at=timezone.now(), lease_id=None, lease_until=None)
        return True
    portal = "client" if user.role == "CLIENT" else "team"
    path = "/cliente" if portal == "client" else "/advogado"
    url = settings.PORTAL_ORIGINS[portal] + path
    body = "Há uma novidade ou pendência no seu atendimento Iustus.\n\nEntre no painel para consultar os detalhes com segurança:\n" + url + "\n\nVocê pode ajustar estes e-mails em Minha conta."
    try:
        message = EmailMessage("Iustus: atualização no atendimento", body, None, [user.email],
                               headers={"Message-ID": f"<case-{notice.pk}@iustus.invalid>"})
        if message.send(fail_silently=False) != 1:
            raise RuntimeError("MailNotAccepted")
    except Exception as exc:
        CaseEmail.objects.filter(pk=item.pk, lease_id=lease).update(lease_id=None, lease_until=None,
            last_error=type(exc).__name__[:40], available_at=timezone.now()+timedelta(seconds=min(3600,30*2**item.attempts)))
    else:
        CaseEmail.objects.filter(pk=item.pk, lease_id=lease).update(sent_at=timezone.now(), lease_id=None, lease_until=None, last_error="")
    return True


def schedule_reminders():
    now = timezone.now()
    # Uma notificação por compromisso, data e destinatário. Remarcação cria uma nova chave.
    candidates = LegalTask.objects.filter(completed_at__isnull=True, due_at__lte=now+timedelta(hours=24)).exclude(
        case__state__in=[Case.State.CLOSED, Case.State.REJECTED]).values_list("pk", "case_id")
    count = 0
    for task_id, case_id in candidates.iterator(chunk_size=200):
        with transaction.atomic():
            case = Case.objects.select_for_update().get(pk=case_id)
            task = LegalTask.objects.filter(pk=task_id, completed_at__isnull=True, due_at__lte=now+timedelta(hours=24)).first()
            if not task or case.state in (Case.State.CLOSED, Case.State.REJECTED):
                continue
            fingerprint = hashlib.sha256(f"{task.pk}:{task.due_at.isoformat()}".encode()).hexdigest()[:32]
            recipients = [case.lawyer_id] if task.kind == "DEADLINE" else [case.lawyer_id, case.owner_id]
            for recipient in filter(None, recipients):
                create_notice(recipient_id=recipient, source_key=f"task:{fingerprint}", case=case,
                              task=task, kind="TASK_REMINDER", title="Um compromisso do seu caso precisa de atenção")
                count += 1
    return count
