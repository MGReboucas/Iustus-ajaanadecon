from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4

from django.db import connection, connections
from django.test import TransactionTestCase

from apps.cases.models import Case
from apps.communication.models import Message, Notification
from . import test_identity as identity


@skipUnless(connection.vendor == "postgresql", "Exige locks reais de PostgreSQL")
class CommunicationConcurrencyTests(TransactionTestCase):
    browser = identity.IdentityTests.browser
    post = identity.IdentityTests.post
    user = identity.IdentityTests.user
    login = identity.IdentityTests.login

    def test_concurrent_retry_persists_one_message_and_one_notification(self):
        owner = self.user()
        lawyer = self.user("LAWYER", "lawyer@example.test")
        case = Case.objects.create(owner=owner, lawyer=lawyer, state=Case.State.TRIAGE)
        browsers = [self.browser(), self.browser()]
        for browser in browsers:
            self.login(browser, owner)
        tokens = [browser.get("/api/v1/auth/csrf").json()["csrfToken"] for browser in browsers]
        barrier = Barrier(2)
        key = str(uuid4())

        def send(index):
            try:
                barrier.wait(timeout=10)
                response = browsers[index].post(f"/api/v1/cases/{case.pk}/messages",
                    {"text": "Envio simultâneo", "clientMessageId": key}, content_type="application/json", HTTP_X_CSRFTOKEN=tokens[index])
                return response.status_code, response.json()["id"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(send, (0, 1)))
        self.assertEqual(sorted(row[0] for row in results), [200, 201])
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
