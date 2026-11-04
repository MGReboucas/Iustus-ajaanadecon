import logging
import sys
from django.test import SimpleTestCase
from config.safe_logging import SafeExceptionFormatter


class SafeLoggingTests(SimpleTestCase):
    def test_handled_api_failure_logs_exception_without_private_message(self):
        from apps.identity.errors import identity_exception_handler
        from apps.identity.security import IdentityError
        from urllib.error import HTTPError
        try:
            try:
                raise HTTPError("https://private-url", 403, "private-provider-body", {}, None)
            except HTTPError as cause:
                raise IdentityError("PAYMENT_PROVIDER_UNAVAILABLE", "private-message", 503) from cause
        except IdentityError as exc:
            with self.assertLogs("django.request", level="ERROR") as captured:
                response = identity_exception_handler(exc, {})
        output = SafeExceptionFormatter().format(captured.records[0])
        self.assertEqual(response.status_code, 503)
        self.assertIn("code=PAYMENT_PROVIDER_UNAVAILABLE", output)
        self.assertIn("provider_http_status=403", output)
        self.assertNotIn("private-", output)

    def test_exception_chain_keeps_location_and_omits_sensitive_values(self):
        try:
            try:
                raise ValueError("private-token-and-customer-data")
            except ValueError as cause:
                raise RuntimeError("private-sql-query") from cause
        except RuntimeError:
            record = logging.LogRecord("django.request", logging.ERROR, __file__, 1,
                                       "private-url", (), sys.exc_info())
        record.request = {"Authorization": "private-authorization"}
        output = SafeExceptionFormatter().format(record)
        self.assertIn("RuntimeError", output)
        self.assertIn("ValueError", output)
        self.assertIn("test_safe_logging.py:", output)
        self.assertNotIn("private-", output)
