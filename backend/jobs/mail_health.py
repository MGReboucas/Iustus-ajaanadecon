import logging
import os
import socket
from datetime import timedelta

from django.utils import timezone
from apps.identity.models import IdentityEmail, MailWorkerHeartbeat
from apps.communication.models import CaseEmail


def update_mail_health():
    now = timezone.now()
    MailWorkerHeartbeat.objects.update_or_create(name=f"{socket.gethostname()}:{os.getpid()}"[:80], defaults={"updated_at": now})
    MailWorkerHeartbeat.objects.filter(updated_at__lt=now - timedelta(days=7)).delete()
    for name, model in (("identity", IdentityEmail), ("case", CaseEmail)):
        query = model.objects.filter(sent_at__isnull=True, cancelled_at__isnull=True)
        exhausted = query.filter(attempts__gte=5).count()
        stale = query.filter(available_at__lt=now - timedelta(minutes=15)).count()
        if exhausted or stale:
            logging.getLogger("jobs.mail").error("Mail queue unhealthy: queue=%s exhausted=%s delayed=%s", name, exhausted, stale)
