from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import connection, connections
from django.test import TransactionTestCase

from apps.cases.models import Case
from apps.documents.models import DocumentVersion
from . import test_identity as identity


@skipUnless(connection.vendor == "postgresql", "Exige locks reais de PostgreSQL")
class DocumentConcurrencyTests(TransactionTestCase):
    browser = identity.IdentityTests.browser
    post = identity.IdentityTests.post
    user = identity.IdentityTests.user
    login = identity.IdentityTests.login

    def test_competing_versions_have_one_winner(self):
        user = self.user()
        case = Case.objects.create(owner=user)
        browsers = [self.browser(), self.browser()]
        for browser in browsers:
            self.login(browser, user)
        data = {"filename": "ficticio.pdf", "mime": "application/pdf", "sizeBytes": 20}
        first = self.post(browsers[0], f"cases/{case.pk}/documents/uploads", data).json()
        document_id = first["version"]["documentId"]
        tokens = [browser.get("/api/v1/auth/csrf").json()["csrfToken"] for browser in browsers]
        barrier = Barrier(2)

        def create(index):
            try:
                barrier.wait(timeout=10)
                return browsers[index].post(f"/api/v1/documents/{document_id}/versions", {**data, "previousVersion": 1},
                    content_type="application/json", HTTP_X_CSRFTOKEN=tokens[index]).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(create, (0, 1))), [201, 409])
        self.assertEqual(list(DocumentVersion.objects.filter(document_id=document_id).order_by("number")
                              .values_list("number", flat=True)), [1, 2])
