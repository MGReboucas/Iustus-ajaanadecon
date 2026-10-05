import base64
from io import StringIO
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings
from apps.identity.security import IdentityError
from integrations.pagbank.client import request_api


@override_settings(BILLING_ENABLED=False, PAGBANK_API_TOKEN="", PAGBANK_WEBHOOK_PUBLIC_KEY="", PAGBANK_ENVIRONMENT="sandbox")
class PagBankSetupTests(SimpleTestCase):
    def test_missing_token_diagnostic_does_not_call_provider(self):
        output = StringIO()
        with patch("jobs.management.commands.check_pagbank.request_api") as provider:
            call_command("check_pagbank", stdout=output)
            provider.assert_not_called()
            with self.assertRaises(CommandError):
                call_command("check_pagbank", fetch_webhook_key=True, stdout=output)
        self.assertIn("Token configurado: não", output.getvalue())

    @override_settings(PAGBANK_API_TOKEN="synthetic-private-token")
    def test_key_can_be_fetched_while_checkout_is_disabled_without_printing_secrets(self):
        key = ec.generate_private_key(ec.SECP256R1()).public_key()
        encoded = base64.b64encode(key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
        output = StringIO()
        with patch("jobs.management.commands.check_pagbank.request_api", return_value={"public_key": encoded}) as provider, patch("pathlib.Path.write_text") as write:
            call_command("check_pagbank", fetch_webhook_key=True, stdout=output)
            provider.assert_called_once_with("/public-keys?type=webhook", configuration_check=True)
            write.assert_called_once()
        self.assertNotIn("synthetic-private-token", output.getvalue())
        self.assertNotIn(encoded, output.getvalue())

    @override_settings(PAGBANK_API_TOKEN="synthetic")
    def test_configuration_bypass_cannot_create_checkout(self):
        with self.assertRaises(ValueError):
            request_api("/checkouts", {}, configuration_check=True)
        with self.assertRaises(IdentityError):
            request_api("/checkouts", {})
