from datetime import timedelta
from uuid import uuid4
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.cases.models import Case, ServiceAccess
from apps.documents.models import Document, DocumentVersion
from apps.legal.models import LegalWork, LegalTask
from .test_cases import CaseTests

@override_settings(CASE_LOCAL_TEST_ACCESS=False)
class WorkflowTests(TestCase):
    browser = CaseTests.browser
    post = CaseTests.post
    user = CaseTests.user
    login = CaseTests.login
    team_login = CaseTests.team_login
    setUp = CaseTests.setUp
    draft = CaseTests.draft
    submit = CaseTests.submit
    mutation = CaseTests.mutation
    submitted = CaseTests.submitted
    assigned = CaseTests.assigned
    triage = CaseTests.triage

    def grant_access(self):
        response = self.post(self.admin, "admin/service-access", {"email": self.client_user.email,
            "enabled": True, "expiresAt": (timezone.now() + timedelta(days=3)).isoformat(), "reason": "Atendimento autorizado"})
        self.assertEqual(response.status_code, 200, response.content)

    def accepted(self):
        self.grant_access()
        return self.mutation(self.lawyer, self.triage(), "transitions", targetState="ACEITO",
            reason="Escopo e informações conferidos", scopeConfirmed=True, conflictChecked=True, informationSufficient=True)

    def file(self, item, user, status="AVAILABLE"):
        doc = Document.objects.create(case_id=item["id"], created_by=user)
        return DocumentVersion.objects.create(document=doc, uploaded_by=user, number=1, filename="sintetico.pdf",
            declared_mime="application/pdf", size_bytes=10, object_key=str(uuid4()), status=status,
            expires_at=timezone.now()+timedelta(days=1))

    def action(self, item, action, browser=None, **data):
        response = self.post(browser or self.lawyer, f"cases/{item['id']}/workflow", {"version": item["version"], "action": action, **data})
        self.assertEqual(response.status_code, 200, response.content)
        return {"id": item["id"], **response.json()}

    def preparing(self):
        item = self.accepted()
        mandate = self.file(item, self.lawyer_user)
        item = self.action(item, "START", text="Preparação, protocolo e acompanhamento", position="AUTHOR", documentId=str(mandate.pk))
        signed = self.file(item, self.client_user)
        item = self.action(item, "SIGN", self.browser_client, documentId=str(signed.pk))
        return self.action(item, "VERIFY", confirmed=True)

    def test_admission_authorization_revocation_and_expiry(self):
        body = {"email": self.client_user.email, "enabled": True, "expiresAt": (timezone.now()+timedelta(days=1)).isoformat(), "reason": "Teste de liberação"}
        for browser in (self.browser_client, self.lawyer):
            self.assertEqual(self.post(browser, "admin/service-access", body).status_code, 403)
            self.assertEqual(browser.get("/api/v1/admin/service-access").status_code, 403)
        self.assertEqual(self.post(self.admin, "admin/service-access", body, csrf=False).status_code, 403)
        item = self.draft()
        self.assertEqual(self.submit(item).status_code, 422)
        self.grant_access()
        self.assertEqual(self.submit(item).status_code, 200)
        self.assertEqual(self.admin.get("/api/v1/admin/service-access").status_code, 200)
        self.assertEqual(self.post(self.admin, "admin/service-access", {**body, "enabled": False}).status_code, 200)
        self.assertEqual(self.browser_client.get(f"/api/v1/cases/{item['id']}").status_code, 200)
        self.assertEqual(self.submit(self.draft()).status_code, 422)
        self.grant_access()
        ServiceAccess.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertFalse(self.browser_client.get("/api/v1/cases/catalog").json()["submission"]["canSubmit"])

    def test_full_workflow_draft_privacy_protocol_deadline_and_closure(self):
        item = self.preparing()
        item = self.action(item, "DRAFT", text="Minuta confidencial sintética")
        client = self.browser_client.get(f"/api/v1/cases/{item['id']}/workflow").json()
        self.assertNotIn("draft", client)
        self.assertEqual(client["publishedText"], "")
        item = self.action(item, "PUBLISH", confirmed=True)
        receipt = self.file(item, self.lawyer_user)
        item = self.action(item, "FILE", documentId=str(receipt.pk), protocol="PROTO-123", authority="Órgão sintético", confirmed=True)
        self.assertEqual(item["state"], "EM_ACOMPANHAMENTO")
        item = self.action(item, "TASK", kind="HEARING", title="Audiência sintética", dueAt=(timezone.now()+timedelta(days=2)).isoformat(), text="Agendamento confirmado")
        response = self.post(self.lawyer, f"cases/{item['id']}/workflow", {"version": item["version"], "action": "CLOSE", "text": "Atendimento concluído", "confirmed": True})
        self.assertEqual(response.status_code, 422)
        task = item["tasks"][0]["id"]
        item = self.action(item, "RESCHEDULE", taskId=task, dueAt=(timezone.now()+timedelta(days=4)).isoformat(), text="Remarcação confirmada")
        item = self.action(item, "COMPLETE", taskId=task, text="Audiência realizada")
        item = self.action(item, "CLOSE", confirmed=True, text="Resultado comunicado e atendimento concluído")
        self.assertEqual(item["state"], "ENCERRADO")
        self.assertEqual(self.browser_client.get(f"/api/v1/cases/{item['id']}/workflow").json()["publishedText"], "Minuta confidencial sintética")
        denied = self.post(self.lawyer, f"cases/{item['id']}/workflow", {"version": item["version"], "action": "UPDATE", "text": "Alteração tardia"})
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(self.post(self.browser_client, f"cases/{item['id']}/messages", {"text": "Após encerrar", "visibility": "PUBLIC", "clientMessageId": str(uuid4())}).status_code, 409)

    def test_document_scope_quarantine_and_mandate_checks(self):
        item = self.accepted()
        foreign = self.file({"id": self.draft()["id"]}, self.lawyer_user)
        quarantine = self.file(item, self.lawyer_user, "QUARANTINED")
        for file in (foreign, quarantine):
            response = self.post(self.lawyer, f"cases/{item['id']}/workflow", {"version": item["version"], "action": "START", "position": "AUTHOR", "text": "Etapas contratadas sintéticas", "documentId": str(file.pk)})
            self.assertEqual(response.status_code, 422)
        self.assertFalse(LegalWork.objects.filter(case_id=item["id"]).exists())
        mandate = self.file(item, self.lawyer_user)
        item = self.action(item, "START", position="DEFENDANT", text="Etapas contratadas sintéticas", documentId=str(mandate.pk))
        response = self.post(self.lawyer, f"cases/{item['id']}/workflow", {"version": item["version"], "action": "VERIFY", "confirmed": True})
        self.assertEqual(response.status_code, 422)

    def test_isolation_transfer_and_stale_version(self):
        item = self.preparing()
        url = f"cases/{item['id']}/workflow"
        for browser in (self.admin, self.other, self.colleague):
            self.assertEqual(browser.get("/api/v1/" + url).status_code, 404)
        self.assertEqual(self.post(self.browser_client, url, {"version": item["version"], "action": "UPDATE", "text": "Ação indevida"}).status_code, 403)
        old = item["version"]
        item = self.action(item, "UPDATE", text="Movimentação pública sintética")
        self.assertEqual(self.post(self.lawyer, url, {"version": old, "action": "UPDATE", "text": "Ação desatualizada"}).status_code, 409)
        self.mutation(self.admin, item, "assignment", lawyerId=str(self.colleague_user.pk), reason="Transferência autorizada")
        self.assertEqual(self.lawyer.get("/api/v1/"+url).status_code, 404)
        self.assertEqual(self.post(self.lawyer, url, {"version": item["version"], "action": "UPDATE", "text": "Ação após transferência"}).status_code, 404)
        self.assertEqual(self.colleague.get("/api/v1/"+url).status_code, 200)

    def test_attention_tracks_mandate_and_overdue_tasks(self):
        item = self.preparing()
        item = self.action(item, "TASK", kind="DEADLINE", title="Prazo vencido", dueAt=(timezone.now()-timedelta(days=1)).isoformat(), text="Prazo informado pelo responsável")
        summary = self.lawyer.get("/api/v1/dashboard/overview").json()
        self.assertEqual(summary["attentionCount"], 1)
        self.assertIn(item["id"], [row["id"] for row in summary["attentionCases"]])

    def test_return_mandate_requires_correction_and_keeps_version_history(self):
        item = self.accepted()
        mandate = self.file(item, self.lawyer_user)
        item = self.action(item, "START", text="Etapas contratadas sintéticas", position="DEFENDANT", documentId=str(mandate.pk))
        signed = self.file(item, self.client_user)
        item = self.action(item, "SIGN", self.browser_client, documentId=str(signed.pk))
        item = self.action(item, "RETURN_MANDATE", text="Assinatura incompleta; envie uma nova versão.")
        self.assertIsNone(item["signedMandate"])
        summary = self.browser_client.get("/api/v1/dashboard/overview").json()
        self.assertEqual(summary["attentionCount"], 1)
        second = self.file(item, self.client_user)
        item = self.action(item, "SIGN", self.browser_client, documentId=str(second.pk))
        item = self.action(item, "VERIFY", confirmed=True)
        item = self.action(item, "DRAFT", text="Primeira minuta sintética")
        item = self.action(item, "PUBLISH", confirmed=True)
        item = self.action(item, "DRAFT", text="Segunda minuta ainda privada")
        case = Case.objects.get(pk=item["id"])
        self.assertEqual(case.events.get(action="LEGAL_PUBLISH").metadata["snapshot"]["text"], "Primeira minuta sintética")
        self.assertEqual(self.browser_client.get(f"/api/v1/cases/{item['id']}/workflow").json()["publishedText"], "Primeira minuta sintética")
        self.assertEqual(case.events.filter(action="LEGAL_SIGN").count(), 2)
