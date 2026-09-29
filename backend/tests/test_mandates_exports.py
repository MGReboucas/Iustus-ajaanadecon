import hashlib
import json
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
from zipfile import ZipFile
from django.core import signing
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from pypdf import PdfReader
from apps.cases.models import Case
from apps.communication.models import Message
from apps.documents.models import DocumentVersion
from apps.legal.models import MandateTemplate, GeneratedMandate, CaseExport
from integrations.storage.private import object_path
from .test_workflow import WorkflowTests

BODY = "Outorgante: {{cliente_nome}}, documento {{cliente_documento}}.\nAdvogado: {{advogado_nome}}, OAB {{advogado_oab}}.\nTexto sintético para testes de preenchimento; sem uso jurídico real.\n{{cidade}}, {{data_emissao}}. Caso {{caso_referencia}}."
FIELDS = {"cliente_nome": "José de Teste", "cliente_documento": "DOC-SINTETICO", "advogado_nome": "Maria de Teste", "advogado_oab": "OAB-TESTE", "cidade": "Natal"}

@override_settings(CASE_LOCAL_TEST_ACCESS=False)
class MandateExportTests(TestCase):
    browser = WorkflowTests.browser
    post = WorkflowTests.post
    user = WorkflowTests.user
    login = WorkflowTests.login
    team_login = WorkflowTests.team_login
    draft = WorkflowTests.draft
    submit = WorkflowTests.submit
    mutation = WorkflowTests.mutation
    submitted = WorkflowTests.submitted
    assigned = WorkflowTests.assigned
    triage = WorkflowTests.triage
    grant_access = WorkflowTests.grant_access
    accepted = WorkflowTests.accepted
    action = WorkflowTests.action

    def setUp(self):
        WorkflowTests.setUp(self)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = override_settings(DOCUMENT_LOCAL_STORAGE_ENABLED=True, DOCUMENT_STORAGE_ROOT=folder.name)
        config.enable()
        self.addCleanup(config.disable)
        self.storage = Path(folder.name)

    def template(self):
        result = self.post(self.lawyer, "legal/mandate-templates", {"name": "Modelo de teste", "body": BODY, "approved": True})
        self.assertEqual(result.status_code, 201, result.content)
        return result.json()

    def generated(self):
        item, template = self.accepted(), self.template()
        result = self.post(self.lawyer, f"cases/{item['id']}/mandates", {"version": item["version"], "templateId": template["id"], "fields": FIELDS, "confirmed": True})
        self.assertEqual(result.status_code, 201, result.content)
        item["version"] = result.json()["caseVersion"]
        return item, result.json()

    def export(self, item, browser=None):
        result = self.post(browser or self.browser_client, f"cases/{item['id']}/exports", {"version": item["version"]})
        self.assertEqual(result.status_code, 201, result.content)
        return result.json()

    def download(self, bundle, browser=None):
        response = (browser or self.browser_client).get(bundle["url"])
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        content = b"".join(response.streaming_content)
        return content

    def test_template_approval_revision_ownership_and_placeholder_validation(self):
        payload = {"name": "Modelo de teste", "body": BODY, "approved": True}
        for browser in (self.browser_client, self.admin):
            self.assertEqual(self.post(browser, "legal/mandate-templates", payload).status_code, 403)
        self.assertEqual(self.post(self.lawyer, "legal/mandate-templates", payload, csrf=False).status_code, 403)
        for extra in ({"approved": False}, {"body": BODY+" {{desconhecido}}"}, {"body": BODY.replace("{{cliente_nome}}", "nome")}, {"body": BODY+" {campo}"}):
            self.assertEqual(self.post(self.lawyer, "legal/mandate-templates", {**payload, **extra}).status_code, 422)
        first = self.template()
        second = self.post(self.lawyer, "legal/mandate-templates", {**payload, "previousId": first["id"], "body": BODY+"\nVersão dois."})
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["number"], 2)
        self.assertEqual(MandateTemplate.objects.get(pk=first["id"]).body, BODY)
        self.assertEqual(self.post(self.lawyer, "legal/mandate-templates", {**payload, "previousId": first["id"]}).status_code, 409)
        self.assertEqual(self.post(self.colleague, "legal/mandate-templates", {**payload, "previousId": first["id"]}).status_code, 404)

    def test_generated_pdf_hash_fields_version_and_stale_retry(self):
        item, result = self.generated()
        version = DocumentVersion.objects.get(pk=result["document"]["id"])
        content = object_path(version.object_key).read_bytes()
        text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(content)).pages)
        self.assertIn("José de Teste", text)
        self.assertIn("Modelo de teste v1", text)
        self.assertNotIn("{{", text)
        self.assertEqual(hashlib.sha256(content).hexdigest(), version.sha256)
        generated = GeneratedMandate.objects.get(version=version)
        self.assertEqual(generated.template.sha256, hashlib.sha256(BODY.encode()).hexdigest())
        response = self.post(self.lawyer, f"cases/{item['id']}/mandates", {"version": item["version"]-1, "templateId": str(generated.template_id), "fields": FIELDS, "confirmed": True})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(GeneratedMandate.objects.count(), 1)
        self.assertIsNone(version.scanned_at)  # Conteúdo gerado no servidor, sem inventar inspeção de upload.

    def test_generation_rejects_missing_fields_other_case_and_rolls_back_storage(self):
        item, template = self.accepted(), self.template()
        body = {"version": item["version"], "templateId": template["id"], "fields": FIELDS, "confirmed": True}
        url = f"cases/{item['id']}/mandates"
        self.assertEqual(self.post(self.colleague, url, body).status_code, 404)
        self.assertEqual(self.post(self.browser_client, url, body).status_code, 403)
        for fields, expected in (({}, 422), ({**FIELDS, "unexpected": "extra"}, 422), ({**FIELDS, "cliente_nome": "\x00"}, 400)):
            self.assertEqual(self.post(self.lawyer, url, {**body, "fields": fields}).status_code, expected)
        with patch("apps.legal.mandates.changed", side_effect=RuntimeError("synthetic rollback")):
            with self.assertRaises(RuntimeError):
                self.post(self.lawyer, url, body)
        self.assertFalse(GeneratedMandate.objects.exists())
        self.assertEqual(list(self.storage.iterdir()), [])

    def test_dossier_includes_files_and_publication_but_never_private_content(self):
        item, result = self.generated()
        case = Case.objects.get(pk=item["id"])
        case.state = Case.State.PREPARING
        case.save()
        item = self.action(item, "DRAFT", text="PECA_PUBLICADA_SINTETICA")
        item = self.action(item, "PUBLISH", confirmed=True)
        item = self.action(item, "DRAFT", text="MINUTA_PRIVADA_NUNCA_EXPORTAR")
        Message.objects.create(case=case, author=self.lawyer_user, text="NOTA_INTERNA_NUNCA_EXPORTAR", visibility="INTERNAL", client_id=uuid4())
        Message.objects.create(case=case, author=self.client_user, text="MENSAGEM_PUBLICA_SINTETICA", visibility="PUBLIC", client_id=uuid4())
        bundle = self.export(item)
        content = self.download(bundle)
        self.assertEqual(hashlib.sha256(content).hexdigest(), bundle["sha256"])
        with ZipFile(BytesIO(content)) as archive:
            text = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist() if name.endswith((".txt", ".json")))
            self.assertIn("PECA_PUBLICADA_SINTETICA", text)
            self.assertIn("MENSAGEM_PUBLICA_SINTETICA", text)
            self.assertNotIn("MINUTA_PRIVADA_NUNCA_EXPORTAR", text)
            self.assertNotIn("NOTA_INTERNA_NUNCA_EXPORTAR", text)
            self.assertNotIn("Distribuição interna privada", text)
            manifest = json.loads(archive.read("manifesto.json"))
            entry = manifest["documents"][0]
            self.assertEqual(hashlib.sha256(archive.read(entry["path"])).hexdigest(), result["sha256"])
            self.assertTrue(all(not name.startswith(("/", "..")) for name in archive.namelist()))

    def test_export_session_expiration_transfer_and_purge(self):
        item, _ = self.generated()
        bundle = self.export(item)
        self.assertEqual(self.other.get(bundle["url"]).status_code, 403)
        other_session = self.browser()
        self.login(other_session, self.client_user)
        self.assertEqual(other_session.get(bundle["url"]).status_code, 403)
        self.assertEqual(self.admin.get(bundle["url"]).status_code, 403)
        self.assertEqual(self.post(self.admin, f"cases/{item['id']}/exports", {"version": item["version"]}).status_code, 404)
        lawyer_bundle = self.export(item, self.lawyer)
        self.mutation(self.admin, item, "assignment", lawyerId=str(self.colleague_user.pk), reason="Transferência de teste")
        self.assertEqual(self.lawyer.get(lawyer_bundle["url"]).status_code, 404)
        row = CaseExport.objects.get(pk=bundle["id"])
        row.expires_at = timezone.now()-timedelta(seconds=1)
        row.save()
        self.assertEqual(self.browser_client.get(bundle["url"]).status_code, 410)
        call_command("purge_case_exports", stdout=StringIO())
        row.refresh_from_db()
        self.assertIsNotNone(row.purged_at)
        self.assertFalse(object_path(row.object_key).exists())
        self.assertTrue(object_path(CaseExport.objects.get(pk=lawyer_bundle["id"]).object_key).exists())

    def test_expired_signature_and_missing_or_corrupt_file_fail_closed(self):
        item, result = self.generated()
        bundle = self.export(item)
        with patch("apps.legal.exports.signing.loads", side_effect=signing.SignatureExpired()):
            self.assertEqual(self.browser_client.get(bundle["url"]).status_code, 403)
        version = DocumentVersion.objects.get(pk=result["document"]["id"])
        object_path(version.object_key).write_bytes(b"corrupt")
        response = self.post(self.browser_client, f"cases/{item['id']}/exports", {"version": item["version"]})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(CaseExport.objects.count(), 1)
        object_path(version.object_key).unlink()
        self.assertEqual(self.post(self.browser_client, f"cases/{item['id']}/exports", {"version": item["version"]}).status_code, 409)

    def test_unavailable_documents_are_listed_not_exported_and_closed_case_is_readable(self):
        item, result = self.generated()
        DocumentVersion.objects.filter(pk=result["document"]["id"]).update(status="QUARANTINED")
        Case.objects.filter(pk=item["id"]).update(state=Case.State.CLOSED)
        bundle = self.export(item)
        with ZipFile(BytesIO(self.download(bundle))) as archive:
            manifest = json.loads(archive.read("manifesto.json"))
            self.assertEqual(manifest["documents"], [])
            self.assertEqual(manifest["omittedDocuments"][0]["status"], "QUARANTINED")
            self.assertFalse(any(name.endswith(".pdf") for name in archive.namelist()))
