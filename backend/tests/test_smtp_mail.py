import io
from unittest.mock import patch
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from apps.identity.models import IdentityEmail
from apps.identity.security import encrypt
from jobs.mail import deliver_one
from jobs.branded_mail import build_message, render_email


class BrandedMailTests(TestCase):
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
