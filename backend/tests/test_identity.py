import re
import time
from datetime import timedelta
from unittest.mock import patch

import pyotp
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.identity.models import ActionToken, IdentityEmail, MFADevice, User
from apps.identity.security import decrypt, encrypt
from jobs.mail import deliver_one

PASSWORD = "Synthetic-Passphrase-938!"


class IdentityTests(TestCase):
    def browser(self, team=False):
        return Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1:3000" if team else "localhost:3000", HTTP_X_IUSTUS_PROXY_KEY=settings.IUSTUS_PROXY_SECRET)

    def post(self, client, route, data=None, csrf=True):
        headers = {}
        if csrf:
            response = client.get("/api/v1/auth/csrf")
            self.assertEqual(response.status_code, 200, response.content)
            headers["HTTP_X_CSRFTOKEN"] = response.json()["csrfToken"]
        return client.post("/api/v1/" + route, data or {}, content_type="application/json", **headers)

    def user(self, role="CLIENT", email="client@example.test", verified=True):
        return User.objects.create_user(email, PASSWORD, first_name="Pessoa Teste", role=role, email_verified_at=timezone.now() if verified else None)

    def email_token(self, mode):
        body = decrypt(IdentityEmail.objects.latest("created_at").encrypted_body)
        return re.search(r"#" + mode + r"=([^\s]+)", body)[1]

    def login(self, browser, user):
        return self.post(browser, "auth/login", {"email": user.email, "password": PASSWORD})

    def team_login(self, role="ADMIN", email="admin@example.test"):
        user = self.user(role, email)
        browser = self.browser(True)
        self.assertEqual(self.login(browser, user).status_code, 202)
        response = self.post(browser, "auth/mfa/enroll")
        self.assertEqual(response.status_code, 200, response.content)
        secret = response.json()["secret"]
        result = self.post(browser, "auth/mfa/verify", {"code": pyotp.TOTP(secret).now()})
        self.assertEqual(result.status_code, 200, result.content)
        return browser, user, secret, result.json()["recoveryCodes"]

    def test_anonymous_mutations_require_csrf_including_login(self):
        for route in ("auth/register", "auth/login", "auth/recovery", "auth/reset", "auth/verify", "auth/mfa/enroll", "auth/mfa/verify", "auth/invitations/accept"):
            with self.subTest(route=route):
                response = self.post(self.browser(), route, csrf=False)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "CSRF_FAILED")

    def test_untrusted_proxy_and_cross_origin_denied(self):
        self.assertEqual(Client(HTTP_HOST="localhost:3000").get("/api/v1/auth/csrf").status_code, 403)
        browser = self.browser()
        csrf = browser.get("/api/v1/auth/csrf").json()["csrfToken"]
        response = browser.post("/api/v1/auth/login", {}, content_type="application/json", HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN="http://evil.invalid")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "CSRF_FAILED")

    def test_register_verify_login_logout_and_duplicate_generic(self):
        browser = self.browser()
        data = {"name": "Cliente Teste", "email": "NEW@example.test", "password": PASSWORD, "policyVersion": settings.REGISTRATION_POLICY_VERSION}
        result = self.post(browser, "auth/register", data)
        self.assertEqual(result.status_code, 202, result.content)
        duplicate = self.post(browser, "auth/register", data)
        self.assertEqual(result.json(), duplicate.json())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(IdentityEmail.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.role, "CLIENT")
        self.assertEqual(self.login(browser, user).status_code, 403)
        token = self.email_token("verify")
        self.assertNotIn(token, str(ActionToken.objects.values().first()))
        self.assertNotIn(token, IdentityEmail.objects.get().encrypted_body)
        self.assertEqual(self.post(browser, "auth/verify", {"token": token}).status_code, 204)
        self.assertEqual(self.post(browser, "auth/verify", {"token": token}).status_code, 400)
        self.assertEqual(self.login(browser, user).status_code, 200)
        self.assertEqual(browser.get("/api/v1/dashboard/client").status_code, 200)
        cookie = browser.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.post(browser, "auth/logout").status_code, 204)
        replay = self.browser()
        replay.cookies[settings.SESSION_COOKIE_NAME] = cookie
        self.assertEqual(replay.get("/api/v1/me").status_code, 403)

    def test_registration_cannot_grant_roles_and_is_not_on_team_portal(self):
        data = {"name": "Pessoa Teste", "email": "new@example.test", "password": PASSWORD, "policyVersion": settings.REGISTRATION_POLICY_VERSION}
        self.assertEqual(self.post(self.browser(), "auth/register", {**data, "role": "ADMIN"}).status_code, 400)
        self.assertEqual(self.post(self.browser(True), "auth/register", data).status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_copied_cookie_and_forwarded_host_do_not_change_portal(self):
        user = self.user()
        client = self.browser()
        self.login(client, user)
        team = self.browser(True)
        team.cookies = client.cookies.copy()
        self.assertEqual(team.get("/api/v1/me", HTTP_X_FORWARDED_HOST="localhost:3000").status_code, 403)
        self.assertEqual(client.get("/api/v1/me").status_code, 200)
        self.assertEqual(client.get("/api/v1/dashboard/team").status_code, 403)
        self.assertIn("no-store", client.get("/api/v1/me")["Cache-Control"])

    def test_reset_revokes_every_session_and_old_token(self):
        user = self.user()
        first, second = self.browser(), self.browser()
        self.login(first, user)
        self.login(second, user)
        recovery = self.browser()
        result = self.post(recovery, "auth/recovery", {"email": user.email})
        unknown = self.post(recovery, "auth/recovery", {"email": "unknown@example.test"})
        self.assertEqual(result.json(), unknown.json())
        token = self.email_token("reset")
        data = {"token": token, "password": "New-Synthetic-Passphrase-194!"}
        self.assertEqual(self.post(recovery, "auth/reset", data).status_code, 204)
        self.assertEqual(first.get("/api/v1/me").status_code, 403)
        self.assertEqual(second.get("/api/v1/me").status_code, 403)
        self.assertEqual(self.post(recovery, "auth/reset", data).status_code, 400)

    def test_expired_token_and_blocked_account(self):
        user = self.user()
        browser = self.browser()
        self.post(browser, "auth/recovery", {"email": user.email})
        token = self.email_token("reset")
        ActionToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post(browser, "auth/reset", {"token": token, "password": PASSWORD}).status_code, 400)
        self.login(browser, user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        self.assertEqual(browser.get("/api/v1/me").status_code, 403)

    def test_idle_expiry_allows_fresh_login(self):
        user = self.user()
        browser = self.browser()
        self.login(browser, user)
        session = browser.session
        session["last_active"] = time.time() - 999999
        session.save()
        self.assertEqual(browser.get("/api/v1/me").status_code, 403)
        self.assertEqual(self.login(browser, user).status_code, 200)

    def test_password_alone_cannot_access_team_or_create_invites(self):
        user = self.user("ADMIN", "admin@example.test")
        browser = self.browser(True)
        self.assertEqual(self.login(browser, user).status_code, 202)
        self.assertEqual(browser.get("/api/v1/dashboard/team").status_code, 403)
        self.assertEqual(self.post(browser, "admin/invitations", {"email": "lawyer@example.test"}).status_code, 403)
        self.assertEqual(self.login(self.browser(), user).status_code, 403)

    def test_mfa_enrollment_replay_and_one_time_recovery(self):
        browser, user, secret, codes = self.team_login()
        device = MFADevice.objects.get(user=user)
        self.assertNotIn(secret, device.encrypted_secret)
        self.assertNotIn(codes[0], str(device.recovery_hashes))
        self.assertEqual(len(codes), 8)
        self.assertEqual(browser.get("/api/v1/dashboard/team").status_code, 200)
        self.post(browser, "auth/logout")
        self.login(browser, user)
        self.assertEqual(self.post(browser, "auth/mfa/enroll").status_code, 409)
        self.assertEqual(self.post(browser, "auth/mfa/verify", {"code": pyotp.TOTP(secret).at(device.last_counter * 30)}).status_code, 403)
        self.assertEqual(self.post(browser, "auth/mfa/verify", {"code": codes[0]}).status_code, 200)
        self.post(browser, "auth/logout")
        self.login(browser, user)
        self.assertEqual(self.post(browser, "auth/mfa/verify", {"code": codes[0]}).status_code, 403)

    def test_password_reset_preserves_mfa_requirement_and_revokes_challenge(self):
        browser, user, secret, codes = self.team_login()
        self.post(browser, "auth/logout")
        self.login(browser, user)
        other = self.browser(True)
        self.post(other, "auth/recovery", {"email": user.email})
        self.post(other, "auth/reset", {"token": self.email_token("reset"), "password": PASSWORD})
        self.assertEqual(self.post(browser, "auth/mfa/verify", {"code": codes[0]}).status_code, 403)
        self.assertTrue(self.login(other, user).json()["mfaRequired"])
        self.assertEqual(other.get("/api/v1/me").status_code, 403)

    def test_admin_invites_lawyer_and_invite_is_single_use(self):
        browser, _, _, _ = self.team_login()
        self.assertEqual(self.post(browser, "admin/invitations", {"email": "lawyer@example.test"}).status_code, 202)
        token = self.email_token("invite")
        accept = self.browser(True)
        data = {"token": token, "name": "Advogado Teste", "password": PASSWORD}
        self.assertEqual(self.post(accept, "auth/invitations/accept", data).status_code, 201)
        self.assertEqual(self.post(accept, "auth/invitations/accept", data).status_code, 400)
        lawyer = User.objects.get(email="lawyer@example.test")
        self.assertEqual(lawyer.role, "LAWYER")
        self.assertTrue(self.login(accept, lawyer).json()["enrollmentRequired"])

    def test_lawyer_cannot_invite_or_promote(self):
        browser, _, _, _ = self.team_login("LAWYER", "lawyer@example.test")
        self.assertEqual(self.post(browser, "admin/invitations", {"email": "other@example.test"}).status_code, 403)

    @override_settings(IDENTITY_RATE_LIMITS_ENABLED=True)
    def test_login_rate_limit_survives_new_browser_sessions(self):
        for _ in range(10):
            response = self.post(self.browser(), "auth/login", {"email": "target@example.test", "password": PASSWORD})
            self.assertEqual(response.status_code, 403)
        response = self.post(self.browser(), "auth/login", {"email": "target@example.test", "password": PASSWORD})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "300")

    def test_mail_retry_and_scrubbing_after_delivery(self):
        item = IdentityEmail.objects.create(recipient="test@example.test", subject="Teste", encrypted_body=encrypt("Link fictício"), available_at=timezone.now())
        with patch("jobs.mail.build_message", side_effect=ConnectionError("secret-not-for-logs")):
            self.assertTrue(deliver_one())
        item.refresh_from_db()
        self.assertEqual(item.last_error, "ConnectionError")
        self.assertIsNone(item.sent_at)
        self.assertFalse(deliver_one())
        IdentityEmail.objects.filter(pk=item.pk).update(available_at=timezone.now())
        self.assertTrue(deliver_one())
        item.refresh_from_db()
        self.assertEqual(item.encrypted_body, "")
        self.assertIsNotNone(item.sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(deliver_one())
