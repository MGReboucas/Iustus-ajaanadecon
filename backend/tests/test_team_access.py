from io import StringIO

import pyotp
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.identity.models import User
from .test_identity import IdentityTests, PASSWORD


@override_settings(PORTAL_ORIGINS={"team": "http://localhost:3000"},
                   IUSTUS_INITIAL_ADMIN_EMAIL="initial@example.test")
class TeamAccessTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login
    email_token = IdentityTests.email_token

    def activate(self, browser, token):
        return self.post(browser, "auth/invitations/accept", {
            "token": token, "name": "Equipe Teste", "password": PASSWORD})

    def bootstrap(self):
        call_command("bootstrap_admin", stdout=StringIO())
        browser = self.browser()
        self.assertEqual(self.activate(browser, self.email_token("invite")).status_code, 201)
        admin = User.objects.get(role="ADMIN")
        self.assertEqual(self.login(browser, admin).status_code, 202)
        secret = self.post(browser, "auth/mfa/enroll").json()["secret"]
        self.assertEqual(self.post(browser, "auth/mfa/verify", {"code": pyotp.TOTP(secret).now()}).status_code, 200)
        return browser, admin

    def test_public_registration_and_client_sessions_are_denied(self):
        browser = self.browser()
        self.assertEqual(browser.get("/api/v1/auth/csrf").json()["portal"], "team")
        self.assertEqual(self.post(browser, "auth/register", {
            "email": "initial@example.test", "password": PASSWORD, "name": "Intruso",
            "policyVersion": "development-v1"}).status_code, 403)
        self.assertFalse(User.objects.exists())
        client = self.user()
        self.assertEqual(self.login(browser, client).status_code, 403)
        self.assertEqual(self.browser(True).get("/api/v1/auth/csrf").status_code, 403)

    def test_bootstrap_requires_mail_activation_then_password_and_mfa(self):
        call_command("bootstrap_admin", stdout=StringIO())
        user = User.objects.get()
        self.assertFalse(user.has_usable_password())
        self.assertIsNone(user.email_verified_at)
        browser = self.browser()
        self.assertEqual(self.login(browser, user).status_code, 403)
        old = self.email_token("invite")
        call_command("bootstrap_admin", stdout=StringIO())
        self.assertEqual(self.activate(browser, old).status_code, 400)
        token = self.email_token("invite")
        self.assertEqual(self.activate(browser, token).status_code, 201)
        self.assertEqual(self.activate(browser, token).status_code, 400)
        self.assertEqual(self.login(browser, user).status_code, 202)
        self.assertEqual(browser.get("/api/v1/dashboard/team").status_code, 403)
        with self.assertRaises(CommandError):
            call_command("bootstrap_admin", stdout=StringIO())

    def test_bootstrap_never_promotes_existing_identity(self):
        user = self.user(email="initial@example.test")
        with self.assertRaises(CommandError):
            call_command("bootstrap_admin", stdout=StringIO())
        user.refresh_from_db()
        self.assertEqual(user.role, "CLIENT")

    def test_approval_can_be_revoked_before_activation_and_reissued(self):
        browser, _ = self.bootstrap()
        self.assertEqual(self.post(browser, "admin/invitations", {"email": "new@example.test"}).status_code, 202)
        user = User.objects.get(email="new@example.test")
        self.assertFalse(user.has_usable_password())
        token = self.email_token("invite")
        path = f"admin/users/{user.pk}/access"
        self.assertEqual(self.post(browser, path, {"active": False, "version": 1, "reason": "Aprovação cancelada pelo gestor"}).status_code, 200)
        self.assertEqual(self.activate(self.browser(), token).status_code, 400)
        self.assertEqual(self.post(browser, path, {"active": True, "version": 2, "reason": "Nova aprovação pelo gestor"}).status_code, 200)
        self.post(browser, "admin/invitations", {"email": user.email})
        self.assertEqual(self.activate(self.browser(), self.email_token("invite")).status_code, 201)

    def test_revocation_invalidates_sessions_and_mfa_challenges(self):
        admin, _ = self.bootstrap()
        self.post(admin, "admin/invitations", {"email": "new@example.test"})
        browser = self.browser()
        self.activate(browser, self.email_token("invite"))
        user = User.objects.get(email="new@example.test")
        self.login(browser, user)
        secret = self.post(browser, "auth/mfa/enroll").json()["secret"]
        self.post(browser, "auth/mfa/verify", {"code": pyotp.TOTP(secret).now()})
        self.assertEqual(browser.get("/api/v1/me").status_code, 200)
        self.assertEqual(browser.get("/api/v1/admin/users").status_code, 403)
        pending = self.browser()
        self.login(pending, user)
        path = f"admin/users/{user.pk}/access"
        self.post(admin, path, {"active": False, "version": 1, "reason": "Revogação imediata de acesso"})
        self.assertEqual(browser.get("/api/v1/me").status_code, 403)
        self.assertEqual(self.post(pending, "auth/mfa/verify", {"code": pyotp.TOTP(secret).now()}).status_code, 403)
        self.post(admin, path, {"active": True, "version": 2, "reason": "Acesso novamente aprovado"})
        self.assertEqual(browser.get("/api/v1/me").status_code, 403)

@override_settings(IDENTITY_MFA_REQUIRED=False, PORTAL_ORIGINS={"team": "http://localhost:3000"})
class PasswordOnlyTeamTests(TestCase):
    browser = IdentityTests.browser
    post = IdentityTests.post
    user = IdentityTests.user
    login = IdentityTests.login

    def test_password_login_opens_panel_without_claiming_mfa(self):
        admin = self.user(role="ADMIN")
        browser = self.browser()
        self.assertFalse(browser.get('/api/v1/auth/csrf').json()['mfaRequired'])
        response = self.login(browser, admin)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('mfaRequired', response.json())
        self.assertFalse(browser.session['mfa_verified'])
        self.assertEqual(browser.get('/api/v1/dashboard/team').status_code, 200)
        self.assertEqual(browser.get('/api/v1/admin/users').status_code, 200)
        with override_settings(IDENTITY_MFA_REQUIRED=True):
            self.assertEqual(browser.get('/api/v1/dashboard/team').status_code, 403)

    def test_roles_verification_revocation_and_password_remain_enforced(self):
        for role, verified in [('CLIENT', True), ('ADMIN', False)]:
            user = self.user(role=role, email=role+'@example.test', verified=verified)
            self.assertEqual(self.login(self.browser(), user).status_code, 403)
        lawyer = self.user(role='LAWYER', email='lawyer@example.test')
        browser = self.browser()
        self.assertEqual(self.post(browser, 'auth/login', {'email':lawyer.email, 'password':'wrong'}).status_code, 403)
        self.assertEqual(self.login(browser, lawyer).status_code, 200)
        self.assertEqual(browser.get('/api/v1/admin/users').status_code, 403)
        lawyer.is_active = False
        lawyer.save(update_fields=['is_active'])
        self.assertEqual(browser.get('/api/v1/dashboard/team').status_code, 403)

    def test_active_verified_lawyer_can_be_listed_without_mfa(self):
        admin = self.user(role='ADMIN')
        lawyer = self.user(role='LAWYER', email='lawyer@example.test')
        browser = self.browser()
        self.login(browser, admin)
        result = browser.get('/api/v1/cases/lawyers')
        self.assertEqual(result.status_code, 200)
        self.assertEqual([row['id'] for row in result.json()['results']], [str(lawyer.pk)])
