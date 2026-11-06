import io
from datetime import timedelta
from unittest.mock import patch
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from apps.identity.models import ActionToken, IdentityEmail, User
from apps.identity.security import encrypt
from apps.identity.services import issue_token
from jobs.mail import deliver_one
from jobs.branded_mail import build_message, render_email


class BrandedMailTests(TestCase):
    def test_replaced_invite_is_cancelled_and_only_latest_is_delivered(self):
        admin = User.objects.create_user("admin@example.test", "synthetic", role="ADMIN")
        lawyer = User(email="lawyer@example.test", role="LAWYER")
        lawyer.set_unusable_password()
        lawyer.save()
        issue_token("INVITE", lawyer.email, "team", user=lawyer, created_by=admin)
        old = IdentityEmail.objects.get()
        ActionToken.objects.update(consumed_at=timezone.now())
        issue_token("INVITE", lawyer.email, "team", user=lawyer, created_by=admin)
        self.assertTrue(deliver_one())
        old.refresh_from_db()
        self.assertIsNotNone(old.cancelled_at)
        self.assertIsNone(old.sent_at)
        self.assertEqual(old.encrypted_body, "")
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(deliver_one())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [lawyer.email])
        self.assertIn("Ativar meu acesso", mail.outbox[0].alternatives[0].content)
        self.assertFalse(deliver_one())

    def test_expired_revoked_or_changed_identity_links_are_not_sent(self):
        user = User.objects.create_user("client@example.test", "synthetic")
        for scenario in ("expired", "revoked", "version", "missing"):
            with self.subTest(scenario=scenario):
                user.is_active = True
                user.save()
                issue_token("RESET", user.email, "client", user=user)
                if scenario == "expired":
                    ActionToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
                elif scenario == "revoked":
                    user.is_active = False
                    user.save()
                elif scenario == "version":
                    user.auth_version += 1
                    user.save()
                else:
                    ActionToken.objects.all().delete()
                self.assertTrue(deliver_one())
                row = IdentityEmail.objects.latest("created_at")
                self.assertIsNotNone(row.cancelled_at)
                self.assertIsNone(row.sent_at)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(PORTAL_ORIGINS={"client": "https://iustus.app", "team": "https://iustus.app"})
    def test_queued_legacy_link_uses_canonical_domain_and_preserves_token(self):
        message = build_message("Access", "https://iustus-defesa-juridica.vercel.app/acessar#member=synthetic", ["buyer@example.test"])
        self.assertEqual(message.body, "https://www.iustus.app/acessar#member=synthetic")
        self.assertIn('href="https://www.iustus.app/acessar#member=synthetic"', message.alternatives[0].content)
        self.assertIn("Concluir meu cadastro", message.alternatives[0].content)

    @override_settings(PORTAL_ORIGINS={"client": "https://iustus.app", "team": "https://iustus.app"})
    def test_queued_apex_link_uses_www_and_preserves_token(self):
        message = build_message("Access", "https://iustus.app/acessar#member=synthetic", ["buyer@example.test"])
        self.assertEqual(message.body, "https://www.iustus.app/acessar#member=synthetic")
        self.assertIn('href="https://www.iustus.app/acessar#member=synthetic"', message.alternatives[0].content)

    def test_similar_external_hostname_is_not_rewritten(self):
        body = "https://iustus.app.evil.example/acessar#member=synthetic"
        message = build_message("Access", body, ["buyer@example.test"])
        self.assertEqual(message.body, body)
        self.assertNotIn('href="https://iustus.app.evil.example', message.alternatives[0].content)

    def test_health_check_is_read_only_and_does_not_send_mail(self):
        with patch("jobs.management.commands.check_mail.build_message") as message:
            call_command("check_mail", stdout=io.StringIO())
        message.assert_not_called()

    def test_message_contains_text_html_and_inline_logo(self):
        body = "Pagamento confirmado.\n\nhttp://localhost:3000/acessar#member=synthetic"
        message = build_message("Sua conta", body, ["buyer@example.test"])
        self.assertEqual(message.body, body)
        html = message.alternatives[0].content
        self.assertIn("Concluir meu cadastro", html)
        self.assertIn('src="cid:iustus-logo"', html)
        self.assertIn("#0b1b2f", html)
        parts = list(message.message().walk())
        self.assertTrue(any(part.get_content_type() == "text/plain" for part in parts))
        self.assertTrue(any(part.get("Content-ID") == "<iustus-logo>" for part in parts))

    def test_html_escapes_content_and_does_not_make_external_action_button(self):
        html = render_email("<script>alert(1)</script>", '<img src=x>\n\nhttps://evil.example/acessar#reset=bad')
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x>", html)
        self.assertNotIn('href="https://evil.example', html)

    def test_failed_delivery_keeps_body_then_success_scrubs_it(self):
        row = IdentityEmail.objects.create(recipient="buyer@example.test", subject="Access",
            encrypted_body=encrypt("secret link"), available_at=timezone.now())
        with patch("jobs.mail.build_message", side_effect=ConnectionError("private token")), self.assertLogs("jobs.mail") as logs:
            self.assertTrue(deliver_one())
        self.assertNotIn("private token", str(logs.output))
        row.refresh_from_db()
        self.assertIsNone(row.sent_at)
        self.assertTrue(row.encrypted_body)
        self.assertGreater(row.available_at, timezone.now())
        self.assertFalse(deliver_one())
        IdentityEmail.objects.filter(pk=row.pk).update(available_at=timezone.now())
        self.assertTrue(deliver_one())
        row.refresh_from_db()
        self.assertIsNotNone(row.sent_at)
        self.assertEqual(row.encrypted_body, "")
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
