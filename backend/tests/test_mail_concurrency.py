from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless
from unittest.mock import patch, Mock

from django.db import connection, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.identity.models import IdentityEmail
from apps.identity.security import encrypt
from jobs.mail import deliver_one


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL leases")
class MailConcurrencyTests(TransactionTestCase):
    def test_second_worker_cannot_deliver_a_message_while_smtp_is_in_flight(self):
        row = IdentityEmail.objects.create(recipient="synthetic@example.test", subject="Test",
            encrypted_body=encrypt("Synthetic message"), available_at=timezone.now())
        sending, release = Event(), Event()

        def send(**kwargs):
            sending.set()
            if not release.wait(10):
                raise TimeoutError
            return 1

        def worker():
            try:
                return deliver_one()
            finally:
                connections.close_all()

        with patch("jobs.mail.build_message", return_value=Mock(send=send)) as build:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(worker)
                try:
                    self.assertTrue(sending.wait(10))
                    self.assertFalse(pool.submit(worker).result(timeout=10))
                finally:
                    release.set()
                self.assertTrue(first.result(timeout=10))
        row.refresh_from_db()
        self.assertIsNotNone(row.sent_at)
        self.assertEqual(row.attempts, 1)
        build.assert_called_once()
