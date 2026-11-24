import uuid
from datetime import timedelta

from django.db import transaction
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.cases.models import Case
from apps.cases.services import changed
from apps.documents.models import DocumentVersion
from integrations.scanner.clamav import scan
from integrations.scanner.guardduty import verdict
from integrations.storage.private import InvalidFile, inspect_file, open_object, delete_object


def purge_removed_one(*, case_id=None):
    """Retry deletion after signed PUTs have expired, including late uploads."""
    with transaction.atomic():
        query = DocumentVersion.objects.select_for_update(skip_locked=True).filter(
            status="REMOVED", last_error="REMOVAL_PENDING", available_at__lte=timezone.now())
        if case_id is not None:
            query = query.filter(document__case_id=case_id)
        item = query.order_by("available_at").first()
        if not item:
            return False
        try:
            delete_object(item.object_key)
        except Exception:
            item.available_at = timezone.now() + timedelta(minutes=5)
            item.save(update_fields=["available_at"])
            return False
        item.last_error = ""
        item.save(update_fields=["last_error"])
        return True


def scan_one(*, case_id=None):
    guardduty = settings.DOCUMENT_SCANNER_BACKEND == "guardduty"
    now, lease = timezone.now(), uuid.uuid4()
    with transaction.atomic():
        query = DocumentVersion.objects.select_for_update(skip_locked=True)
        if case_id is not None:
            query = query.filter(document__case_id=case_id)
        errors = Q(status="ERROR") if guardduty else Q(status="ERROR", attempts__lt=5)
        item = (query
                .filter(Q(status="QUARANTINED") | errors |
                        Q(status="SCANNING", lease_until__lt=now))
                .filter(available_at__lte=now).order_by("available_at", "created_at").first())
        if not item:
            return False
        if item.attempts >= 5 and not guardduty:
            item.status, item.last_error = "ERROR", "ATTEMPTS_EXHAUSTED"
            item.lease_id = item.lease_until = None
            item.save(update_fields=["status", "last_error", "lease_id", "lease_until"])
            return True
        item.status, item.lease_id = "SCANNING", lease
        item.lease_until = now + timedelta(minutes=5)
        item.attempts = min(item.attempts + 1, 1000)
        item.save(update_fields=["status", "lease_id", "lease_until", "attempts"])
    status, error = "ERROR", ""
    try:
        if guardduty:
            status, error = verdict(item.object_key)
        if not guardduty or status == "AVAILABLE":
            checksum, mime = inspect_file(item.object_key, item.size_bytes)
            if checksum != item.sha256 or mime != item.detected_mime:
                raise InvalidFile("integrity")
            if not guardduty:
                with open_object(item.object_key) as source:
                    status = "AVAILABLE" if scan(source) else "REJECTED"
    except (InvalidFile, FileNotFoundError):
        status, error = "REJECTED", "INTEGRITY_FAILED"
    except Exception as exc:
        # Não persistir nomes/conteúdos nem a resposta livre do scanner em logs.
        status, error = "ERROR", type(exc).__name__[:40]
    with transaction.atomic():
        # Mesma ordem das mutações da API: caso, depois versão.
        case = Case.objects.select_for_update().get(pk=item.document.case_id)
        current = DocumentVersion.objects.select_for_update().get(pk=item.pk)
        if current.lease_id != lease:
            return True
        current.status, current.last_error = status, error
        current.lease_id = current.lease_until = None
        delay = (15 if status == "QUARANTINED" else 60) if guardduty else min(3600, 30 * 2 ** min(current.attempts, 7))
        current.available_at = timezone.now() + timedelta(seconds=delay)
        if status in ("AVAILABLE", "REJECTED"):
            current.scanned_at = timezone.now()
            changed(case, current.uploaded_by, "DOCUMENT_" + status,
                    "Documento liberado após verificação." if status == "AVAILABLE" else "Documento recusado na verificação.",
                    versionId=str(current.pk), source="scanner")
        current.save(update_fields=["status", "last_error", "lease_id", "lease_until", "available_at", "scanned_at"])
    return True
