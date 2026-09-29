from unittest.mock import patch

from django.conf import settings
from django.db import OperationalError
from django.test import TestCase


class ReadinessTests(TestCase):
    def request(self, **headers):
        return self.client.get("/api/v1/ready", HTTP_HOST="localhost:3000", **headers)

    def test_direct_access_is_rejected_before_database_check(self):
        with patch("config.views.connection.cursor") as cursor:
            response = self.request()
        self.assertEqual(response.status_code, 403)
        cursor.assert_not_called()

    def test_trusted_proxy_can_check_database_without_user_session(self):
        response = self.request(HTTP_X_IUSTUS_PROXY_KEY=settings.IUSTUS_PROXY_SECRET)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-store", response["Cache-Control"])

    def test_database_failure_returns_no_connection_details(self):
        with patch("config.views.connection.cursor", side_effect=OperationalError("private password and host")):
            response = self.request(HTTP_X_IUSTUS_PROXY_KEY=settings.IUSTUS_PROXY_SECRET)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertIn("no-store", response["Cache-Control"])

    def test_mutations_are_rejected(self):
        response = self.client.post("/api/v1/ready", HTTP_HOST="localhost:3000",
                                    HTTP_X_IUSTUS_PROXY_KEY=settings.IUSTUS_PROXY_SECRET)
        self.assertEqual(response.status_code, 405)
