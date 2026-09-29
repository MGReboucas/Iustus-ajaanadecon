from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings

from jobs.management.commands.check_document_services import PUBLIC_FLAGS, REQUIRED_HEADERS


@override_settings(DOCUMENT_STORAGE_BACKEND="s3", DOCUMENT_S3_BUCKET="synthetic",
                   PORTAL_ORIGINS={"client": "https://client.example.test", "team": "https://team.example.test"})
class DocumentServicesTests(SimpleTestCase):
    def storage_client(self):
        client = Mock()
        client.get_public_access_block.return_value = {"PublicAccessBlockConfiguration": dict.fromkeys(PUBLIC_FLAGS, True)}
        client.get_bucket_ownership_controls.return_value = {"OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}}
        client.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": False}}
        client.get_bucket_cors.return_value = {"CORSRules": [{
            "AllowedOrigins": ["https://client.example.test", "https://team.example.test"],
            "AllowedMethods": ["PUT"], "AllowedHeaders": list(REQUIRED_HEADERS),
        }]}
        return client

    def run_check(self, client=None, verdicts=(True, False), **options):
        output = StringIO()
        with patch("jobs.management.commands.check_document_services.s3_client", return_value=client or self.storage_client()), \
             patch("jobs.management.commands.check_document_services.scan", side_effect=verdicts) as scanner:
            call_command("check_document_services", stdout=output, **options)
        return output.getvalue(), scanner

    def test_private_bucket_and_clean_and_eicar_checks_pass_without_writes(self):
        client = self.storage_client()
        output, scanner = self.run_check(client)
        self.assertIn("storage: OK", output)
        self.assertIn("scanner: OK", output)
        samples = [call.args[0].getvalue() for call in scanner.call_args_list]
        self.assertEqual(len(samples[1]), 68)
        self.assertIn(b"EICAR-STANDARD", samples[1])
        self.assertTrue(all(name.startswith("get_") for name, _, _ in client.mock_calls))

    def test_public_policy_and_disabled_block_are_rejected(self):
        for public_policy in (True, False):
            client = self.storage_client()
            if public_policy:
                client.get_bucket_policy_status.return_value = {"PolicyStatus": {"IsPublic": True}}
            else:
                client.get_public_access_block.return_value["PublicAccessBlockConfiguration"]["BlockPublicAcls"] = False
            with self.subTest(public_policy=public_policy), self.assertRaises(CommandError):
                self.run_check(client)

    def test_cors_rejects_wildcard_missing_portal_missing_header_and_extra_methods(self):
        for field, value in (("AllowedOrigins", ["*"]), ("AllowedOrigins", ["https://client.example.test"]),
                             ("AllowedHeaders", ["content-type"]), ("AllowedMethods", ["PUT", "GET"])):
            client = self.storage_client()
            client.get_bucket_cors.return_value["CORSRules"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(CommandError):
                self.run_check(client)

    def test_scanner_must_detect_eicar_and_accept_clean_sample(self):
        for verdicts in ((True, True), (False,)):
            with self.subTest(verdicts=verdicts), self.assertRaises(CommandError):
                self.run_check(verdicts=verdicts, only="scanner")

    def test_network_errors_do_not_expose_private_details(self):
        client = self.storage_client()
        client.get_public_access_block.side_effect = RuntimeError("private-key-and-host")
        with self.assertRaises(CommandError) as result:
            self.run_check(client, only="storage")
        self.assertNotIn("private-key-and-host", str(result.exception))

    @override_settings(DOCUMENT_STORAGE_BACKEND="disabled")
    def test_missing_configuration_is_not_reported_as_success(self):
        with self.assertRaises(CommandError):
            self.run_check(only="storage")
