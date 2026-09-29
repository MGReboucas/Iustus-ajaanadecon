import hashlib
import json
import uuid
from datetime import timedelta
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZIP_DEFLATED
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.response import Response
from apps.cases.serializers import VersionInput
from apps.cases.services import case_data, expect_version, get_case
from apps.cases.views import CaseView
from apps.documents.models import DocumentVersion
from apps.identity.security import IdentityError, digest, throttle
from apps.identity.services import audit
from integrations.storage.private import open_object, delete_object, write_stream, storage_configured
from .models import CaseExport, LegalWork

MAX_BYTES = 100 * 1024 * 1024
MAX_ROWS = 1000
EXPORT_SECONDS = 900


def bounded(query):
    rows = list(query[:MAX_ROWS + 1])
    if len(rows) > MAX_ROWS:
        raise IdentityError("EXPORT_TOO_LARGE", "O caso excede o limite desta exportação. Solicite uma cópia assistida ao escritório.", 422)
    return rows


def json_bytes(value):
    result = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    if len(result) > 10 * 1024 * 1024:
        raise IdentityError("EXPORT_TOO_LARGE", "O histórico excede o limite desta exportação.", 422)
    return result


def build_export(item, output):
    versions = bounded(DocumentVersion.objects.filter(document__case=item).order_by("created_at", "id"))
    files = [row for row in versions if row.status == DocumentVersion.Status.AVAILABLE]
    if len(files) > 200 or sum(row.size_bytes for row in files) > MAX_BYTES:
        raise IdentityError("EXPORT_TOO_LARGE", "A exportação aceita até 200 arquivos e 100 MiB de documentos.", 422)
    events = bounded(item.events.filter(public=True).order_by("created_at", "id"))
    messages = bounded(item.messages.filter(visibility="PUBLIC").select_related("author").order_by("created_at", "id"))
    tasks = bounded(item.legal_tasks.order_by("due_at", "id"))
    requests = bounded(item.information_requests.prefetch_related("attachments").order_by("created_at", "id"))
    work = LegalWork.objects.filter(case=item).first()
    manifest = {"caseId": str(item.pk), "caseVersion": item.version, "generatedAt": timezone.now().isoformat(),
                "documents": [], "omittedDocuments": [{"id": str(row.pk), "filename": row.filename, "status": row.status}
                    for row in versions if row.status != DocumentVersion.Status.AVAILABLE],
                "excludes": ["minutas internas", "notas internas", "eventos administrativos privados", "arquivos não liberados"]}
    metadata = {
        "caso.json": {**case_data(item, detail=True), "scope": work.scope if work else "",
                      "position": work.client_position if work else "", "processNumber": work.process_number if work else "",
                      "authority": work.authority if work else "", "protocol": work.protocol if work else ""},
        "complementos.json": [{"description": row.description, "response": row.response, "resolution": row.resolution,
                                "attachments": [str(link.version_id) for link in row.attachments.all()]} for row in requests],
        "historico.json": [{"action": row.action, "state": row.state, "reason": row.reason,
                            "createdAt": row.created_at.isoformat()} for row in events],
        "mensagens.json": [{"text": row.text, "author": row.author.first_name, "createdAt": row.created_at.isoformat()} for row in messages],
        "compromissos.json": [{"kind": row.kind, "title": row.title, "dueAt": row.due_at.isoformat(),
                               "completedAt": row.completed_at.isoformat() if row.completed_at else None, "outcome": row.outcome} for row in tasks],
    }
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("LEIA-ME.txt", "Dossiê do caso Iustus. Os arquivos JSON são textos UTF-8.\nDocumentos liberados e versões publicadas estão nas pastas documentos e pecas.\nArquivos ainda em verificação ou recusados são identificados no manifesto e não integram o pacote.\nMinutas, notas internas e eventos administrativos privados não são exportados.\n")
        for name, value in metadata.items():
            archive.writestr(name, json_bytes(value))
        for row in events:
            if row.action == "LEGAL_PUBLISH":
                text = row.metadata.get("snapshot", {}).get("text", "")
                if text:
                    archive.writestr(f"pecas/publicacao-{row.version}.txt", text.encode("utf-8"))
        if work and work.published_text:
            archive.writestr("pecas/ultima-publicacao.txt", work.published_text.encode("utf-8"))
        for row in files:
            # Caminhos do ZIP são gerados pelo servidor; nenhum nome do usuário controla diretórios.
            suffix = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}.get(row.detected_mime)
            if suffix is None:
                raise IdentityError("EXPORT_INTEGRITY", "Um documento precisa de nova conferência antes da exportação.", 409)
            name = f"documentos/{row.document_id}/v{row.number}{suffix}"
            checksum, size = hashlib.sha256(), 0
            try:
                with open_object(row.object_key) as source, archive.open(name, "w") as target:
                    while chunk := source.read(65536):
                        size += len(chunk)
                        if size > row.size_bytes:
                            raise IdentityError("EXPORT_INTEGRITY", "Integridade de documento incompatível.", 409)
                        checksum.update(chunk)
                        target.write(chunk)
            except (FileNotFoundError, ValueError):
                raise IdentityError("EXPORT_DOCUMENT_MISSING", "Um documento não está disponível no armazenamento. Tente novamente após a conferência do escritório.", 409)
            if size != row.size_bytes or checksum.hexdigest() != row.sha256:
                raise IdentityError("EXPORT_INTEGRITY", "Integridade de documento incompatível.", 409)
            manifest["documents"].append({"path": name, "filename": row.filename, "versionId": str(row.pk), "sha256": row.sha256, "sizeBytes": size})
        archive.writestr("manifesto.json", json_bytes(manifest))
    return output.tell()


def export_token(request, row):
    return signing.dumps({"export": str(row.pk), "user": str(request.user.pk), "portal": request.portal,
                          "session": digest(request.session.session_key or "")}, salt="case-export")


class ExportsView(CaseView):
    def post(self, request, case_id):
        self.limited(request)
        throttle("case-export", str(request.user.pk), 3, seconds=60)
        data = self.data(request, VersionInput)
        if not storage_configured():
            raise IdentityError("DOCUMENT_STORAGE_UNAVAILABLE", "Armazenamento privado não configurado.", 503)
        key, written = uuid.uuid4().hex, False
        try:
            with transaction.atomic():
                item = get_case(request.user, case_id, locked=True)
                expect_version(item, data["version"])
                with SpooledTemporaryFile(max_size=4*1024*1024, mode="w+b") as output:
                    size = build_export(item, output)
                    output.seek(0)
                    checksum = hashlib.file_digest(output, "sha256").hexdigest()
                    output.seek(0)
                    write_stream(key, output, size)
                    written = True
                row = CaseExport.objects.create(case=item, requested_by=request.user, case_version=item.version,
                    object_key=key, sha256=checksum, size_bytes=size, expires_at=timezone.now()+timedelta(seconds=EXPORT_SECONDS))
                audit(request.user, "case.export_created", request.portal, caseId=str(item.pk), exportId=str(row.pk), sha256=checksum)
                return Response({"id": str(row.pk), "url": f"/api/v1/exports/{row.pk}/content?token={export_token(request, row)}",
                    "filename": f"dossie-{str(item.pk)[:8].upper()}.zip", "expiresAt": row.expires_at.isoformat(),
                    "sha256": checksum, "sizeBytes": size}, status=201)
        except Exception:
            if written:
                delete_object(key)
            raise


class ExportContentView(CaseView):
    def get(self, request, export_id):
        try:
            payload = signing.loads(request.query_params.get("token", ""), salt="case-export", max_age=EXPORT_SECONDS)
            if payload != {"export": str(export_id), "user": str(request.user.pk), "portal": request.portal,
                           "session": digest(request.session.session_key or "")}:
                raise signing.BadSignature()
        except (signing.BadSignature, ValueError, TypeError):
            raise IdentityError("INVALID_DOWNLOAD", "Link expirado ou inválido. Gere uma nova exportação.", 403)
        row = CaseExport.objects.filter(pk=export_id, requested_by=request.user).first()
        if not row:
            raise Http404
        get_case(request.user, row.case_id)
        if row.expires_at <= timezone.now() or row.purged_at:
            raise IdentityError("EXPORT_EXPIRED", "O dossiê expirou. Gere uma nova exportação.", 410)
        try:
            source = open_object(row.object_key)
        except FileNotFoundError:
            raise Http404
        audit(request.user, "case.export_downloaded", request.portal, caseId=str(row.case_id), exportId=str(row.pk))
        response = FileResponse(source, as_attachment=True, filename=f"dossie-{str(row.case_id)[:8].upper()}.zip", content_type="application/zip")
        response["Cache-Control"] = "no-store, private"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox"
        response["Referrer-Policy"] = "no-referrer"
        return response
