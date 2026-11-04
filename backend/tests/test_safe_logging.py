import logging
import sys
from django.test import SimpleTestCase
from config.safe_logging import SafeExceptionFormatter


class SafeLoggingTests(SimpleTestCase):
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
