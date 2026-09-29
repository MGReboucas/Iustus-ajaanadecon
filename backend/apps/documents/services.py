import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.db.models import Max
from django.http import Http404
from django.utils import timezone

from apps.cases.models import Case
from apps.cases.services import changed, expect_state, get_case
from apps.identity.security import IdentityError
from .models import Document, DocumentVersion
from integrations.storage.private import storage_configured


def version_data(item):
    return {"id": str(item.pk), "documentId": str(item.document_id), "number": item.number,
            "uploadedById": str(item.uploaded_by_id),
            "filename": item.filename, "sizeBytes": item.size_bytes, "status": item.status,
            "statusLabel": item.get_status_display(), "createdAt": item.created_at.isoformat()}


def get_version(user, version_id, *, locked=False):
    item = DocumentVersion.objects.select_related("document").filter(pk=version_id).first()
    if not item:
        raise Http404
    case = get_case(user, item.document.case_id, locked=locked)
    if locked:
        item = DocumentVersion.objects.select_for_update().get(pk=version_id)
    return case, item


def check_upload(case, item, user):
    expect_state(case, *[value for value in Case.State.values if value not in (Case.State.REJECTED, Case.State.CLOSED)])
    if item.uploaded_by_id != user.pk:
        raise Http404
    if item.status != DocumentVersion.Status.UPLOADING or item.expires_at <= timezone.now():
        raise IdentityError("UPLOAD_CLOSED", "Este envio foi concluído ou expirou. Inicie um novo envio.", 409)


def create_upload(case, user, data, document=None):
    expect_state(case, *[value for value in Case.State.values if value not in (Case.State.REJECTED, Case.State.CLOSED)])
    if not storage_configured():
        raise IdentityError("DOCUMENT_STORAGE_UNAVAILABLE", "O envio de documentos ainda não está disponível neste ambiente.", 503)
    filename = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "_", data["filename"]).strip(" .")
    suffixes = {"application/pdf": (".pdf",), "image/jpeg": (".jpg", ".jpeg"), "image/png": (".png",)}
    if not filename or not filename.lower().endswith(suffixes[data["mime"]]):
        raise IdentityError("INVALID_FILE", "Use um arquivo PDF, JPEG ou PNG com extensão compatível.", 422)
    if document:
        latest = document.versions.aggregate(number=Max("number"))["number"]
        if latest != data["previousVersion"]:
            raise IdentityError("VERSION_CONFLICT", "A lista de versões mudou. Atualize os documentos.", 409)
    else:
        document = Document.objects.create(case=case, created_by=user)
        latest = 0
    item = DocumentVersion.objects.create(document=document, number=latest + 1, uploaded_by=user,
        filename=filename, size_bytes=data["sizeBytes"], declared_mime=data["mime"], object_key=uuid.uuid4().hex,
        expires_at=timezone.now() + timedelta(minutes=30))
    changed(case, user, "DOCUMENT_UPLOAD_STARTED", "Envio de documento iniciado.", documentId=str(document.pk), versionId=str(item.pk))
    return {"directUpload": settings.DOCUMENT_DIRECT_UPLOAD_ENABLED, "uploadId": str(item.pk), "uploadUrl": f"/api/v1/uploads/{item.pk}/content",
            "expiresAt": item.expires_at.isoformat(), "version": version_data(item)}
