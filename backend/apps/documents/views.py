from django.core import signing
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.response import Response

from apps.cases.services import changed, get_case
from apps.cases.views import CaseView
from apps.identity.security import IdentityError, digest
from apps.identity.services import audit
from integrations.storage.private import InvalidFile, inspect_file, object_path, write_stream
from . import serializers as inputs
from .models import Document, DocumentVersion
from .services import check_upload, create_upload, get_version, version_data


class DocumentsView(CaseView):
    def get(self, request, case_id):
        case = get_case(request.user, case_id)
        return self.listed(request, DocumentVersion.objects.filter(document__case=case), version_data)

    def post(self, request, case_id):
        self.limited(request)
        data = self.data(request, inputs.UploadInput)
        with transaction.atomic():
            case = get_case(request.user, case_id, locked=True)
            result = create_upload(case, request.user, data)
        return Response(result, status=201)


class VersionsView(CaseView):
    def post(self, request, document_id):
        self.limited(request)
        data = self.data(request, inputs.NewVersionInput)
        document = Document.objects.filter(pk=document_id).first()
        if not document:
            raise Http404
        with transaction.atomic():
            case = get_case(request.user, document.case_id, locked=True)
            result = create_upload(case, request.user, data, document)
        return Response(result, status=201)


class ContentView(CaseView):
    def post(self, request, upload_id):
        self.limited(request)
        if request.content_type != "application/octet-stream":
            raise IdentityError("INVALID_INPUT", "Envie o conteúdo binário do arquivo.", 415)
        with transaction.atomic():
            case, item = get_version(request.user, upload_id, locked=True)
            check_upload(case, item, request.user)
            if item.uploaded_at:
                raise IdentityError("UPLOAD_CLOSED", "O conteúdo desta versão já foi recebido.", 409)
            try:
                write_stream(item.object_key, request.stream, item.size_bytes)
            except InvalidFile as exc:
                raise IdentityError("INVALID_FILE", "O tamanho recebido não confere ou o envio já existe.", 422) from exc
            item.uploaded_at = timezone.now()
            item.save(update_fields=["uploaded_at"])
        return Response(status=204)


class CompleteView(CaseView):
    def post(self, request, upload_id):
        self.limited(request)
        data = self.data(request, inputs.CompleteInput)
        with transaction.atomic():
            case, item = get_version(request.user, upload_id, locked=True)
            if item.uploaded_by_id != request.user.pk:
                raise Http404
            # Retry da confirmação é idempotente, mas não pode trocar o checksum.
            if item.status != DocumentVersion.Status.UPLOADING:
                if item.sha256 and item.sha256 == data["checksum"]:
                    return Response(version_data(item), status=202)
                raise IdentityError("UPLOAD_CLOSED", "Este envio já foi concluído.", 409)
            check_upload(case, item, request.user)
            if not item.uploaded_at:
                raise IdentityError("UPLOAD_INCOMPLETE", "Envie o arquivo antes de concluir.", 409)
            try:
                checksum, mime = inspect_file(item.object_key, item.size_bytes)
                if checksum != data["checksum"] or mime != item.declared_mime:
                    raise InvalidFile("integrity")
            except (InvalidFile, FileNotFoundError):
                item.status = DocumentVersion.Status.REJECTED
                item.last_error = "INVALID_FILE"
                item.save(update_fields=["status", "last_error"])
                changed(case, request.user, "DOCUMENT_REJECTED", "Documento recusado na validação do envio.", versionId=str(item.pk))
                return Response({"error": {"code": "INVALID_FILE", "message": "Formato, tamanho ou integridade incompatível. Envie uma nova versão.", "fields": {}}}, status=422)
            item.sha256, item.detected_mime = checksum, mime
            item.status = DocumentVersion.Status.QUARANTINED
            item.save(update_fields=["sha256", "detected_mime", "status"])
            changed(case, request.user, "DOCUMENT_QUARANTINED", "Documento recebido e aguardando verificação.", versionId=str(item.pk))
        return Response(version_data(item), status=202)


def downloadable(request, document_id, version_id):
    case, item = get_version(request.user, version_id)
    if item.document_id != document_id:
        raise Http404
    if item.status != DocumentVersion.Status.AVAILABLE:
        raise IdentityError("DOCUMENT_UNAVAILABLE", "O arquivo ainda não foi liberado para download.", 409)
    return item


class DownloadView(CaseView):
    def get(self, request, document_id, version_id):
        item = downloadable(request, document_id, version_id)
        token = signing.dumps({"version": str(item.pk), "user": str(request.user.pk), "portal": request.portal,
            "session": digest(request.session.session_key or "")}, salt="document-download")
        response = Response({"url": f"/api/v1/documents/{document_id}/versions/{version_id}/content?token={token}", "expiresIn": 300})
        response["Cache-Control"] = "no-store, private"
        return response


class DownloadContentView(CaseView):
    def get(self, request, document_id, version_id):
        try:
            payload = signing.loads(request.query_params.get("token", ""), salt="document-download", max_age=300)
            expected = {"version": str(version_id), "user": str(request.user.pk), "portal": request.portal,
                        "session": digest(request.session.session_key or "")}
            if payload != expected:
                raise signing.BadSignature()
        except (signing.BadSignature, ValueError, TypeError):
            raise IdentityError("INVALID_DOWNLOAD", "Link expirado ou inválido. Solicite o download novamente.", 403)
        item = downloadable(request, document_id, version_id)
        try:
            source = object_path(item.object_key).open("rb")
        except FileNotFoundError:
            raise Http404
        audit(request.user, "DOCUMENT_DOWNLOADED", request.portal, versionId=str(item.pk))
        response = FileResponse(source, as_attachment=True, filename=item.filename, content_type="application/octet-stream")
        response["Cache-Control"] = "no-store, private"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox"
        response["Referrer-Policy"] = "no-referrer"
        return response
