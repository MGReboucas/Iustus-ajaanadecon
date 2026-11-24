from datetime import timedelta
from io import StringIO
from uuid import uuid4

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.cases.models import Case, CaseEvent, InformationRequest, LocalCaseAccess
from . import test_identity as identity


@override_settings(CASE_LOCAL_TEST_ACCESS=True)
class CaseTests(TestCase):
    browser = identity.IdentityTests.browser
    post = identity.IdentityTests.post
    user = identity.IdentityTests.user
    login = identity.IdentityTests.login
    team_login = identity.IdentityTests.team_login

    def setUp(self):
        self.client_user = self.user()
        self.browser_client = self.browser()
        self.login(self.browser_client, self.client_user)
        self.other_user = self.user(email="other@example.test")
        self.other = self.browser()
        self.login(self.other, self.other_user)
        self.admin, self.admin_user, *_ = self.team_login()
        self.lawyer, self.lawyer_user, *_ = self.team_login("LAWYER", "lawyer@example.test")
        self.colleague, self.colleague_user, *_ = self.team_login("LAWYER", "colleague@example.test")
        self.grant = LocalCaseAccess.objects.create(user=self.client_user, expires_at=timezone.now() + timedelta(days=1), reason="Teste sintético")

    def draft(self):
        response = self.post(self.browser_client, "cases", {"title": "Título privado", "description": "Relato confidencial fictício para testar o isolamento.", "category": "CIVIL_OTHER", "scopeAcknowledged": True})
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def mutation(self, browser, item, action, **data):
        result = self.post(browser, f"cases/{item['id']}/{action}", {"version": item["version"], **data})
        self.assertIn(result.status_code, (200, 201), result.content)
        return result.json()

    def submit(self, item, browser=None, key=None, version=None):
        browser = browser or self.browser_client
        token = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        return browser.post(f"/api/v1/cases/{item['id']}/submit", {"version": version or item["version"]}, content_type="application/json", HTTP_X_CSRFTOKEN=token, HTTP_IDEMPOTENCY_KEY=key or str(uuid4()))

    def submitted(self):
        result = self.submit(self.draft())
        self.assertEqual(result.status_code, 200, result.content)
        return result.json()

    def assigned(self):
        return self.mutation(self.admin, self.submitted(), "assignment", lawyerId=str(self.lawyer_user.pk), reason="Distribuição interna privada")

    def triage(self):
        return self.mutation(self.lawyer, self.assigned(), "transitions", targetState="EM_TRIAGEM")

    def test_sessions_csrf_and_strict_fields(self):
        self.assertEqual(self.browser().get("/api/v1/cases").status_code, 403)
        self.assertEqual(self.post(self.browser_client, "cases", csrf=False).status_code, 403)
        for body in ({"owner": str(self.other_user.pk)}, {"state": "ACEITO"}, {"category": "FAMILY"}, {"category": "SUCCESSIONS"}):
            self.assertEqual(self.post(self.browser_client, "cases", body).status_code, 400)
        self.assertEqual(self.post(self.admin, "cases", {}).status_code, 403)
        self.assertEqual(Case.objects.count(), 0)

    def test_private_drafts_and_case_scope_on_every_read(self):
        item = self.draft()
        for browser in (self.other, self.lawyer, self.colleague, self.admin):
            self.assertEqual(browser.get("/api/v1/cases").json()["results"], [])
            for suffix in ("", "/requests", "/timeline"):
                self.assertEqual(browser.get(f"/api/v1/cases/{item['id']}{suffix}").status_code, 404)

    def test_submission_fail_closed_expiration_and_incomplete_data(self):
        item = self.draft()
        self.grant.expires_at = timezone.now() - timedelta(seconds=1)
        self.grant.save()
        self.assertEqual(self.submit(item).json()["error"]["code"], "SUBMISSION_UNAVAILABLE")
        self.grant.expires_at = timezone.now() + timedelta(days=1)
        self.grant.save()
        with override_settings(CASE_LOCAL_TEST_ACCESS=False):
            self.assertFalse(self.browser_client.get("/api/v1/cases/catalog").json()["submission"]["canSubmit"])
            self.assertEqual(self.submit(item).status_code, 422)
        Case.objects.filter(pk=item["id"]).update(scope_acknowledged=False)
        self.assertEqual(self.submit(item).json()["error"]["code"], "INCOMPLETE_CASE")
        self.assertEqual(CaseEvent.objects.count(), 1)

    def test_submission_without_client_category(self):
        item = self.draft()
        Case.objects.filter(pk=item["id"]).update(category="")
        response = self.submit(item)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["category"], "")
        self.assertEqual(response.json()["state"], "SUBMETIDO")

    def test_submission_idempotency_and_foreign_owner(self):
        item, key = self.draft(), str(uuid4())
        self.assertEqual(self.submit(item, self.other, key).status_code, 404)
        first, again = self.submit(item, key=key), self.submit(item, key=key)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), again.json())
        self.assertEqual(CaseEvent.objects.filter(action="SUBMITTED").count(), 1)
        self.assertEqual(self.submit(item, key=key, version=9).status_code, 409)
        self.assertEqual(self.submit(item).status_code, 409)

    def test_admin_only_metadata_and_assignment_requires_active_mfa_lawyer(self):
        item = self.submitted()
        metadata = self.admin.get("/api/v1/cases").json()["results"][0]
        self.assertNotIn("title", metadata)
        self.assertNotIn("description", metadata)
        self.assertNotIn("owner", metadata)
        self.assertEqual(self.admin.get(f"/api/v1/cases/{item['id']}").status_code, 404)
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/assignment", {"version": item["version"], "lawyerId": str(self.lawyer_user.pk), "reason": "Teste"}).status_code, 403)
        for user in (self.client_user, self.admin_user, self.user("LAWYER", "no-factor@example.test")):
            result = self.post(self.admin, f"cases/{item['id']}/assignment", {"version": item["version"], "lawyerId": str(user.pk), "reason": "Teste negativo"})
            self.assertEqual(result.status_code, 400)
        self.assertEqual(self.browser_client.get("/api/v1/cases/lawyers").status_code, 403)

    def test_transfer_revokes_reads_and_mutations_and_hides_private_reason(self):
        item = self.triage()
        item = self.mutation(self.admin, item, "assignment", lawyerId=str(self.colleague_user.pk), reason="Motivo privado de redistribuição")
        for suffix in ("", "/requests", "/timeline"):
            self.assertEqual(self.lawyer.get(f"/api/v1/cases/{item['id']}{suffix}").status_code, 404)
        result = self.post(self.lawyer, f"cases/{item['id']}/transitions", {"version": item["version"], "targetState": "RECUSADO", "reason": "Não autorizado"})
        self.assertEqual(result.status_code, 404)
        self.assertEqual(self.colleague.get(f"/api/v1/cases/{item['id']}").status_code, 200)
        events = self.browser_client.get(f"/api/v1/cases/{item['id']}/timeline").json()["results"]
        self.assertNotIn("ASSIGNED", [row["action"] for row in events])
        self.assertNotIn("privado", str(events))

    def test_version_conflict_and_no_edits_after_submission(self):
        item = self.draft()
        token = self.browser_client.get("/api/v1/auth/csrf").json()["csrfToken"]
        def patch(version):
            return self.browser_client.patch(f"/api/v1/cases/{item['id']}", {"version": version, "title": "Alterado"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        fresh = patch(item["version"]).json()
        self.assertEqual(patch(item["version"]).status_code, 409)
        submitted = self.submit(fresh).json()
        self.assertEqual(patch(submitted["version"]).status_code, 409)
        self.assertEqual(Case.objects.get(pk=item["id"]).title, "Alterado")

    def test_triage_checklist_and_invalid_transition(self):
        item = self.assigned()
        data = {"version": item["version"], "targetState": "ACEITO", "reason": "Análise concluída"}
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/transitions", data).status_code, 409)
        item = self.mutation(self.lawyer, item, "transitions", targetState="EM_TRIAGEM")
        data["version"] = item["version"]
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/transitions", data).status_code, 422)
        item = self.mutation(self.lawyer, item, "transitions", targetState="ACEITO", reason="Escopo e informações conferidos", scopeConfirmed=True, conflictChecked=True, informationSufficient=True)
        self.assertEqual(item["state"], "ACEITO")
        self.assertEqual(CaseEvent.objects.filter(case_id=item["id"], action="TRIAGE_DECISION").count(), 1)

    def test_rejection_requires_public_reason_and_is_terminal_here(self):
        item = self.triage()
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/transitions", {"version": item["version"], "targetState": "RECUSADO"}).status_code, 422)
        item = self.mutation(self.lawyer, item, "transitions", targetState="RECUSADO", reason="Matéria de família fora do escopo confirmado.")
        events = self.browser_client.get(f"/api/v1/cases/{item['id']}/timeline").json()["results"]
        self.assertIn("família", events[0]["reason"])
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/transitions", {"version": item["version"], "targetState": "EM_TRIAGEM"}).status_code, 409)

    def test_complement_response_does_not_resolve_and_cross_case_ids_fail(self):
        item = self.mutation(self.lawyer, self.triage(), "requests", description="Informe a data do fato fictício.")
        pending = InformationRequest.objects.get(case_id=item["id"])
        path = f"requests/{pending.pk}"
        self.assertEqual(self.post(self.lawyer, f"cases/{item['id']}/{path}/resolve", {"version": item["version"], "reason": "Sem resposta ainda"}).status_code, 422)
        self.assertEqual(self.post(self.other, f"cases/{item['id']}/{path}/response", {"version": item["version"], "text": "Tentativa alheia"}).status_code, 404)
        other = self.mutation(self.lawyer, self.triage(), "requests", description="Outra pendência fictícia.")
        self.assertEqual(self.post(self.browser_client, f"cases/{other['id']}/{path}/response", {"version": other["version"], "text": "ID de outro caso"}).status_code, 404)
        item = self.mutation(self.browser_client, item, path + "/response", text="O fato ocorreu na data informada para teste.")
        self.assertEqual(item["state"], "AGUARDANDO_CLIENTE")
        self.assertEqual(self.post(self.browser_client, f"cases/{item['id']}/{path}/response", {"version": item["version"], "text": "Não sobrescrever"}).status_code, 409)
        item = self.mutation(self.lawyer, item, path + "/resolve", reason="Complemento conferido pelo responsável.")
        self.assertEqual(item["state"], "EM_TRIAGEM")
        pending.refresh_from_db()
        self.assertIsNotNone(pending.resolved_at)

    def test_pagination_and_filters_apply_after_scope(self):
        Case.objects.bulk_create([Case(owner=self.client_user, title=f"Próprio {i}") for i in range(25)] + [Case(owner=self.other_user, title="Privado alheio")])
        first = self.browser_client.get("/api/v1/cases").json()
        second = self.browser_client.get("/api/v1/cases", {"cursor": first["nextCursor"]}).json()
        ids = [row["id"] for row in first["results"] + second["results"]]
        self.assertEqual(len(set(ids)), 25)
        self.assertIsNone(second["nextCursor"])
        self.assertNotIn("alheio", str(first) + str(second))
        self.assertEqual(self.browser_client.get("/api/v1/cases?state=ACEITO").json()["results"], [])

    def test_local_grant_guard_and_expiry(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command("grant_local_case_access", self.client_user.email, reason="Teste", stdout=StringIO())
        with override_settings(DEBUG=True):
            with self.assertRaises(CommandError):
                call_command("grant_local_case_access", self.client_user.email, days=8, reason="Teste", stdout=StringIO())
            call_command("grant_local_case_access", self.client_user.email, reason="Teste sintético", stdout=StringIO())
        self.grant.refresh_from_db()
        self.assertGreater(self.grant.expires_at, timezone.now())
