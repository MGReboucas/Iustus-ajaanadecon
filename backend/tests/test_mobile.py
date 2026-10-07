from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.cases.models import Case, CaseEvent
from apps.communication.models import Message, Notification
from apps.identity.models import IdentityEmail, MobileSession, User
from apps.identity.security import digest


PASSWORD = "Synthetic-Mobile-938!"


class MobileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mobile@example.test", PASSWORD, first_name="Associado",
                                            email_verified_at=timezone.now())
        self.client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost:3000",
                             HTTP_X_IUSTUS_PROXY_KEY=settings.IUSTUS_PROXY_SECRET)

    def login(self, **changes):
        return self.client.post("/api/v1/mobile/auth/login", {"email": self.user.email, "password": PASSWORD, **changes},
                                content_type="application/json")

    def headers(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.content)
        return {"HTTP_AUTHORIZATION": "Bearer " + response.json()["token"]}

    def test_session_is_hashed_and_not_a_web_cookie(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]
        self.assertTrue(MobileSession.objects.filter(pk=digest(token)).exists())
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertNotIn(token, str(list(MobileSession.objects.values())))
        self.assertEqual(self.client.get("/api/v1/me", HTTP_AUTHORIZATION="Bearer " + token).status_code, 403)

    def test_browser_session_cannot_authenticate_mobile(self):
        csrf = self.client.get("/api/v1/auth/csrf").json()["csrfToken"]
        response = self.client.post("/api/v1/auth/login", {"email": self.user.email, "password": PASSWORD},
            content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/mobile/dashboard").status_code, 401)

    def test_invalid_and_privileged_accounts_cannot_login(self):
        self.assertEqual(self.login(password="wrong").status_code, 403)
        self.assertEqual(self.login(role="ADMIN").status_code, 400)
        for changes in ({"email_verified_at": None}, {"is_active": False}, {"role": "LAWYER"}, {"role": "ADMIN"}):
            with self.subTest(changes=changes):
                User.objects.filter(pk=self.user.pk).update(email_verified_at=timezone.now(), is_active=True, role="CLIENT")
                User.objects.filter(pk=self.user.pk).update(**changes)
                self.assertEqual(self.login().status_code, 403)
        self.assertFalse(MobileSession.objects.exists())

    def test_expiry_idle_and_account_changes_revoke_access(self):
        for change in ("expiry", "idle", "password", "inactive", "role", "unverified"):
            with self.subTest(change=change):
                User.objects.filter(pk=self.user.pk).update(is_active=True, role="CLIENT", email_verified_at=timezone.now())
                headers = self.headers()
                session = MobileSession.objects.get(pk=digest(headers["HTTP_AUTHORIZATION"].split()[1]))
                if change == "expiry":
                    MobileSession.objects.filter(pk=session.pk).update(expires_at=timezone.now()-timedelta(seconds=1))
                elif change == "idle":
                    MobileSession.objects.filter(pk=session.pk).update(last_active_at=timezone.now()-timedelta(seconds=settings.IDENTITY_IDLE_SECONDS["client"]+1))
                elif change == "password":
                    User.objects.filter(pk=self.user.pk).update(auth_version=session.auth_version+1)
                elif change == "inactive":
                    User.objects.filter(pk=self.user.pk).update(is_active=False)
                elif change == "role":
                    User.objects.filter(pk=self.user.pk).update(role="ADMIN")
                else:
                    User.objects.filter(pk=self.user.pk).update(email_verified_at=None)
                self.assertEqual(self.client.get("/api/v1/mobile/dashboard", **headers).status_code, 401)

    def test_logout_revokes_only_current_device(self):
        first, second = self.headers(), self.headers()
        self.assertEqual(self.client.post("/api/v1/mobile/auth/logout", {}, content_type="application/json", **first).status_code, 204)
        self.assertEqual(self.client.get("/api/v1/mobile/dashboard", **first).status_code, 401)
        self.assertEqual(self.client.get("/api/v1/mobile/dashboard", **second).status_code, 200)

    def test_dashboard_and_detail_isolate_owner_and_private_events(self):
        own = Case.objects.create(owner=self.user, title="Meu caso", description="Descrição pessoal", category="CONSUMER")
        other = User.objects.create_user("other@example.test", PASSWORD)
        hidden = Case.objects.create(owner=other, title="Outro caso")
        CaseEvent.objects.create(case=own, actor=self.user, action="SUBMITTED", state=own.state, version=1, public=True, reason="Visível")
        CaseEvent.objects.create(case=own, actor=self.user, action="ASSIGNED", state=own.state, version=2, public=False, reason="Sigiloso")
        headers = self.headers()
        dashboard = self.client.get("/api/v1/mobile/dashboard", **headers).json()
        self.assertEqual(dashboard["totalCases"], 1)
        self.assertEqual(dashboard["user"]["email"], self.user.email)
        self.assertFalse(dashboard["membership"]["active"])
        cases = self.client.get("/api/v1/mobile/cases", **headers).json()["results"]
        self.assertEqual([row["id"] for row in cases], [str(own.pk)])
        self.assertEqual(self.client.get(f"/api/v1/mobile/cases/{hidden.pk}", **headers).status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/mobile/cases/{hidden.pk}/timeline", **headers).status_code, 404)
        detail = self.client.get(f"/api/v1/mobile/cases/{own.pk}", **headers).json()
        self.assertEqual(detail["description"], "Descrição pessoal")
        events = self.client.get(f"/api/v1/mobile/cases/{own.pk}/timeline", **headers).json()["results"]
        self.assertEqual([row["reason"] for row in events], ["Visível"])
        self.assertEqual(self.client.post("/api/v1/mobile/cases", {}, content_type="application/json", **headers).status_code, 405)

    def test_case_cursor_pagination(self):
        Case.objects.bulk_create([Case(owner=self.user, title=f"Caso {i}") for i in range(23)])
        headers = self.headers()
        first = self.client.get("/api/v1/mobile/cases", **headers).json()
        second = self.client.get("/api/v1/mobile/cases", {"cursor": first["nextCursor"]}, **headers).json()
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(len(second["results"]), 3)
        self.assertFalse(set(row["id"] for row in first["results"]) & set(row["id"] for row in second["results"]))

    def test_mobile_conversation_permissions_and_retry(self):
        lawyer = User.objects.create_user("lawyer@example.test", PASSWORD, role="LAWYER")
        item = Case.objects.create(owner=self.user, lawyer=lawyer, state=Case.State.TRIAGE)
        other = User.objects.create_user("outsider@example.test", PASSWORD)
        hidden = Case.objects.create(owner=other, lawyer=lawyer, state=Case.State.TRIAGE)
        Message.objects.create(case=item, author=lawyer, text="Nota privada", visibility="INTERNAL", client_id=uuid4())
        Message.objects.create(case=item, author=lawyer, text="Mensagem pública", visibility="PUBLIC", client_id=uuid4())
        headers = self.headers()
        url = f"/api/v1/mobile/cases/{item.pk}/messages"
        payload = {"text": "Resposta do associado", "clientMessageId": str(uuid4())}
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertTrue(self.client.get(f"/api/v1/mobile/cases/{item.pk}", **headers).json()["canMessage"])
        self.assertEqual([row["text"] for row in self.client.get(url, **headers).json()["results"]], ["Mensagem pública"])
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(f"/api/v1/mobile/cases/{hidden.pk}/messages", payload if method == self.client.post else {},
                                   content_type="application/json", **headers).status_code, 404)
        self.assertEqual(self.client.post(url, {**payload, "visibility": "INTERNAL"}, content_type="application/json", **headers).status_code, 403)
        first = self.client.post(url, payload, content_type="application/json", **headers)
        repeated = self.client.post(url, payload, content_type="application/json", **headers)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(first.json()["id"], repeated.json()["id"])
        self.assertEqual(Notification.objects.filter(recipient=lawyer).count(), 1)
        self.assertEqual(self.client.post(url, {**payload, "text": "Mudou"}, content_type="application/json", **headers).status_code, 409)
        for state in (Case.State.DRAFT, Case.State.REJECTED, Case.State.CLOSED):
            Case.objects.filter(pk=item.pk).update(state=state)
            self.assertFalse(self.client.get(f"/api/v1/mobile/cases/{item.pk}", **headers).json()["canMessage"])
            self.assertEqual(self.client.post(url, {**payload, "clientMessageId": str(uuid4())}, content_type="application/json", **headers).status_code, 409)

    def test_recovery_does_not_disclose_accounts(self):
        responses = [self.client.post("/api/v1/mobile/auth/recovery", {"email": email}, content_type="application/json")
                     for email in [self.user.email, "unknown@example.test"]]
        self.assertEqual([response.status_code for response in responses], [202, 202])
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(IdentityEmail.objects.count(), 1)

    @override_settings(IDENTITY_RATE_LIMITS_ENABLED=True)
    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.login(password="wrong").status_code, 403)
        self.assertEqual(self.login().status_code, 429)

    def test_proxy_portal_and_malformed_credentials(self):
        self.assertEqual(Client(HTTP_HOST="localhost:3000").get("/api/v1/mobile/dashboard").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/mobile/auth/login", {"email": self.user.email, "password": PASSWORD},
            content_type="application/json", HTTP_HOST="127.0.0.1:3000").status_code, 403)
        for token in ("Basic invalid", "Bearer bad", "Bearer", "Bearer " + "x"*43):
            self.assertEqual(self.client.get("/api/v1/mobile/dashboard", HTTP_AUTHORIZATION=token).status_code, 401)

    def test_limits_number_of_sessions(self):
        first = self.headers()
        for _ in range(5):
            self.headers()
        self.assertEqual(MobileSession.objects.filter(user=self.user).count(), 5)
        self.assertEqual(self.client.get("/api/v1/mobile/dashboard", **first).status_code, 401)
