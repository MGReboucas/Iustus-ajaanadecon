import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.cases.models import Case
from apps.cases.services import changed
from apps.documents.models import DocumentVersion
from integrations.scanner.clamav import scan
from integrations.storage.private import InvalidFile, inspect_file, open_object


def scan_one():
    now, lease = timezone.now(), uuid.uuid4()
    with transaction.atomic():
        item = (DocumentVersion.objects.select_for_update(skip_locked=True)
                .filter(Q(status="QUARANTINED") | Q(status="ERROR", attempts__lt=5) |
                        Q(status="SCANNING", lease_until__lt=now))
                .filter(available_at__lte=now).order_by("created_at").first())
        if not item:
            return False
        if item.attempts >= 5:
            item.status, item.last_error = "ERROR", "ATTEMPTS_EXHAUSTED"
            item.lease_id = item.lease_until = None
            item.save(update_fields=["status", "last_error", "lease_id", "lease_until"])
            return True
        item.status, item.lease_id = "SCANNING", lease
        item.lease_until = now + timedelta(minutes=5)
        item.attempts += 1
        item.save(update_fields=["status", "lease_id", "lease_until", "attempts"])
    status, error = "ERROR", ""
    try:
        checksum, mime = inspect_file(item.object_key, item.size_bytes)
        if checksum != item.sha256 or mime != item.detected_mime:
            raise InvalidFile("integrity")
        with open_object(item.object_key) as source:
            status = "AVAILABLE" if scan(source) else "REJECTED"
    except (InvalidFile, FileNotFoundError):
        status, error = "REJECTED", "INTEGRITY_FAILED"
    except Exception as exc:
        # Não persistir nomes/conteúdos nem a resposta livre do scanner em logs.
        error = type(exc).__name__[:40]
    with transaction.atomic():
        # Mesma ordem das mutações da API: caso, depois versão.
        case = Case.objects.select_for_update().get(pk=item.document.case_id)
        current = DocumentVersion.objects.select_for_update().get(pk=item.pk)
        if current.lease_id != lease:
            return True
        current.status, current.last_error = status, error
        current.lease_id = current.lease_until = None
        current.available_at = timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** current.attempts))
        if status in ("AVAILABLE", "REJECTED"):
            current.scanned_at = timezone.now()
            changed(case, current.uploaded_by, "DOCUMENT_" + status,
                    "Documento liberado após verificação." if status == "AVAILABLE" else "Documento recusado na verificação.",
                    versionId=str(current.pk), source="scanner")
        current.save(update_fields=["status", "last_error", "lease_id", "lease_until", "available_at", "scanned_at"])
    return True
