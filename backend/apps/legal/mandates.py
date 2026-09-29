import hashlib
import re
import uuid
from datetime import timedelta
from io import BytesIO
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from apps.cases.models import Case
from apps.cases.serializers import VersionInput
from apps.cases.services import changed, expect_state, expect_version, get_case
from apps.cases.views import CaseView
from apps.documents.models import Document, DocumentVersion
from apps.documents.services import version_data
from apps.identity.models import User
from apps.identity.security import IdentityError
from apps.identity.serializers import StrictSerializer
from apps.identity.services import audit
from integrations.storage.private import object_path, write_stream
from .models import MandateTemplate, GeneratedMandate
from .pdf import mandate_pdf, supported

FIELDS = {"cliente_nome": "Nome do outorgante", "cliente_documento": "Documento do outorgante",
          "cliente_endereco": "Endereço do outorgante", "advogado_nome": "Nome do advogado",
          "advogado_oab": "Inscrição OAB", "advogado_endereco": "Endereço profissional", "cidade": "Cidade da assinatura"}
AUTO = {"data_emissao", "caso_referencia"}
TOKEN = re.compile(r"\{\{([a-z_]+)\}\}")
REQUIRED = {"cliente_nome", "advogado_nome", "advogado_oab"}


def fields_for(body):
    keys = set(TOKEN.findall(body))
    rest = TOKEN.sub("", body)
    if "{" in rest or "}" in rest or keys - set(FIELDS) - AUTO or not REQUIRED <= keys:
        raise IdentityError("INVALID_TEMPLATE", "Use apenas os campos indicados, incluindo cliente_nome, advogado_nome e advogado_oab.", 422)
    if not supported(body):
        raise IdentityError("UNSUPPORTED_TEXT", "O modelo contém caracteres não suportados pelo PDF.", 422)
    return keys


class TemplateInput(StrictSerializer):
    name = serializers.CharField(min_length=3, max_length=160)
    body = serializers.CharField(min_length=40, max_length=30000)
    previousId = serializers.UUIDField(required=False)
    approved = serializers.BooleanField()


class GenerateInput(VersionInput):
    templateId = serializers.UUIDField()
    fields = serializers.DictField(child=serializers.CharField(max_length=500))
    confirmed = serializers.BooleanField()


def template_data(row):
    return {"id": str(row.pk), "name": row.name, "number": row.number, "body": row.body, "sha256": row.sha256,
            "fields": [{"key": key, "label": FIELDS[key]} for key in sorted(fields_for(row.body) - AUTO)],
            "approvedAt": row.approved_at.isoformat()}


class TemplatesView(CaseView):
    def get(self, request):
        self.role(request, "LAWYER")
        return self.listed(request, MandateTemplate.objects.filter(owner=request.user), template_data)

    def post(self, request):
        self.role(request, "LAWYER")
        self.limited(request)
        data = self.data(request, TemplateInput)
        if not data["approved"] or not supported(data["name"]):
            raise IdentityError("APPROVAL_REQUIRED", "Revise e aprove o texto jurídico do modelo antes de salvar.", 422)
        fields_for(data["body"])
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            family, number = uuid.uuid4(), 1
            if data.get("previousId"):
                previous = MandateTemplate.objects.filter(pk=data["previousId"], owner=request.user).first()
                if not previous:
                    raise Http404
                latest = MandateTemplate.objects.filter(family=previous.family).aggregate(n=Max("number"))["n"]
                if latest != previous.number:
                    raise IdentityError("VERSION_CONFLICT", "Use a versão mais recente deste modelo.", 409)
                family, number = previous.family, previous.number + 1
            row = MandateTemplate.objects.create(owner=request.user, family=family, number=number,
                name=data["name"], body=data["body"], sha256=hashlib.sha256(data["body"].encode()).hexdigest(), approved_at=timezone.now())
            audit(request.user, "mandate.template_approved", request.portal, templateId=str(row.pk), sha256=row.sha256)
        return Response(template_data(row), status=201)


class GenerateMandateView(CaseView):
    def post(self, request, case_id):
        self.role(request, "LAWYER")
        self.limited(request)
        data = self.data(request, GenerateInput)
        if not data["confirmed"]:
            raise IdentityError("APPROVAL_REQUIRED", "Confira os dados e o modelo antes de gerar a procuração.", 422)
        if not settings.DOCUMENT_LOCAL_STORAGE_ENABLED or not settings.DOCUMENT_STORAGE_ROOT:
            raise IdentityError("DOCUMENT_STORAGE_UNAVAILABLE", "Armazenamento privado não configurado.", 503)
        key = uuid.uuid4().hex
        written = False
        try:
            with transaction.atomic():
                item = get_case(request.user, case_id, locked=True)
                expect_version(item, data["version"])
                expect_state(item, Case.State.ACCEPTED)
                template = MandateTemplate.objects.filter(pk=data["templateId"], owner=request.user).first()
                if not template:
                    raise Http404
                expected = fields_for(template.body) - AUTO
                values = data["fields"]
                if set(values) != expected or any(not value.strip() or not supported(value) or any(ord(c) < 32 for c in value) for value in values.values()):
                    raise IdentityError("INVALID_FIELDS", "Preencha exatamente os campos do modelo, sem caracteres de controle.", 422)
                values = {**values, "data_emissao": timezone.localdate().strftime("%d/%m/%Y"), "caso_referencia": str(item.pk)[:8].upper()}
                body = TOKEN.sub(lambda match: values[match.group(1)], template.body)
                number = (item.generated_mandates.aggregate(n=Max("number"))["n"] or 0) + 1
                content = mandate_pdf(body, template_name=template.name, template_number=template.number,
                                      generation_number=number, reference=values["caso_referencia"])
                write_stream(key, BytesIO(content), len(content))
                written = True
                document = Document.objects.create(case=item, created_by=request.user)
                version = DocumentVersion.objects.create(document=document, number=1, uploaded_by=request.user,
                    filename=f"procuracao-{values['caso_referencia']}-{number}.pdf", declared_mime="application/pdf", detected_mime="application/pdf",
                    size_bytes=len(content), object_key=key, sha256=hashlib.sha256(content).hexdigest(),
                    status=DocumentVersion.Status.AVAILABLE, uploaded_at=timezone.now(), expires_at=timezone.now()+timedelta(minutes=30))
                GeneratedMandate.objects.create(case=item, template=template, version=version, number=number, fields=values)
                changed(item, request.user, "MANDATE_GENERATED", "Procuração gerada a partir de modelo revisado.",
                        templateId=str(template.pk), templateVersion=template.number, templateHash=template.sha256,
                        versionId=str(version.pk), sha256=version.sha256)
                return Response({"document": version_data(version), "caseVersion": item.version,
                                 "templateVersion": template.number, "sha256": version.sha256}, status=201)
        except Exception:
            if written:
                object_path(key).unlink(missing_ok=True)
            raise
